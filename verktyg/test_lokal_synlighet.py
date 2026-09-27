import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lokal_synlighet as ls  # noqa: E402
from test_verksamhetsuppgifter import exempel  # noqa: E402


class Prov(unittest.TestCase):
    def test_tillamplighet(self):
        self.assertEqual(ls.tillamplighet(exempel())[0], 'förbjuden')
        self.assertEqual(ls.tillamplighet(exempel(fiktiv=False))[0], 'tillämplig')
        self.assertEqual(ls.tillamplighet(exempel(fiktiv=False, rackvidd={'typ': 'nationell', 'orter': []}, adress=None))[0], 'inte tillämplig')

    def test_datablad_och_dold_adress(self):
        md = ls.datablad(exempel(fiktiv=False))
        self.assertIn('Tillämplighet:** tillämplig', md); self.assertIn('Provgatan 1, 123 45 Provstad', md); self.assertIn('Måndag: 07:00–16:00', md); self.assertIn('hitta.se', md)
        dold = ls.datablad(exempel(fiktiv=False, adress={'gata': 'Hemgatan 2', 'postnummer': '123 45', 'ort': 'Provstad', 'publik': False, 'roll': 'hemvist'}))
        self.assertIn('DOLD', dold); self.assertNotIn('Hemgatan', dold)
        self.assertIn('Inget datablad', ls.datablad(exempel()))

    def test_kontroll_mot_bygge(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'index.html'
            p.write_text('<html><body><p>Ring 070-123 45 67</p><script type="application/ld+json">{"@type":"LocalBusiness","name":"Fel Namn","telephone":"+46701234567"}</script></body></html>')
            k = ls.kontrollera(exempel(fiktiv=False), d)
            self.assertEqual(k['scheman'], 1)
            self.assertEqual([f['typ'] for f in k['fynd']], ['schema name ≠ verksamhetens namn', 'schema saknar address fast adressen är publik'])
            p.write_text('<html><body><script type="application/ld+json">{"@type":"LocalBusiness","name":"Testfirma Nord","telephone":"+46701234567","address":{"postalCode":"123 45"}}</script></body></html>')
            k = ls.kontrollera(exempel(fiktiv=False), d)
            self.assertEqual([f['typ'] for f in k['fynd']], ['telefonnumret saknas som synlig text'])


if __name__ == '__main__':
    unittest.main()
