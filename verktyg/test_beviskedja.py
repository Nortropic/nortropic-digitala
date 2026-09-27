"""Beviskedjans fynd A, B och C (HELHET-20260927 etapp 4): laddade versioner konsumeras och verifieras, kontextpolicy per
kritikmall med avskärmat femsekunderstest, och kvalitetsbilden döljer ingen körning."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROT = HERE.parent
sys.path.insert(0, str(HERE))
import kvalitetsbild  # noqa: E402
from test_kor_profil import fake_runtime, receipt_file, PROFIL  # noqa: E402


class Rig(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='nd-bevis-'))
        self.fall = self.tmp / 'fall'
        self.fall.mkdir()
        self.root = fake_runtime(self.tmp, PROFIL['vyer'], PROFIL['axe_taggar'], parametrar=True)
        self.filer = self.tmp / 'filer.json'
        self.filer.write_text(json.dumps([{'kalla': '/tmp/a.png', 'plats': 'VYER/a.png', 'vad': 'bild'}]))

    def run_cli(self, *args):
        env = dict(os.environ, NR_HOST_ROOT=str(self.root))
        done = subprocess.run([sys.executable, '-B', str(HERE / 'kor_profil.py'), *args], capture_output=True, text=True, env=env, cwd=self.tmp)
        return done.returncode, json.loads(done.stdout.strip()) if done.stdout.strip() else {'stderr': done.stderr}


class A_LaddningKontraAnvandning(Rig):
    def test_matprofilen_lases_ur_den_laddade_arbetsytan_inte_ur_repot(self):
        annan = dict(PROFIL); annan['vyer'] = {'liten-320': {'width': 320, 'height': 480, 'deviceScaleFactor': 1, 'isMobile': True, 'hasTouch': True}}
        laddning = receipt_file(self.tmp, 'matning', profil_text=json.dumps(annan), name='L-annan.json')
        code, out = self.run_cli('matning', '--laddning', str(laddning), '--fall', str(self.fall), '--etikett', 'a-1', '--fil', '/tmp/x.html', '--torr')
        self.assertEqual(code, 0, out)
        self.assertEqual(out['argv'][out['argv'].index('--vyer') + 1], 'liten-320=320x480@1m', 'värdena kom ur arbetsytan, inte ur repots levande PROFIL.json')

    def test_fel_stegs_kvitto_vagras(self):
        laddning = receipt_file(self.tmp, 'kritik', name='L-kritik.json')
        code, out = self.run_cli('matning', '--laddning', str(laddning), '--fall', str(self.fall), '--etikett', 'a-2', '--fil', '/tmp/x.html', '--torr')
        self.assertEqual(code, 2, out)
        self.assertIn('kräver steget', out['skal'])

    def test_andrad_laddad_fil_vagras(self):
        laddning = receipt_file(self.tmp, 'matning', name='L-andrad.json')
        receipt = json.loads(laddning.read_text())
        Path(receipt['arbetsyta'], 'underlag/profession/matning/PROFIL.json').write_text('{"andrad": true}')
        code, out = self.run_cli('matning', '--laddning', str(laddning), '--fall', str(self.fall), '--etikett', 'a-3', '--fil', '/tmp/x.html', '--torr')
        self.assertEqual(code, 2, out)
        self.assertIn('ändrat sedan kvittot', out['skal'])

    def test_bindningen_bokfors_i_korningen(self):
        laddning = receipt_file(self.tmp, 'matning', name='L-bind.json')
        code, out = self.run_cli('matning', '--laddning', str(laddning), '--fall', str(self.fall), '--etikett', 'a-4', '--fil', '/tmp/x.html', '--bindning', 'revision=abc123', '--torr')
        self.assertEqual(code, 0, out)
        b = out['bindning']
        self.assertEqual((b['steg'], b['revision'], b['mandat'], b['utforare']), ('matning', 'abc123', 'staende', 'claude'))
        self.assertIn('kor_profil.py', b['verktyg'])
        self.assertEqual(len(b['verktyg']['kor_profil.py']), 64)


class B_LackageTillBlindBedomning(Rig):
    def setUp(self):
        super().setUp()
        self.laddning = receipt_file(self.tmp, 'kritik', name='L-kritik.json')

    def kritik(self, mall, filer=None, *extra):
        return self.run_cli('kritik', '--laddning', str(self.laddning), '--fall', str(self.fall), '--etikett', 'b-' + mall[:6], '--mall', mall,
                            '--filer', str(filer or self.filer), '--utforare', 'claude', '--modell', 'claude-opus-5', *extra, '--torr')

    def test_femsekunderstestet_far_varken_brief_eller_professionstext(self):
        code, out = self.kritik('femsekunderstest')
        self.assertEqual(code, 0, out)
        self.assertEqual(out['manifest_platser'], ['VYER/a.png'])
        self.assertTrue(out['kontext_policy']['avskarmad'])

    def test_femsekunderstestet_vagrar_parametrar_som_kan_bara_briefen(self):
        code, out = self.kritik('femsekunderstest', None, '--parameter', 'KONTEXT=briefens riktning')
        self.assertEqual(code, 2, out)
        self.assertIn('inga --parameter', out['skal'])

    def test_avskarmad_vagran_galler_ord_inte_delstrangar(self):
        filer = self.tmp / 'filer-ordgrans.json'
        filer.write_text(json.dumps([{'kalla': '/tmp/kritikvy.png', 'plats': 'VYER/kritikvy-390.png', 'vad': 'bild'}]))
        code, out = self.kritik('femsekunderstest', filer)
        self.assertEqual(code, 0, out)
        for plats in ('VYER/kritik-svar.png', 'VYER/briefen.png', 'VYER/researchens-bild.png'):
            filer.write_text(json.dumps([{'kalla': '/tmp/a.png', 'plats': plats, 'vad': 'bild'}]))
            code, out = self.kritik('femsekunderstest', filer)
            self.assertEqual(code, 2, (plats, out))

    def test_femsekunderstestet_vagrar_bilagor_som_kan_bara_facit(self):
        filer = self.tmp / 'filer-brief.json'
        filer.write_text(json.dumps([{'kalla': '/tmp/a.png', 'plats': 'VYER/a.png', 'vad': 'bild'}, {'kalla': '/tmp/PROJECT-BRIEF.md', 'plats': 'KUND/PROJECT-BRIEF.md', 'vad': 'brief'}]))
        code, out = self.kritik('femsekunderstest', filer)
        self.assertEqual(code, 2, out)
        self.assertIn('avskärmad', out['skal'])

    def test_briefstyrd_kritik_far_brief_och_professionstext(self):
        self.filer.write_text('[]')
        code, out = self.kritik('renderingslasning', None, '--parameter', 'NUMMER=1', '--parameter', 'ANTAL=1', '--parameter', 'VAD=x', '--parameter', 'KUND=k')
        self.assertEqual(code, 0, out)
        self.assertIn('KUND/PROJECT-BRIEF.md', out['manifest_platser'])
        self.assertIn('UNDERLAG/SKILL.md', out['manifest_platser'])
        self.assertNotIn('UNDERLAG/FRAGA-femsekunderstest.md', out['manifest_platser'], 'andra mallar följer aldrig med')


class C_KvalitetsbildensGiltighet(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='nd-kb-'))
        self.fall = self.tmp / 'fall'; self.fall.mkdir()
        self.laddning = self.tmp / 'LADDNING.json'; self.laddning.write_text('{"schema": 1, "steg": "matning"}')
        self.ladd_sha = hashlib.sha256(self.laddning.read_bytes()).hexdigest()

    def korning(self, name, outcome='klar', bindning=None, kvitto=True, hash_ok=True, run=True):
        rundir = self.tmp / ('run-' + name)
        if run:
            rundir.mkdir()
            if kvitto:
                (rundir / 'KVITTO.json').write_text(json.dumps({'outcome': outcome, 'profile': 'matning'}))
                (rundir / 'KVITTO.sha256').write_text((hashlib.sha256((rundir / 'KVITTO.json').read_bytes()).hexdigest() if hash_ok else 'a' * 64) + '  KVITTO.json\n')
                (rundir / 'SAMMANFATTNING.json').write_text(json.dumps({'views': {}}))
        post = {'schema': 1, 'runtime_kvitto_sha256':hashlib.sha256((rundir/'KVITTO.json').read_bytes()).hexdigest() if run and kvitto else None, 'profil': 'matning', 'etikett': name, 'exit': 0, 'resultat': {'run': str(rundir), 'outcome': outcome},
                'laddning': {'fil': str(self.laddning), 'sha256': self.ladd_sha, 'steg': 'matning'}, 'bindning': bindning or {}}
        (self.fall / ('KORNING-20260927T%s-matning-%s.json' % (name.zfill(6)[-6:], name))).write_text(json.dumps(post))

    def test_varje_brist_visas_och_bara_ok_inom_leveransen_raknas(self):
        self.korning('ok', bindning={'revision': 'r1'})
        self.korning('gammal', bindning={'revision': 'r0'})
        self.korning('trasig', hash_ok=False, bindning={'revision': 'r1'})
        self.korning('borta', run=False, bindning={'revision': 'r1'})
        self.korning('fel', outcome='avbruten', bindning={'revision': 'r1'})
        (self.fall / 'KORNING-20260927T000000-matning-korrupt.json').write_text('{not json')
        rows = kvalitetsbild.samla(self.fall, {'revision': 'r1'})
        status = {r['fil'].split('-matning-')[-1].replace('.json', ''): r['status'] for r in rows}
        self.assertEqual(status['ok'], 'ok')
        self.assertTrue(status['gammal'].startswith('utanför leveransen'))
        self.assertTrue(status['trasig'].startswith('kvittohash'))
        self.assertTrue(status['borta'].startswith('saknas'))
        self.assertTrue(status['fel'].startswith('underkänd'))
        self.assertTrue(status['korrupt'].startswith('korrupt'))
        text = kvalitetsbild.rendera(rows, None, {'revision': 'r1'})
        self.assertIn('Aktuella leveransbevis: 1. Historik eller utanför kvalitetsgrinden: 5.', text)
        for name in ('gammal', 'trasig', 'borta', 'fel', 'korrupt'):
            self.assertIn(name, text)
        self.assertIn('kritik: INGEN aktuell körning', text)

    def test_andrat_laddningskvitto_gor_korningen_inaktuell(self):
        self.korning('x', bindning={'revision': 'r1'})
        self.laddning.write_text('{"schema": 1, "steg": "matning", "andrad": true}')
        rows = kvalitetsbild.samla(self.fall, {'revision': 'r1'})
        self.assertTrue(rows[0]['status'].startswith('inaktuell'))

    def test_utan_leverans_sags_det_tydligt(self):
        self.korning('x')
        text = kvalitetsbild.rendera(kvalitetsbild.samla(self.fall, None), None, None)
        self.assertIn('INTE bunden till någon leverans', text)


if __name__ == '__main__':
    unittest.main()
