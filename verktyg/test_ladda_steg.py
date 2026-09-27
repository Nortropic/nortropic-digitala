"""Prov för ladda_steg: legitim laddning och de negativa fallen (saknat, fel version, sammanblandning, mandat)."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ladda_steg  # noqa: E402

STEG = {
    'schema': 1, 'beskrivning': 'prov',
    'steg': {
        'provsteg': {'mandat': 'staende', 'syfte': 's', 'anvisning': 'a', 'underlag': [
            {'fil': 'kunskap/a.md', 'klass': 'profession', 'obligatorisk': True, 'delar': 'hela'},
            {'fil': 'kunskap/valfri.md', 'klass': 'profession', 'obligatorisk': False, 'delar': 'hela'},
            {'fil': 'BRIEF.md', 'klass': 'kund', 'obligatorisk': True, 'delar': '§1'},
            {'fil': 'EXTRA.md', 'klass': 'kund', 'obligatorisk': False, 'delar': 'hela'}]},
        'bestallt': {'mandat': 'bestallning', 'syfte': 's', 'anvisning': 'a', 'underlag': [
            {'fil': 'kunskap/a.md', 'klass': 'profession', 'obligatorisk': True, 'delar': 'hela'}]},
        'utan-kund': {'mandat': 'staende', 'syfte': 's', 'anvisning': 'a', 'underlag': [
            {'fil': 'kunskap/a.md', 'klass': 'profession', 'obligatorisk': True, 'delar': 'hela'},
            {'fil': 'BRIEF.md', 'klass': 'kund', 'obligatorisk': False, 'delar': '§1'}]}}}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def tree(root):
    return sorted(str(p.relative_to(root)) for p in Path(root).rglob('*'))


class Rig(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='nd-prov-'))
        self.rot = self.tmp / 'repo'
        (self.rot / 'kunskap').mkdir(parents=True)
        (self.rot / 'steg').mkdir()
        (self.rot / 'kunskap/a.md').write_text('# a\n')
        (self.rot / 'steg/steg.json').write_text(json.dumps(STEG))
        self.pin()
        self.kund = self.tmp / 'kund'
        self.kund.mkdir()
        (self.kund / 'BRIEF.md').write_text('# brief\n')
        self.ut = self.tmp / 'ut'

    def pin(self, extra=None):
        pins = {'kunskap/a.md': sha((self.rot / 'kunskap/a.md').read_bytes())}
        if (self.rot / 'kunskap/valfri.md').is_file():
            pins['kunskap/valfri.md'] = sha((self.rot / 'kunskap/valfri.md').read_bytes())
        pins.update(extra or {})
        (self.rot / 'steg/PINNAR.sha256').write_text(''.join('%s  %s\n' % (v, k) for k, v in sorted(pins.items())))

    def cli(self, *args):
        done = subprocess.run([sys.executable, '-B', str(HERE / 'ladda_steg.py'), '--rot', str(self.rot), *args],
                              capture_output=True, text=True, cwd=self.tmp)
        return done.returncode, json.loads(done.stdout.strip().splitlines()[-1])


class LegitimLaddning(Rig):
    def test_laddar_obligatoriskt_och_valfritt_och_skriver_kvitto(self):
        before = tree(self.rot)
        code, out = self.cli('--steg', 'provsteg', '--kund', str(self.kund), '--ut', str(self.ut), '--utforare', 'claude')
        self.assertEqual(code, 0, out)
        self.assertEqual(out['utfall'], 'laddad')
        self.assertEqual(out['laddade'], 2)
        self.assertEqual(sorted(out['valfria_saknade']), ['EXTRA.md', 'kunskap/valfri.md'])
        receipt = json.loads((self.ut / 'LADDNING.json').read_text())
        self.assertEqual(receipt['steg'], 'provsteg')
        self.assertEqual(receipt['utforare'], 'claude')
        self.assertEqual(receipt['kundmapp'], str(self.kund.resolve()))
        rows = {r['fil']: r for r in receipt['underlag']}
        self.assertEqual(rows['kunskap/a.md']['status'], 'laddad')
        self.assertEqual(rows['kunskap/a.md']['pinnad_sha256'], rows['kunskap/a.md']['sha256'])
        self.assertEqual(rows['BRIEF.md']['klass'], 'kund')
        self.assertIsNone(rows['BRIEF.md']['pinnad_sha256'])
        self.assertEqual(rows['kunskap/valfri.md']['status'], 'saknas (valfri)')
        self.assertEqual(rows['EXTRA.md']['status'], 'saknas (valfri)')
        self.assertTrue((self.ut / 'underlag/profession/kunskap/a.md').is_file())
        self.assertTrue((self.ut / 'underlag/kund/BRIEF.md').is_file())
        underlag = (self.ut / 'UNDERLAG.md').read_text()
        self.assertIn('`underlag/profession/kunskap/a.md` | profession | ja', underlag)
        self.assertIn('| `kunskap/valfri.md` | profession | nej', underlag)
        self.assertIn('stående (MANDAT.md §1)', underlag)
        noter = (self.ut / 'ANVANDNINGSNOTER.md').read_text()
        self.assertIn('underlag/kund/BRIEF.md', noter)
        self.assertNotIn('valfri.md', noter)
        self.assertEqual(tree(self.rot), before, 'ingenting skrivs i repot')
        self.assertEqual(oct(self.ut.stat().st_mode & 0o777), '0o700')

    def test_ett_bestallningssteg_laddas_med_beslutspost(self):
        code, out = self.cli('--steg', 'bestallt', '--ut', str(self.ut), '--bestallning', 'DIGITALA-1-AGARBESLUT-20260926')
        self.assertEqual(code, 0, out)
        receipt = json.loads((self.ut / 'LADDNING.json').read_text())
        self.assertEqual(receipt['bestallning'], 'DIGITALA-1-AGARBESLUT-20260926')
        self.assertIn('beställning DIGITALA-1-AGARBESLUT-20260926', (self.ut / 'UNDERLAG.md').read_text())

    def test_ett_steg_med_bara_valfri_kundfil_laddas_utan_kundmapp(self):
        code, out = self.cli('--steg', 'utan-kund', '--ut', str(self.ut))
        self.assertEqual(code, 0, out)
        self.assertEqual(out['valfria_saknade'], ['BRIEF.md'])


class Vagran(Rig):
    def vagras(self, *args, skal=''):
        before = tree(self.rot)
        code, out = self.cli(*args)
        self.assertEqual(code, 2, out)
        self.assertEqual(out['utfall'], 'vagrad')
        self.assertIn(skal, out['skal'])
        self.assertFalse(self.ut.exists(), 'ingen utkatalog vid vägran')
        self.assertEqual(tree(self.rot), before)
        return out

    def test_saknat_obligatoriskt_professionsunderlag(self):
        (self.rot / 'kunskap/a.md').unlink()
        self.vagras('--steg', 'provsteg', '--kund', str(self.kund), '--ut', str(self.ut), skal='saknat obligatoriskt underlag: profession/kunskap/a.md')

    def test_saknat_obligatoriskt_kundunderlag_och_saknad_kundmapp(self):
        (self.kund / 'BRIEF.md').unlink()
        self.vagras('--steg', 'provsteg', '--kund', str(self.kund), '--ut', str(self.ut), skal='kund/BRIEF.md')
        self.vagras('--steg', 'provsteg', '--ut', str(self.ut), skal='kund/BRIEF.md')

    def test_fel_version_vagras(self):
        (self.rot / 'kunskap/a.md').write_text('# a, ändrad\n')
        self.vagras('--steg', 'provsteg', '--kund', str(self.kund), '--ut', str(self.ut), skal='fel version')

    def test_opinnad_fil_vagras(self):
        (self.rot / 'kunskap/valfri.md').write_text('valfri\n')
        self.vagras('--steg', 'provsteg', '--kund', str(self.kund), '--ut', str(self.ut), skal='opinnad')

    def test_okant_steg(self):
        self.vagras('--steg', 'finns-inte', '--ut', str(self.ut), skal='okänt steg')

    def test_bestallningssteg_utan_beslutspost_och_med_ogiltigt_id(self):
        self.vagras('--steg', 'bestallt', '--ut', str(self.ut), skal='utanför det stående mandatet')
        self.vagras('--steg', 'bestallt', '--ut', str(self.ut), '--bestallning', 'liten-post', skal='beställnings-id')

    def test_kundmapp_i_repot_ar_sammanblandning(self):
        inne = self.rot / 'kunder-fel'
        inne.mkdir()
        (inne / 'BRIEF.md').write_text('x')
        self.vagras('--steg', 'provsteg', '--kund', str(inne), '--ut', str(self.ut), skal='sammanblandning')

    def test_kundfil_som_lamnar_kundmappen_ar_sammanblandning(self):
        utanfor = self.tmp / 'annan.md'
        utanfor.write_text('utanför\n')
        (self.kund / 'BRIEF.md').unlink()
        os.symlink(utanfor, self.kund / 'BRIEF.md')
        self.vagras('--steg', 'provsteg', '--kund', str(self.kund), '--ut', str(self.ut), skal='symbolisk länk')

    def test_professionsfil_som_lamnar_repot_vagras(self):
        utanfor = self.tmp / 'annan.md'
        utanfor.write_text('# a\n')
        (self.rot / 'kunskap/a.md').unlink()
        os.symlink(utanfor, self.rot / 'kunskap/a.md')
        self.vagras('--steg', 'provsteg', '--kund', str(self.kund), '--ut', str(self.ut), skal='symbolisk länk')

    def test_utkatalog_som_finns_eller_ligger_i_repot_vagras(self):
        self.ut.mkdir()
        code, out = self.cli('--steg', 'provsteg', '--kund', str(self.kund), '--ut', str(self.ut))
        self.assertEqual(code, 2)
        self.assertIn('finns redan', out['skal'])
        code, out = self.cli('--steg', 'provsteg', '--kund', str(self.kund), '--ut', str(self.rot / 'arbetsyta'))
        self.assertEqual(code, 2)
        self.assertIn('utanför repot', out['skal'])
        self.assertFalse((self.rot / 'arbetsyta').exists())

    def test_trasig_stegdefinition_vagras(self):
        (self.rot / 'steg/steg.json').write_text(json.dumps({'schema': 1, 'steg': {'x': {'mandat': 'fri', 'syfte': 's', 'anvisning': 'a', 'underlag': []}}}))
        self.vagras('--steg', 'x', '--ut', str(self.ut), skal='fel form')


if __name__ == '__main__':
    unittest.main()
