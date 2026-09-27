import io
import contextlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import intervju as iv  # noqa: E402
from test_verksamhetsuppgifter import exempel  # noqa: E402


def kor(*args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = iv.main(list(args))
    return code, json.loads(out.getvalue())


class Intervju(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.k = Path(self.tmp.name) / 'kund'; self.k.mkdir()
        (self.k / 'VERKSAMHET.json').write_text(json.dumps(exempel(fiktiv=True)))
        self.repo = HERE.parent

    def tearDown(self):
        self.tmp.cleanup()

    def test_kanda_svar_ateranvands_och_luckor_ger_fragor(self):
        code, r = kor('start', '--kund', str(self.k), '--kanal', 'e-post', '--testdialog')
        self.assertEqual(code, 0); self.assertEqual(r['omgangar'], 1); self.assertTrue(r['testdialog'])
        s = iv.las(str(self.k))
        fragor = [q['id'] for q in s['omgangar'][0]['fragor']]
        self.assertNotIn('A2', fragor, 'erbjudandet är känt ur VERKSAMHET.json och frågas inte om')
        self.assertIn('A1', fragor); self.assertIn('C1', fragor); self.assertLessEqual(len(fragor), iv.PER_OMGANG)
        md = (self.k / 'INTERVJU' / 'omgang-1.md').read_text()
        self.assertIn('TESTDIALOG', md); self.assertIn('### A1', md); self.assertIn('Varför vi frågar', md)
        self.assertFalse(any(p.is_relative_to(self.repo) for p in self.k.rglob('*')), 'inget skrivs i repot')
        self.assertFalse(list(self.repo.glob('INTERVJU*')))

    def test_bokningsbehov_ger_verksamhetsfragor_inte_kontaktformular(self):
        kor('start', '--kund', str(self.k), '--kanal', 'e-post', '--testdialog')
        svar = self.k / 'svar1.md'
        svar.write_text('### A1\nFler kunder ska kunna boka tid själva utan att ringa.\n\n### C1\nMejlen kommer till info@, Anna svarar samma dag.\n')
        code, r = kor('svar', '--kund', str(self.k), '--omgang', '1', '--fil', str(svar))
        self.assertEqual(code, 0); self.assertEqual(r['svar'], 2); self.assertGreaterEqual(r['foljdfragor_vantande'], 4)
        s = iv.las(str(self.k))
        self.assertEqual(s['svar'][0]['text'], 'Fler kunder ska kunna boka tid själva utan att ringa.')
        self.assertEqual([u['regel'] for u in s['foljdregler_utlosta']], ['bokning'])
        code, r = kor('nasta', '--kund', str(self.k))
        s = iv.las(str(self.k)); o2 = s['omgangar'][1]
        ids = [q['id'] for q in o2['fragor']]
        self.assertEqual(ids[:4], ['BOK1', 'BOK2', 'BOK3', 'BOK4'])
        self.assertTrue(o2['fragor'][0]['utlost_av'].startswith('A1: '))
        self.assertIn('bokningsintegrationens nivå', o2['fragor'][0]['paverkar'])
        self.assertFalse(any('kontaktformulär' in q['text'].lower() for q in o2['fragor']))

    def test_motsagelse_registreras_spårbart_och_ger_foljdfraga(self):
        kor('start', '--kund', str(self.k), '--kanal', 'e-post')
        f = self.k / 'F.json'; f.write_text(json.dumps([{'nyckel': 'oppettider', 'varde': 'mån–fre 08–17', 'status': 'kunden uppger', 'kalla': 'svar C1', 'omrade': 'C'}]))
        code, r = kor('fakta', '--kund', str(self.k), '--fil', str(f))
        self.assertEqual(code, 0); self.assertEqual(r['motsagelser_oavgjorda'], ['MOT1'])
        s = iv.las(str(self.k))
        self.assertEqual(s['motsagelser'][0]['uppgift_1']['kalla'], 'VERKSAMHET.json oppettider')
        self.assertTrue(any(q['id'] == 'MOT1' for q in s['vantande_foljdfragor']))
        md = iv.research_md(s)
        self.assertIn('motsägelse MOT1', md); self.assertIn('- MOT1 (oppettider)', md)
        code, r = kor('avgor', '--kund', str(self.k), '--motsagelse', 'MOT1', '--galler', 'mån–fre 08–17', '--skal', 'kunden bekräftade i omgång 2')
        self.assertEqual(r['motsagelser_oavgjorda'], [])
        s = iv.las(str(self.k))
        self.assertTrue([x for x in s['fakta'] if x['nyckel'] == 'oppettider' and x.get('ersatt')])
        bad = self.k / 'B.json'; bad.write_text(json.dumps([{'nyckel': 'x', 'varde': 'y', 'status': 'gissning', 'kalla': 'k', 'omrade': 'A'}]))
        self.assertEqual(kor('fakta', '--kund', str(self.k), '--fil', str(bad))[0], 2)

    def test_farsk_utforare_fortsatter_ur_tillstandet(self):
        kor('start', '--kund', str(self.k), '--kanal', 'e-post')
        code, r = kor('nasta', '--kund', str(self.k))
        self.assertIn('väntar på svar', r['meddelande'])
        svar = self.k / 's.md'; svar.write_text('### A1\nVi vill ha fler förfrågningar från villaägare.\n### A3\nVet inte riktigt vad som fungerar.\n')
        kor('svar', '--kund', str(self.k), '--omgang', '1', '--fil', str(svar))
        code, r = kor('status', '--kund', str(self.k))
        self.assertEqual(r['vantar_pa_svar'], []); self.assertEqual(r['svar'], 2)
        code, r = kor('nasta', '--kund', str(self.k))
        s = iv.las(str(self.k))
        self.assertEqual(s['omgangar'][1]['fragor'][0]['id'], 'OK1', 'osäkert svar ger frågan om vem som kan svara')
        ut = self.k / 'r.md'
        code, r = kor('research', '--kund', str(self.k), '--ut', str(ut))
        text = ut.read_text()
        self.assertIn('## 19. Intervju', text); self.assertIn('> **A1**', text); self.assertIn('Kan research.md besvara', text); self.assertIn('okänt', text)

    def test_hemligheter_i_svar_vagras(self):
        kor('start', '--kund', str(self.k), '--kanal', 'e-post')
        svar = self.k / 's.md'; svar.write_text('### A1\nLösenord: hemligt123 till hemsidan.\n')
        code, r = kor('svar', '--kund', str(self.k), '--omgang', '1', '--fil', str(svar))
        self.assertEqual(code, 2); self.assertIn('lösenord', r['vagrad'])
        self.assertEqual(iv.las(str(self.k))['svar'], [])

    def test_start_utan_verksamhet_och_omstart_bevarar(self):
        k2 = Path(self.tmp.name) / 'kund2'; k2.mkdir()
        code, r = kor('start', '--kund', str(k2), '--kanal', 'telefon')
        self.assertEqual(r['fakta'], 0); self.assertIn('A2', [q['id'] for q in iv.las(str(k2))['omgangar'][0]['fragor']])
        code, r = kor('start', '--kund', str(k2), '--kanal', 'telefon')
        self.assertIn('finns redan', r['meddelande']); self.assertEqual(r['omgangar'], 1)


if __name__ == '__main__':
    unittest.main()
