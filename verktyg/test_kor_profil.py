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


def fake_kontor(tmp, svar=None, kod=0):
    """Ett låtsaskontor vars `tools/partner.py lasare` ger läsarnas val och bokför sin miljö; provet rör aldrig kontorets
    riktiga val."""
    kontor = tmp / 'kontor'
    (kontor / 'tools').mkdir(parents=True, exist_ok=True)
    svar = svar if svar is not None else {'schema': 'lasarval/1', 'modell': None, 'utforare': None}
    (kontor / 'tools/partner.py').write_text(
        'import json, os, sys\nfrom pathlib import Path\nassert sys.argv[1:] == ["lasare"], sys.argv\n'
        'Path(__file__).with_name("miljo.json").write_text(json.dumps(sorted(os.environ)))\n'
        'print(json.dumps(%r))\nsys.exit(%d)\n' % (svar, kod))
    return kontor


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
        from test_kritikbevis import bildfixture
        kund=tmp/'kund'; d=bildfixture(kund)
        put('underlag/kund/BEVISKRAV.json','BEVISKRAV.json','kund',(kund/'BEVISKRAV.json').read_text())
        put('underlag/kund/BEDOMNINGSUNDERLAG.json', 'BEDOMNINGSUNDERLAG.json', 'kund', (kund/'BEDOMNINGSUNDERLAG.json').read_text())
        put('underlag/profession/kritik/BEDOMNING-v2.md', 'kritik/BEDOMNING-v2.md', 'profession', (ROT/'kritik/BEDOMNING-v2.md').read_text())
        for b in d['bilder']:
            rel='underlag/kund/'+b['fil']; target=ws/rel;target.write_bytes((kund/b['fil']).read_bytes())
            rows.append({'plats':rel,'fil':b['fil'],'klass':'kund','status':'laddad','delar':'bild','sha256':b['sha256']})
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
        self.kontor = fake_kontor(self.tmp)

    def run_cli(self, root, *args):
        env = dict(os.environ, NR_HOST_ROOT=str(root), NR_KONTOR_ROOT=str(self.kontor))
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

    def test_avskarmad_mall_bar_bara_bilden(self):
        args = ['kritik', '--laddning', str(self.laddning), '--fall', str(self.fall), '--etikett', 'k-1', '--mall', 'femsekunderstest',
                '--filer', str(self.filer), '--utforare', 'claude', '--modell', 'claude-opus-5', '--torr']
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


class Lasarval(Rig):
    """Läsarnas val i Flödet (kontorets `partner.py lasare`) avgör kritikens och provarens modell."""

    def setUp(self):
        super().setUp()
        self.root = fake_runtime(self.tmp, PROFIL['vyer'], PROFIL['axe_taggar'], parametrar=False)
        self.filer = self.tmp / 'filer.json'
        self.filer.write_text(json.dumps([{'kalla': '/tmp/a.png', 'plats': 'VYER/a.png', 'vad': 'bild'}]))
        self.uppgift = self.tmp / 'UPPGIFT.md'
        self.uppgift.write_text('Startadress: https://x.test/\nDitt handlingskommando är exakt: ./handling\n\nMål: titta.\n')

    def val(self, modell, utforare, anstrangning=None):
        fake_kontor(self.tmp, {'schema': 'lasarval/1', 'modell': modell, 'utforare': utforare, 'anstrangning': anstrangning})

    def kritik(self, *extra):
        return self.run_cli(self.root, 'kritik', '--laddning', str(self.laddning), '--fall', str(self.fall), '--etikett', 'l-1',
                            '--mall', 'femsekunderstest', '--filer', str(self.filer), *extra, '--torr')

    def provare(self, *extra):
        return self.run_cli(self.root, 'provare', '--laddning', str(self.laddning_provare), '--fall', str(self.fall), '--etikett',
                            'l-2', '--start', 'https://x.test/', '--tillatna', 'https://x.test', '--uppgift', str(self.uppgift),
                            '--vy', 'mobil', *extra, '--torr')

    @staticmethod
    def modell_i(argv):
        return argv[argv.index('--utforare') + 1], argv[argv.index('--modell') + 1]

    def test_valet_i_flodet_ger_kritikens_och_provarens_modell(self):
        self.val('gpt-6-astra', 'codex')
        for kor in (self.kritik, self.provare):
            with self.subTest(profil=kor.__name__):
                code, out = kor()
                self.assertEqual(code, 0, out)
                self.assertEqual(self.modell_i(out['argv']), ('codex', 'gpt-6-astra'))
                self.assertEqual(out['lasarval'], {'kalla': 'flodet', 'modell': 'gpt-6-astra', 'utforare': 'codex',
                                                   'anstrangning_sparad': None, 'anstrangning': None, 'anstrangning_fran': 'profilen'})
                self.assertNotIn('--anstrangning', out['argv'])
                self.assertEqual(out['bindning']['utforare'], 'codex')

    def test_ett_annat_val_i_argumenten_vagras_och_samma_godtas(self):
        self.val('claude-opus-5', 'claude')
        for extra in (('--modell', 'claude-sonnet-5'), ('--utforare', 'codex'), ('--utforare', 'codex', '--modell', 'gpt-6-astra')):
            with self.subTest(extra=extra):
                code, out = self.kritik(*extra)
                self.assertEqual(code, 2, out)
                self.assertIn('läsarnas val i Flödet är claude-opus-5 (claude)', out['skal'])
        code, out = self.provare('--utforare', 'claude', '--modell', 'claude-opus-5')
        self.assertEqual(code, 0, out)
        self.assertEqual(out['lasarval']['kalla'], 'flodet')

    def test_utan_val_anger_sessionen_bada_som_forut(self):
        code, out = self.kritik()
        self.assertEqual(code, 2, out); self.assertIn('ange --utforare och --modell', out['skal'])
        code, out = self.provare('--modell', 'claude-opus-5')
        self.assertEqual(code, 2, out)
        code, out = self.kritik('--utforare', 'claude', '--modell', 'claude-sonnet-5')
        self.assertEqual(code, 0, out)
        self.assertEqual(self.modell_i(out['argv']), ('claude', 'claude-sonnet-5'))
        self.assertEqual(out['lasarval'], {'kalla': 'argument', 'modell': 'claude-sonnet-5', 'utforare': 'claude',
                                           'anstrangning_sparad': None, 'anstrangning': None, 'anstrangning_fran': 'profilen'})

    def test_ett_val_som_inte_gar_att_lasa_vagras(self):
        for svar, kod in (({'schema': 'lasarval/1', 'fel': 'installningar.json går inte att läsa'}, 1),
                          ({'schema': 'annat/1', 'modell': None, 'utforare': None}, 0),
                          ({'schema': 'lasarval/1', 'modell': '--flagga', 'utforare': 'claude'}, 0),
                          ({'schema': 'lasarval/1', 'modell': 'gpt-6-astra', 'utforare': None}, 0),
                          ({'schema': 'lasarval/1', 'modell': 'gpt-6-astra', 'utforare': 'codex', 'anstrangning': '--max'}, 0),
                          ({'schema': 'lasarval/1', 'modell': 'gpt-6-astra', 'utforare': 'codex', 'anstrangning': 'MAX'}, 0),
                          ({'schema': 'lasarval/1', 'modell': 'gpt-6-astra', 'utforare': 'codex', 'anstrangning': 5}, 0),
                          ({'schema': 'lasarval/1', 'modell': None, 'utforare': None, 'anstrangning': 'max'}, 0)):
            with self.subTest(svar=svar):
                fake_kontor(self.tmp, svar, kod)
                code, out = self.kritik('--utforare', 'claude', '--modell', 'claude-opus-5')
                self.assertEqual(code, 2, out)
                self.assertIn('läsarnas val', out['skal'])

    def test_valets_niva_skickas_nar_den_aktiva_releasen_tar_en(self):
        # releasens kritik och provare tar en nivå (Runtime D046)
        (self.root / '.runtime/ap10/releases/x/runtime/runtime/web_common.py').write_text('def reader_effort(effort):\n    return effort\n')
        self.val('claude-opus-5-5', 'claude', 'max')
        for kor in (self.kritik, self.provare):
            with self.subTest(profil=kor.__name__):
                code, out = kor()
                self.assertEqual(code, 0, out)
                self.assertEqual(out['argv'][out['argv'].index('--anstrangning') + 1], 'max')
                self.assertEqual(out['argv'].count('--anstrangning'), 1)
                self.assertEqual(out['aktiv_release']['tar_niva'], True)
                self.assertEqual(out['lasarval'], {'kalla': 'flodet', 'modell': 'claude-opus-5-5', 'utforare': 'claude',
                                                   'anstrangning_sparad': 'max', 'anstrangning': 'max', 'anstrangning_fran': 'lasarna'})

    def test_en_release_utan_niva_far_ingen_och_profilen_kor_sin_egen(self):
        self.val('claude-opus-5-5', 'claude', 'max')
        for kor in (self.kritik, self.provare):
            with self.subTest(profil=kor.__name__):
                code, out = kor()
                self.assertEqual(code, 0, out)
                self.assertNotIn('--anstrangning', out['argv'])
                self.assertEqual(out['aktiv_release']['tar_niva'], False)
                self.assertEqual(out['lasarval']['anstrangning'], None)
                self.assertEqual(out['lasarval']['anstrangning_sparad'], 'max')
                self.assertEqual(out['lasarval']['anstrangning_fran'], 'profilen: den aktiva releasen tar ingen nivå')

    def test_utan_kontor_vagras_kritik_och_provare_men_inte_matning(self):
        self.kontor = self.tmp / 'inget-kontor'
        code, out = self.kritik('--utforare', 'claude', '--modell', 'claude-opus-5')
        self.assertEqual(code, 2, out); self.assertIn('kontoret hittas inte', out['skal'])
        code, out = self.run_cli(self.root, 'matning', '--laddning', str(self.laddning_matning), '--fall', str(self.fall),
                                 '--etikett', 'l-3', '--mal', 'https://example.test/', '--torr')
        self.assertEqual(code, 0, out)
        self.assertNotIn('lasarval', out)

    def test_kontorets_lasning_far_en_ren_miljo(self):
        self.val('gpt-6-astra', 'codex')
        env_fore = os.environ.get('PARTNER_DATA')
        os.environ['PARTNER_DATA'] = str(self.tmp / 'annan-data')
        try:
            code, out = self.kritik()
        finally:
            if env_fore is None:
                os.environ.pop('PARTNER_DATA', None)
            else:
                os.environ['PARTNER_DATA'] = env_fore
        self.assertEqual(code, 0, out)
        miljo = json.loads((self.kontor / 'tools/miljo.json').read_text())
        self.assertNotIn('PARTNER_DATA', miljo); self.assertNotIn('NR_HOST_ROOT', miljo); self.assertNotIn('NR_KONTOR_ROOT', miljo)


class HemligVag(unittest.TestCase):
    def test_bokford_argv_doljer_undantagsfilens_sokvag_men_andrar_inte_kommandot(self):
        cmd = ['python', '-m', 'runtime.web_measure', '--undantag-fil', '/privat/hemlig.txt', '--mal', 'https://exempel.test/']
        self.assertEqual(kor_profil.utan_hemlig_vag(cmd), ['python', '-m', 'runtime.web_measure', '--undantag-fil', '<undantag-fil>', '--mal', 'https://exempel.test/'])
        self.assertEqual(cmd[4], '/privat/hemlig.txt')
        self.assertEqual(kor_profil.utan_hemlig_vag(['x', '--mal', 'y']), ['x', '--mal', 'y'])


if __name__ == '__main__':
    unittest.main()
