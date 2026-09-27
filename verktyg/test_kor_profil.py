"""Prov för kor_profil: kommandobygge mot en låtsas-Runtime (torrkörning), Digitalas val kontra kodens värden, mallar."""
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
import kor_profil  # noqa: E402

PROFIL = json.loads((ROT / 'matning/PROFIL.json').read_text())


def fake_runtime(tmp, viewports, axe_tags, parametrar):
    root = tmp / 'rt'
    release = root / '.runtime/ap10/releases/x'
    (release / 'runtime/runtime').mkdir(parents=True)
    (release / 'runtime/runtime/__init__.py').write_text('')
    (release / 'runtime/runtime/web_measure.py').write_text(
        'VIEWPORTS = %r\nAXE_TAGS = %r\n%s' % (viewports, axe_tags, "PARAMETRAR = ('vyer', 'axe-taggar')\n" if parametrar else ''))
    (release / 'config.json').write_text('{"schema": 1}')
    import hashlib
    (root / '.runtime/ap10').mkdir(parents=True, exist_ok=True)
    (root / '.runtime/ap10/active.json').write_text(json.dumps({'config': str(release / 'config.json'),
                                                               'sha256': hashlib.sha256((release / 'config.json').read_bytes()).hexdigest()}))
    (root / '.runtime/temporal-venv/bin').mkdir(parents=True)
    os.symlink(sys.executable, root / '.runtime/temporal-venv/bin/python')
    return root


def receipt_file(tmp, steg='kritik', profil_text=None, name='LADDNING.json'):
    """Ett laddningskvitto med arbetsyta: kritik-steget bär repots tre mallar, matning-steget PROFIL.json; varje rad har sha256."""
    import hashlib
    ws = tmp / ('arbetsyta-' + steg)
    rows = []
    def put(rel, fil, klass, text, delar='hela'):
        p = ws / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text)
        rows.append({'plats': rel, 'fil': fil, 'klass': klass, 'status': 'laddad', 'delar': delar, 'sha256': hashlib.sha256(text.encode()).hexdigest()})
    if steg == 'kritik':
        for mall in ('designkritik-komp', 'renderingslasning', 'femsekunderstest'):
            put('underlag/profession/kritik/FRAGA-%s.md' % mall, 'kritik/FRAGA-%s.md' % mall, 'profession', (ROT / ('kritik/FRAGA-%s.md' % mall)).read_text(), 'mallen')
            put('underlag/profession/kritik/SCHEMA-%s.json' % mall, 'kritik/SCHEMA-%s.json' % mall, 'profession', (ROT / ('kritik/SCHEMA-%s.json' % mall)).read_text(), 'schemat')
        put('underlag/profession/kunskap/externa/SKILL.md', 'kunskap/externa/SKILL.md', 'profession', 'kalibrering', 'delar')
    elif steg == 'matning':
        put('underlag/profession/matning/PROFIL.json', 'matning/PROFIL.json', 'profession', profil_text or (ROT / 'matning/PROFIL.json').read_text())
    else:
        put('underlag/profession/provare/UPPGIFT-MALL.md', 'provare/UPPGIFT-MALL.md', 'profession', 'mall')
    put('underlag/kund/PROJECT-BRIEF.md', 'PROJECT-BRIEF.md', 'kund', 'brief', '§5')
    rows.append({'plats': None, 'fil': 'x', 'klass': 'kund', 'status': 'saknas (valfri)', 'delar': 'x'})
    receipt = {'schema': 1, 'steg': steg, 'mandat': 'staende', 'bestallning': None, 'utforare': 'claude', 'kundmapp': str(tmp / 'kund'), 'arbetsyta': str(ws), 'rot_git_head': 'abc', 'sha256_over_underlag': 'f' * 64, 'underlag': rows}
    path = tmp / name
    path.write_text(json.dumps(receipt))
    return path


class Rig(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='nd-kor-'))
        self.fall = self.tmp / 'fall'
        self.fall.mkdir()
        self.laddning = receipt_file(self.tmp, 'kritik')
        self.laddning_matning = receipt_file(self.tmp, 'matning', name='LADDNING-matning.json')
        self.laddning_provare = receipt_file(self.tmp, 'provare', name='LADDNING-provare.json')

    def run_cli(self, root, *args):
        env = dict(os.environ, NR_HOST_ROOT=str(root))
        done = subprocess.run([sys.executable, '-B', str(HERE / 'kor_profil.py'), *args], capture_output=True, text=True, env=env, cwd=self.tmp)
        return done.returncode, json.loads(done.stdout.strip()) if done.stdout.strip() else {'stderr': done.stderr}


class Matning(Rig):
    def test_utan_parametrar_kravs_lika_varden_och_argv_saknar_vyer(self):
        root = fake_runtime(self.tmp, PROFIL['vyer'], PROFIL['axe_taggar'], parametrar=False)
        code, out = self.run_cli(root, 'matning', '--laddning', str(self.laddning_matning), '--fall', str(self.fall), '--etikett', 'prov-1', '--mal', 'https://example.test/', '--torr')
        self.assertEqual(code, 0, out)
        self.assertTrue(out['torr'])
        self.assertIn('runtime.web_measure', out['argv'])
        self.assertNotIn('--vyer', out['argv'])
        self.assertIn('lika med kodens standardvärden', out['hur'])
        self.assertEqual(out['argv'][out['argv'].index('--delar') + 1], ','.join(PROFIL['delar']))
        self.assertEqual(list(self.fall.iterdir()), [], 'torrkörning skriver ingen KORNING')

    def test_med_parametrar_skickas_digitalas_val(self):
        root = fake_runtime(self.tmp, {'annan': {'width': 1, 'height': 1, 'deviceScaleFactor': 1, 'isMobile': False, 'hasTouch': False}}, ['wcag2a'], parametrar=True)
        code, out = self.run_cli(root, 'matning', '--laddning', str(self.laddning_matning), '--fall', str(self.fall), '--etikett', 'prov-2', '--fil', '/tmp/x.html', '--torr')
        self.assertEqual(code, 0, out)
        argv = out['argv']
        self.assertEqual(argv[argv.index('--vyer') + 1], 'mobil-390=390x844@2m,desktop-1440=1440x900@1d')
        self.assertEqual(argv[argv.index('--axe-taggar') + 1], ','.join(PROFIL['axe_taggar']))

    def test_avvikande_frysta_varden_utan_parametrar_vagras(self):
        root = fake_runtime(self.tmp, PROFIL['vyer'], ['wcag2a'], parametrar=False)
        code, out = self.run_cli(root, 'matning', '--laddning', str(self.laddning_matning), '--fall', str(self.fall), '--etikett', 'prov-3', '--mal', 'https://example.test/', '--torr')
        self.assertEqual(code, 2, out)
        self.assertIn('skiljer sig', out['skal'])

    def test_ogiltig_etikett_och_saknad_fallmapp_vagras(self):
        root = fake_runtime(self.tmp, PROFIL['vyer'], PROFIL['axe_taggar'], parametrar=False)
        code, out = self.run_cli(root, 'matning', '--laddning', str(self.laddning_matning), '--fall', str(self.fall), '--etikett', 'Stor', '--mal', 'https://x/', '--torr')
        self.assertEqual(code, 2)
        code, out = self.run_cli(root, 'matning', '--laddning', str(self.laddning_matning), '--fall', str(self.tmp / 'finns-inte'), '--etikett', 'ok', '--mal', 'https://x/', '--torr')
        self.assertEqual(code, 2)


class Kritik(Rig):
    def setUp(self):
        super().setUp()
        self.root = fake_runtime(self.tmp, PROFIL['vyer'], PROFIL['axe_taggar'], parametrar=False)
        self.filer = self.tmp / 'filer.json'
        self.filer.write_text(json.dumps([{'kalla': '/tmp/a.png', 'plats': 'VYER/a.png', 'vad': 'bild'}]))

    def test_platshallare_fylls_och_underlaget_laggs_till(self):
        args = ['kritik', '--laddning', str(self.laddning), '--fall', str(self.fall), '--etikett', 'k-1', '--mall', 'femsekunderstest',
                '--filer', str(self.filer), '--utforare', 'claude', '--modell', 'claude-opus-5', '--parameter', 'KONTEXT=Sajten är en kvalitetsdemo.', '--torr']
        code, out = self.run_cli(self.root, *args)
        self.assertEqual(code, 0, out)
        self.assertEqual(out['mall'], 'femsekunderstest')
        self.assertEqual(out['antal_filer'], 1, 'femsekunderstestet är avskärmat: varken kundfil eller professionstext följer med')
        self.assertEqual(out['manifest_platser'], ['VYER/a.png'])
        self.assertIn('runtime.web_critique', out['argv'])

    def test_ofyllda_platshallare_vagras(self):
        args = ['kritik', '--laddning', str(self.laddning), '--fall', str(self.fall), '--etikett', 'k-2', '--mall', 'designkritik-komp',
                '--filer', str(self.filer), '--utforare', 'codex', '--modell', 'gpt-6-astra', '--parameter', 'KOMP=A', '--torr']
        code, out = self.run_cli(self.root, *args)
        self.assertEqual(code, 2, out)
        self.assertIn('ofyllda platshållare', out['skal'])
        self.assertIn('{{KUND}}', out['skal'])

    def test_okand_mall_vagras(self):
        code, out = self.run_cli(self.root, 'kritik', '--laddning', str(self.laddning), '--fall', str(self.fall), '--etikett', 'k-3', '--mall', 'x',
                                 '--filer', str(self.filer), '--utforare', 'claude', '--modell', 'm', '--torr')
        self.assertEqual(code, 2)


class Provare(Rig):
    def setUp(self):
        super().setUp()
        self.root = fake_runtime(self.tmp, PROFIL['vyer'], PROFIL['axe_taggar'], parametrar=False)

    def test_uppgift_med_platshallare_vagras_och_fylld_uppgift_binds(self):
        uppgift = self.tmp / 'UPPGIFT.md'
        uppgift.write_text((ROT / 'provare/UPPGIFT-MALL.md').read_text())
        base = ['provare', '--laddning', str(self.laddning_provare), '--fall', str(self.fall), '--etikett', 'p-1', '--start', 'https://x.test/',
                '--tillatna', 'https://x.test', '--uppgift', str(uppgift), '--vy', 'mobil', '--utforare', 'claude', '--modell', 'claude-opus-5', '--torr']
        code, out = self.run_cli(self.root, *base)
        self.assertEqual(code, 2, out)
        self.assertIn('ofyllda platshållare', out['skal'])
        uppgift.write_text('Startadress: https://x.test/\nDitt handlingskommando är exakt: ./handling\n\nMål: titta.\n')
        code, out = self.run_cli(self.root, *base, '--bindning', 'commit=abc')
        self.assertEqual(code, 0, out)
        argv = out['argv']
        self.assertIn('runtime.web_visitor', argv)
        bindningar = [argv[i + 1] for i, a in enumerate(argv) if a == '--bindning']
        self.assertIn('commit=abc', bindningar)
        self.assertTrue(any(b.startswith('laddning=') for b in bindningar))
        self.assertIn('steg=provare', bindningar)


class HemligVag(unittest.TestCase):
    def test_bokford_argv_doljer_undantagsfilens_sokvag_men_andrar_inte_kommandot(self):
        cmd = ['python', '-m', 'runtime.web_measure', '--undantag-fil', '/privat/hemlig.txt', '--mal', 'https://exempel.test/']
        self.assertEqual(kor_profil.utan_hemlig_vag(cmd), ['python', '-m', 'runtime.web_measure', '--undantag-fil', '<undantag-fil>', '--mal', 'https://exempel.test/'])
        self.assertEqual(cmd[4], '/privat/hemlig.txt')
        self.assertEqual(kor_profil.utan_hemlig_vag(['x', '--mal', 'y']), ['x', '--mal', 'y'])


if __name__ == '__main__':
    unittest.main()
