"""Formåterhämtning använder originalets frysta dom utan historisk Python-import."""
import copy
import hashlib
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


if __name__ == '__main__': unittest.main()
