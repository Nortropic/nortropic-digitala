"""Formåterhämtning använder originalets frysta dom utan historisk Python-import."""
import base64
import copy
import contextlib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kor_profil as kp
import kritikbevis as kb
import kvalitetsbild
from test_kor_profil import receipt_file


class Formaterhamtning(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.revision = 'abc51ddc122c4ef4366b31c82b4bac8ea9279604'
        self.hashes = {n: hashlib.sha256(self.old('verktyg/' + n)).hexdigest() for n in kb.DOMKOD}
        self.pin = hashlib.sha256(self.old('steg/DOMKOD.sha256')).hexdigest()
        self.post = {'bindning': {'rot_git_head': self.revision, 'verktyg': self.hashes},
                     'bedomningsbindning': {'domkod_sha256': self.pin}}

    def old(self, relative):
        return subprocess.check_output(['git', '-C', str(kp.ROT), 'show', self.revision + ':' + relative])

    def test_current_semantic_code_runs_with_original_pins_and_context_is_restored(self):
        original_root = kb.ROT
        with kp.historisk_domkod(self.post):
            self.assertEqual(kb.domkod(), self.pin)
            self.assertNotEqual(kb.ROT, original_root)
        self.assertEqual(kb.ROT, original_root)
        try:
            with kp.historisk_domkod(self.post):
                raise RuntimeError('consumer interrupted')
        except RuntimeError:
            pass
        self.assertEqual(kb.ROT, original_root)

    def test_changed_semantics_pin_or_old_wrapper_bytes_are_refused(self):
        for target in ('kritikbevis.py', 'kor_profil.py', 'pin'):
            post = copy.deepcopy(self.post)
            if target == 'pin': post['bedomningsbindning']['domkod_sha256'] = '0' * 64
            else: post['bindning']['verktyg'][target] = '0' * 64
            with self.subTest(target=target), self.assertRaises(kp.Vagrad):
                with kp.historisk_domkod(post): pass

    def fixture(self):
        loaded = receipt_file(self.root)
        receipt = json.loads(loaded.read_text())
        for row in receipt['underlag']:
            if row['fil'] in ('kandidat.png', 'referens.png'):
                row['obligatorisk'] = True
        loaded.write_text(json.dumps(receipt))
        self.post.update({'schema': 1, 'profil': 'kritik', 'mall': 'renderingslasning',
                          'laddning': {'fil': str(loaded), 'sha256': hashlib.sha256(loaded.read_bytes()).hexdigest()}})
        with kp.historisk_domkod(self.post):
            expected, underlag = kb.ur_laddning(loaded)
        self.post.update(bedomningsbindning=expected, bildbedomningsunderlag=underlag)
        run = self.root / 'runtime-source'
        run.mkdir()
        (run / 'KVITTO.json').write_text('{}')
        self.post['runtime_kvitto_sha256'] = hashlib.sha256((run / 'KVITTO.json').read_bytes()).hexdigest()
        self.post['resultat'] = {'run': str(run)}
        self.post['argv'] = ['python', '-B', '-m', 'runtime.web_critique', '--underlag', '/original/manifest.json',
                             '--fraga', '/original/question.md', '--schema', '/original/schema.json',
                             '--utforare', 'claude', '--modell', 'selected-model', '--etikett', 'old', '--tid', '600']
        path = self.root / 'KORNING-old.json'
        path.write_text(json.dumps(self.post))
        return loaded, path

    def test_consumer_uses_original_arguments_and_runtime_preflight_without_retemplating(self):
        loaded, path = self.fixture()
        args = SimpleNamespace(aterhamta=str(path), laddning=str(loaded), etikett='new', formtid=180)
        receipt = json.loads(loaded.read_text())
        actual_run = subprocess.run
        def run(cmd, **kwargs):
            if cmd[0] == 'git': return actual_run(cmd, **kwargs)
            return SimpleNamespace(returncode=0, stdout='form-preflight-ok\n', stderr='')
        with patch.object(kp.subprocess, 'run', side_effect=run) as calls:
            cmd, extra = kp.bygg_aterhamtning(args, {'python': 'python', 'kod': str(self.root)}, self.root,
                                            receipt, self.post['laddning']['sha256'])
        for flag in ('--underlag', '--fraga', '--schema'):
            self.assertEqual(cmd[cmd.index(flag) + 1], self.post['argv'][self.post['argv'].index(flag) + 1])
        self.assertEqual(cmd[cmd.index('--formfalt') + 1], 'summary')
        self.assertEqual(extra['bedomningsbindning'], self.post['bedomningsbindning'])
        self.assertEqual(extra['bildbedomningsunderlag'], self.post['bildbedomningsunderlag'])
        probe = [c for c in calls.call_args_list if c.args[0][0] != 'git']
        self.assertEqual(len(probe), 1)
        self.assertIn('verified_source', probe[0].args[0][3])

    def test_changed_loading_and_original_metadata_refuse_before_runtime_model(self):
        loaded, path = self.fixture()
        args = SimpleNamespace(aterhamta=str(path), laddning=str(loaded), etikett='new', formtid=180)
        with self.assertRaisesRegex(kp.Vagrad, 'laddningskvitto'):
            kp.bygg_aterhamtning(args, {}, self.root, {}, '0' * 64)
        new = {**self.post, 'formaterhamtning': {'korning': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}}
        new['bedomningsbindning'] = {**new['bedomningsbindning'], 'rackvidd': 'wider scope'}
        with self.assertRaisesRegex(kp.Vagrad, 'skiljer'):
            with kp.domkontext(new): pass

    def test_cli_refuses_new_material_or_model_in_form_only_mode(self):
        base = ['kritik', '--laddning', 'old.json', '--fall', 'fall', '--etikett', 'new', '--aterhamta', 'KORNING.json']
        self.assertEqual(kp.parse(base).formtid, 180)
        for flag in ('--filer', '--modell', '--parameter', '--bindning'):
            with self.subTest(flag=flag), self.assertRaises(kp.Vagrad): kp.parse(base + [flag, 'changed'])

    def test_quality_picture_enters_the_same_historical_context(self):
        # Exercise the public status consumer dispatch while leaving its normal
        # evidence checks in place. Missing source metadata must not look current.
        loaded, path = self.fixture()
        post = {**self.post, 'formaterhamtning': {'korning': str(path), 'sha256': '0' * 64}}
        with self.assertRaises(kp.Vagrad):
            with kp.domkontext(post): pass
        self.assertEqual(kvalitetsbild.kor_profil.domkontext, kp.domkontext)

    @staticmethod
    def write_json(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=1) + '\n')

    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def seal_runtime(self, run, receipt):
        # Same recursive output-map shape as Runtime. No model or live receipt
        # is implied by this synthetic transport/consumer fixture.
        receipt['outputs'] = {str(p.relative_to(run)): {'sha256': self.sha(p), 'bytes': p.stat().st_size}
                              for p in sorted(run.rglob('*')) if p.is_file() and p.name not in ('KVITTO.json', 'KVITTO.sha256')}
        self.write_json(run / 'KVITTO.json', receipt)
        (run / 'KVITTO.sha256').write_text(self.sha(run / 'KVITTO.json') + '  KVITTO.json\n')

    def recovery_fixture(self):
        loaded, original_path = self.fixture()
        oldrun = Path(self.post['resultat']['run'])
        images = self.post['bildbedomningsunderlag']['bilder']
        comparison = {'kandidatbild': images[0]['plats'], 'referensbild': images[1]['plats'],
                      **{k: images[1][k] for k in ('kalla', 'tid', 'vy', 'drag')},
                      'observation': 'syntetisk transportkontroll', 'konsekvens': 'ingen produktdom',
                      'beslut_och_skal': 'behåll testbilden för kontraktsprovet'}
        original = {'kriterieversion': kb.VERSION, 'bedomningsbindning': self.post['bedomningsbindning'],
                    'summary': 'Syntetiskt formprov. ' * 120, 'verdict': 'approved', 'blocking_findings': [],
                    'could_not_review': [], 'seen_files': [b['plats'] for b in images],
                    'referensjamforelser': [comparison], 'dagensjamforelser': []}
        stream = [{'type': 'system', 'subtype': 'init', 'session_id': 'synthetic-source'}]
        for index, image in enumerate(images):
            image_path = oldrun / 'arbetsyta' / image['plats']
            image_path.parent.mkdir(parents=True, exist_ok=True)
            image_path.write_bytes((self.root / 'kund' / image['fil']).read_bytes())
            stream += [{'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'name': 'Read',
                         'id': 'read-' + str(index), 'input': {'file_path': str(image_path)}}]}},
                       {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'tool_use_id': 'read-' + str(index),
                         'content': [{'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/png',
                                      'data': base64.b64encode(image_path.read_bytes()).decode()}}]}]}}]
        stream += [{'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'name': 'StructuredOutput',
                       'id': 'structured-original', 'input': original}]}},
                  {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'tool_use_id': 'structured-original',
                       'is_error': True, 'content': 'Output does not match required schema: /summary maxLength'}]}}]
        (oldrun / 'strom.jsonl').write_text('\n'.join(json.dumps(r) for r in stream) + '\n')
        self.write_json(oldrun / 'start.json', {'session_id': 'synthetic-source', 'argv': self.post['argv']})
        old_session = {'valid_terminal': False, 'end': 'tidsgrans', 'seconds': 600.6, 'usage': None}
        old_receipt = {'schema': 1, 'profile': 'kritik', 'outcome': 'tidsgrans', 'session': old_session,
                       'parameters': {'executor': 'claude'},
                       'underlag': [{'place': b['plats'], 'copy_sha256': b['sha256'], 'source_sha256': b['sha256']} for b in images],
                       'images': {'complete': True, 'delivered_or_opened': original['seen_files'],
                                  'how': 'opened with Read (from the stream)'}}
        self.seal_runtime(oldrun, old_receipt)
        self.post['runtime_kvitto_sha256'] = self.sha(oldrun / 'KVITTO.json')
        self.post['etikett'] = 'ursprung'
        self.post['bindning'].update(aktiv_release_config='ursprunglig-release', revision='produkt-revision', driftsattning='syntetisk')
        self.write_json(original_path, self.post)
        run = self.root / 'runtime-recovery'; run.mkdir()
        answer = {**original, 'summary': 'Syntetiskt formprov; ingen produktdom.'}
        self.write_json(run / 'original-svar.json', original)
        self.write_json(run / 'svar.json', answer)
        self.write_json(run / 'start.json', {'mode': 'format_recovery', 'source_run': str(oldrun)})
        (run / 'strom.jsonl').write_text('')  # No new image-session terminal is invented.
        sessions = []
        for directory, value in [('formrattning', {'summary': answer['summary']}),
                                  ('innebordskontroll', {'preserved': True, 'lost_or_changed': [], 'reason': 'Syntetiskt prov'})]:
            d = run / directory; d.mkdir()
            session = {'session_id': 'synthetic-' + directory, 'valid_terminal': True, 'images': 0,
                       'end': 'completed', 'seconds': 1, 'opened': ['FORM.json']}
            sessions.append(session)
            self.write_json(d / 'svar.json', value)
            self.write_json(d / 'SESSION.json', session)
            self.write_json(d / 'start.json', {'executor': 'claude', 'workspace': str(d / 'arbetsyta'), 'synthetic': True})
            self.write_json(d / 'schema.json', {'type': 'object', 'properties': {k: {} for k in value}, 'required': list(value)})
            (d / 'fraga.txt').write_text('Syntetisk textsession: ingen modell körs.\n')
            (d / 'strom.jsonl').write_text(json.dumps({'type': 'result', 'structured_output': value, 'is_error': False}) + '\n')
        provenance = {'source_run': str(oldrun), 'source_receipt_sha256': self.post['runtime_kvitto_sha256'],
                      'source_stream_sha256': self.sha(oldrun / 'strom.jsonl'), 'source_session': old_session,
                      'changed_fields': ['summary'], 'images_reopened': 0, 'sessions': sessions, 'error': None}
        self.write_json(run / 'FORMATERHAMTNING.json', provenance)
        receipt = {**old_receipt, 'outcome': 'svar_giltigt', 'format_recovery': provenance}
        self.seal_runtime(run, receipt)
        loaded_receipt = json.loads(loaded.read_text())
        release = {'config_sha256': 'aktuell-release', 'kod': str(self.root), 'python': sys.executable}
        post = {**copy.deepcopy(self.post), 'etikett': 'aterhamtad', 'aktiv_release': release,
                'bindning': kp.bindning_ur(SimpleNamespace(bindning=None), loaded_receipt, release),
                'resultat': {'run': str(run), 'outcome': 'svar_giltigt'}, 'exit': 0,
                'runtime_kvitto_sha256': self.sha(run / 'KVITTO.json'),
                'formaterhamtning': {'korning': str(original_path), 'sha256': self.sha(original_path),
                                     'falt': ['summary'], 'inga_nya_bildlasningar': True}}
        kp.aterhamtningsbindning(post, self.post)
        self.write_json(self.root / 'KORNING-new.json', post)
        return post, run, receipt, answer

    def test_complete_recovery_receipt_passes_actual_validator_and_historical_verdict(self):
        post, run, receipt, answer = self.recovery_fixture()
        kp.kontrollera_aterhamtningsbevis(post, run, receipt, answer)
        with kp.domkontext(post):
            self.assertEqual(kb.dom(answer, post['bedomningsbindning'], post['bildbedomningsunderlag'], receipt), 'ok')
        self.assertFalse(receipt['session']['valid_terminal'])
        self.assertEqual(len(receipt['format_recovery']['sessions']), 2)

    def test_each_required_output_is_hash_bound(self):
        post, run, receipt, answer = self.recovery_fixture()
        required = ['original-svar.json', 'FORMATERHAMTNING.json'] + [d + '/' + n
                    for d in ('formrattning', 'innebordskontroll')
                    for n in ('svar.json', 'SESSION.json', 'strom.jsonl', 'start.json', 'fraga.txt', 'schema.json')]
        for name in required:
            path = run / name; before = path.read_bytes()
            with self.subTest(output=name):
                path.write_bytes(before + b' ')
                with self.assertRaisesRegex(kp.Vagrad, 'bundna bevis'):
                    kp.kontrollera_aterhamtningsbevis(post, run, receipt, answer)
                path.write_bytes(before)
        kp.kontrollera_aterhamtningsbevis(post, run, receipt, answer)

    def test_source_stream_change_with_same_structured_answer_is_refused(self):
        post, run, receipt, answer = self.recovery_fixture()
        stream = Path(self.post['resultat']['run']) / 'strom.jsonl'
        stream.write_text(stream.read_text() + json.dumps({'type': 'system', 'subtype': 'changed'}) + '\n')
        with self.assertRaisesRegex(kp.Vagrad, 'råström'):
            kp.kontrollera_aterhamtningsbevis(post, run, receipt, answer)

    def test_recovery_provenance_scope_cannot_be_widened(self):
        post, run, receipt, answer = self.recovery_fixture()
        for key, value in [('source_receipt_sha256', '0' * 64), ('source_run', str(self.root / 'other')),
                           ('changed_fields', ['summary', 'verdict']), ('images_reopened', 1), ('error', 'failed')]:
            bad = copy.deepcopy(receipt); bad['format_recovery'][key] = value
            with self.subTest(field=key), self.assertRaisesRegex(kp.Vagrad, 'källkvitto eller avgränsning'):
                kp.kontrollera_aterhamtningsbevis(post, run, bad, answer)

    def test_rehashed_session_and_provenance_changes_still_refuse(self):
        post, run, receipt, answer = self.recovery_fixture()
        session_file = run / 'formrattning/SESSION.json'; old = session_file.read_bytes()
        altered = json.loads(old); altered['session_id'] = 'another-session'
        self.write_json(session_file, altered); self.seal_runtime(run, receipt)
        with self.assertRaisesRegex(kp.Vagrad, 'textsessionens bevis'):
            kp.kontrollera_aterhamtningsbevis(post, run, receipt, answer)
        session_file.write_bytes(old)
        provenance_file = run / 'FORMATERHAMTNING.json'
        altered = copy.deepcopy(receipt['format_recovery']); altered['source_session']['seconds'] = 1
        self.write_json(provenance_file, altered); self.seal_runtime(run, receipt)
        with self.assertRaisesRegex(kp.Vagrad, 'proveniens skiljer'):
            kp.kontrollera_aterhamtningsbevis(post, run, receipt, answer)

    def test_unqualified_text_sessions_and_semantic_changes_refuse(self):
        post, run, receipt, answer = self.recovery_fixture()
        for index in (0, 1):
            for key, value in [('valid_terminal', False), ('images', 1)]:
                bad = copy.deepcopy(receipt); bad['format_recovery']['sessions'][index][key] = value
                with self.subTest(session=index, field=key), self.assertRaisesRegex(kp.Vagrad, 'terminaler'):
                    kp.kontrollera_aterhamtningsbevis(post, run, bad, answer)
        audit = run / 'innebordskontroll/svar.json'
        self.write_json(audit, {'preserved': False, 'lost_or_changed': ['sakuppgift ändrad']})
        self.seal_runtime(run, receipt)
        with self.assertRaisesRegex(kp.Vagrad, 'innebördskontroll'):
            kp.kontrollera_aterhamtningsbevis(post, run, receipt, answer)

    def test_protected_verdict_findings_binding_and_source_answer_remain_immutable(self):
        post, run, receipt, answer = self.recovery_fixture()
        for key, value in [('verdict', 'changes_required'), ('blocking_findings', [{'finding': 'changed'}]),
                           ('could_not_review', ['missing view']), ('bedomningsbindning', {}), ('seen_files', [])]:
            with self.subTest(field=key), self.assertRaisesRegex(kp.Vagrad, 'ändrat dom'):
                kp.kontrollera_aterhamtningsbevis(post, run, receipt, {**answer, key: value})
        original_file = run / 'original-svar.json'
        altered = json.loads(original_file.read_text()); altered['summary'] = 'replaced source prose'
        self.write_json(original_file, altered); self.seal_runtime(run, receipt)
        with self.assertRaisesRegex(kp.Vagrad, 'råobjekt skiljer'):
            kp.kontrollera_aterhamtningsbevis(post, run, receipt, answer)

    def test_current_executor_binding_and_original_source_binding_stay_distinct(self):
        before = copy.deepcopy(self.post)
        post, run, receipt, answer = self.recovery_fixture()
        self.assertEqual(post['bindning']['verktyg'], kp.verktygshashar())
        self.assertEqual(post['bindning']['aktiv_release_config'], post['aktiv_release']['config_sha256'])
        self.assertEqual(post['bindning']['rot_git_head'], subprocess.check_output(['git', '-C', str(kp.ROT), 'rev-parse', 'HEAD'], text=True).strip())
        self.assertNotEqual(post['bindning']['rot_git_head'], before['bindning']['rot_git_head'])
        self.assertEqual(post['formaterhamtning']['ursprunglig_bindning'], self.post['bindning'])
        self.assertEqual(post['formaterhamtning']['konsument_hashar'], kp.verktygshashar())
        self.assertEqual(post['bindning']['revision'], 'produkt-revision')
        self.assertEqual(post['bindning']['driftsattning'], 'syntetisk')
        self.assertEqual(json.loads(Path(post['formaterhamtning']['korning']).read_text()), self.post)

    def test_quality_picture_shows_recovery_source_and_model_limitations_in_json_and_text(self):
        post, run, receipt, answer = self.recovery_fixture()
        rows = kvalitetsbild.samla(self.root, {'revision': 'produkt-revision', 'aktiv_release_config': 'aktuell-release'})
        recovered = next(r for r in rows if r['etikett'] == 'aterhamtad')
        self.assertEqual(recovered['status'], 'ok')
        self.assertEqual(recovered['formaterhamtning'], post['formaterhamtning'])
        self.assertEqual(recovered['kvitto']['format_recovery'], receipt['format_recovery'])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(kvalitetsbild.main(['--fall', str(self.root), '--ut', str(self.root/'kvalitetsbild.md'), '--json']), 0)
        exported = next(r for r in json.loads(output.getvalue())['rader'] if r['etikett'] == 'aterhamtad')
        self.assertEqual(exported['formaterhamtning'], post['formaterhamtning'])
        self.assertEqual(exported['format_recovery'], receipt['format_recovery'])
        self.assertEqual(len(rows), 2)
        self.assertNotEqual(next(r for r in rows if r['etikett'] == 'ursprung')['status'], 'ok')
        text = kvalitetsbild.rendera(rows, [])
        for expected in ('Formåterhämtning av', str(self.root / 'runtime-source'), 'utan giltig terminal',
                         'tidsgrans, 600.6 s', 'Endast summary', 'separat modellbedömning', '0 nya bildläsningar',
                         'Ursprunglig underkänd körning är bevarad'):
            self.assertIn(expected, text)
        old_release = kvalitetsbild.samla(self.root, {'aktiv_release_config': 'ursprunglig-release'})
        self.assertIn('utanför leveransen', next(r for r in old_release if r['etikett'] == 'aterhamtad')['status'])

    def test_recovery_receipt_without_consumer_provenance_is_refused(self):
        post, run, receipt, answer = self.recovery_fixture()
        post.pop('formaterhamtning')
        with self.assertRaisesRegex(kp.Vagrad, 'konsumentproveniens'):
            kp.kontrollera_aterhamtningsbevis(post, run, receipt, answer)

    def test_original_binding_copy_cannot_be_relabelled_as_current_execution(self):
        post, run, receipt, answer = self.recovery_fixture()
        post['formaterhamtning']['ursprunglig_bindning'] = copy.deepcopy(post['bindning'])
        with self.assertRaisesRegex(kp.Vagrad, 'ursprunglig|bindning'):
            kp.kontrollera_aterhamtningsbevis(post, run, receipt, answer)

    def test_real_consumer_postprocessing_records_specific_refusal_after_runtime_success(self):
        post, run, receipt, answer = self.recovery_fixture()
        # Runtime/model subprocess is the only execution double. The actual
        # consumer validator reads all files and detects this later corruption.
        (run / 'formrattning/SESSION.json').write_text('{}')
        loaded = Path(post['laddning']['fil'])
        args = ['kritik', '--laddning', str(loaded), '--fall', str(self.root), '--etikett', 'diagnos',
                '--aterhamta', post['formaterhamtning']['korning']]
        extra = {k: copy.deepcopy(post[k]) for k in ('mall', 'bedomningsbindning', 'bildbedomningsunderlag', 'formaterhamtning')}
        actual = subprocess.run
        def execute(cmd, **kwargs):
            if cmd[0] == 'git': return actual(cmd, **kwargs)
            self.assertEqual(cmd, ['synthetic-runtime-no-model'])
            return SimpleNamespace(returncode=0, stdout=json.dumps({'run': str(run), 'outcome': 'svar_giltigt'}) + '\n', stderr='')
        with patch.object(kp, 'runtime_root', return_value=self.root), patch.object(kp, 'aktiv_release', return_value=post['aktiv_release']), \
             patch.object(kp, 'bygg_aterhamtning', return_value=(['synthetic-runtime-no-model'], extra)), \
             patch.object(kp.subprocess, 'run', side_effect=execute), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(kp.run(args), 1)
        result = json.loads(next(self.root.glob('KORNING-*-diagnos.json')).read_text())
        self.assertEqual(result['exit'], 0)
        self.assertEqual(result['kvalitetsfel'], 'Vagrad')
        self.assertIn('formrattning/SESSION.json', result['kvalitetsstatus'])
        self.assertNotIn('saknat faktiskt svar', result['kvalitetsstatus'])


if __name__ == '__main__': unittest.main()
