import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import verksamhetsuppgifter as vu  # noqa: E402


def exempel(**o):
    v = {'schema': 1, 'namn': 'Testfirma Nord', 'fiktiv': True, 'orgnr': '556677-8899',
         'kontaktvagar': [{'typ': 'telefon', 'varde': '070-123 45 67', 'belagg': 'kundens svar 2026-09-27'}, {'typ': 'formular', 'varde': '/kontakt', 'belagg': 'brief §4'}],
         'adress': {'gata': 'Provgatan 1', 'postnummer': '123 45', 'ort': 'Provstad', 'publik': True, 'roll': 'verksamhetsstalle'},
         'rackvidd': {'typ': 'lokal', 'orter': ['Provstad', 'Grannby']}, 'oppettider': [{'dag': 'man', 'oppnar': '07:00', 'stanger': '16:00'}],
         'kategorier': ['Trädgårdsanläggare'], 'tjanster': ['Anläggning', 'Skötsel'], 'sprak': 'sv'}
    v.update(o)
    return v


class Validering(unittest.TestCase):
    def test_giltig_fil_ger_nap_och_e164(self):
        v = exempel(); self.assertEqual(vu.validera(v), [])
        n = vu.nap(v)
        self.assertEqual((n['telefon_e164'], n['adress'], n['adress_visas'], n['omrade']), ('+46701234567', 'Provgatan 1, 123 45 Provstad', True, ['Provstad', 'Grannby']))

    def test_dold_adress_visas_inte(self):
        v = exempel(adress={'gata': 'Hemgatan 2', 'postnummer': '123 45', 'ort': 'Provstad', 'publik': False, 'roll': 'hemvist'})
        self.assertIsNone(vu.nap(v)['adress'])
        self.assertEqual(vu.nap(v)['ort'], 'Provstad')

    def test_fel_vagras_med_namngivna_fel(self):
        for bad, ord in ((exempel(fiktiv='ja'), 'fiktiv'), (exempel(orgnr='5566778899'), 'orgnr'), (exempel(kontaktvagar=None), 'kontaktvagar'),
                         (exempel(adress=dict(exempel()['adress'], postnummer='12345')), 'postnummer'), (exempel(rackvidd={'typ': 'lokal', 'orter': []}), 'orter'),
                         (exempel(tjanster=[]), 'tjanster'), (exempel(oppettider=[{'dag': 'måndag', 'oppnar': '7', 'stanger': '16:00'}]), 'oppettider'),
                         (exempel(extra=1), 'okända'), (exempel(sokkonsol_agare=['ingen-adress']), 'sokkonsol_agare'), (exempel(omdomen_kalla={'plattform': 'Google'}), 'omdomen_kalla'),
                         (exempel(omdomen_kalla={'plattform': 'Google', 'datum': '2026-09-27', 'antal': '12'}), 'antal'), (exempel(kontaktvagar=[{'typ': 'telefon', 'varde': '12', 'belagg': 'x'}]), 'telefonnumret')):
            with self.assertRaises(vu.Vagrad) as cm:
                vu.validera(bad)
            self.assertTrue(any(ord in f for f in cm.exception.args[0]), (ord, cm.exception.args[0]))

    def test_valfria_falt_for_sokkonsol_och_omdomen_godtas(self):
        v = exempel(sokkonsol_agare=['kund@example.com'], omdomen_kalla={'plattform': 'Google', 'datum': '2026-09-27', 'betyg': 4.8, 'antal': 12})
        self.assertEqual(vu.validera(v), [])

    def test_fiktiv_verksamhet_sparras_fran_verkliga_atgarder(self):
        with self.assertRaises(vu.Vagrad):
            vu.kraver_verklig(exempel(), 'skapa företagsprofil')
        vu.kraver_verklig(exempel(fiktiv=False), 'skapa företagsprofil')

    def test_krav_harleds_ur_uppgifterna(self):
        k = vu.krav(exempel())
        namn = [r['namn'] for r in k['krav']]
        self.assertEqual(namn, ['telefon', 'organisationsnummer', 'serviceomrade', 'adress'])
        import re
        self.assertTrue(re.search(k['krav'][0]['regex'], 'Ring 070-123 45 67'))
        self.assertTrue(re.search(k['krav'][0]['regex'], 'tel:+46701234567'))
        self.assertTrue(re.search(k['krav'][2]['regex'], 'Vi arbetar i Grannby'))
        self.assertEqual(vu.krav(exempel(orgnr=None, adress=None, rackvidd={'typ': 'nationell', 'orter': []}))['krav'][0]['namn'], 'telefon')
        self.assertEqual(len(vu.krav(exempel(orgnr=None, adress=None, rackvidd={'typ': 'nationell', 'orter': []}))['krav']), 1)

    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'VERKSAMHET.json'; f.write_text(json.dumps(exempel()))
            import io, contextlib
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(vu.main(['krav', str(f), '--ut', str(Path(d) / 'KRAV.json')]), 0)
            self.assertTrue((Path(d) / 'KRAV.json').is_file())
            f.write_text('{"schema": 1}')
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(vu.main(['kontrollera', str(f)]), 2)
            self.assertFalse(json.loads(out.getvalue())['giltig'])


if __name__ == '__main__':
    unittest.main()
