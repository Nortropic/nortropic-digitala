import io
import contextlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import annonsberedning as ab  # noqa: E402
from test_verksamhetsuppgifter import exempel  # noqa: E402


def kanalplan(**o):
    kp = {'mal': 'leads', 'malgrupp': 'villaägare i Provstad', 'budskap': 'trädgårdsanläggning i Provstad med fast pris',
          'konverteringar': [{'namn': 'quote_submit', 'handelse': 'offertformulär skickat', 'kategori': 'LEAD'}],
          'budget': {'valuta': 'SEK', 'dag_max': 150, 'villkor': 'ingen spendering utan beställning som namnger budget (MANDAT §2)'},
          'kampanjer': [{'kanal': 'google', 'namn': 'Anläggning Provstad', 'landningssida': 'https://provfirma.se/tjanster/anlaggning/',
                         'rubriker': ['Trädgårdsanläggning Provstad', 'Fast pris efter besök', 'Egen personal'], 'beskrivningar': ['Anläggning och skötsel i Provstad och Grannby. Kostnadsfri offert.', 'Ring eller skicka en förfrågan.'],
                         'sokord': [{'text': 'trädgårdsanläggning provstad', 'match': 'phrase'}], 'negativa': ['gratis']},
                        {'kanal': 'meta', 'namn': 'Vårkampanj', 'landningssida': 'https://provfirma.se/', 'primar_text': 'Dags för trädgården? Vi anlägger och sköter.', 'rubrik': 'Trädgård i Provstad', 'beskrivning': 'Fast pris', 'bilder': ['hero-01.avif']}]}
    kp.update(o)
    return kp


class Bygg(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.d = Path(self.tmp.name)
        self.v = exempel(fiktiv=True, webb={'doman': 'provfirma.se'})
        (self.d / 'tjanster' / 'anlaggning').mkdir(parents=True)
        (self.d / 'tjanster' / 'anlaggning' / 'index.html').write_text('<h1>Trädgårdsanläggning i Provstad</h1><p>Fast pris efter besök.</p>')
        (self.d / 'index.html').write_text('<h1>Välkommen</h1>')

    def tearDown(self):
        self.tmp.cleanup()

    def test_utkast_ar_pausade_med_utm_och_landningskontroll(self):
        ut = ab.bygg(kanalplan(), self.v, str(self.d))
        g = ut['google'][0]; m = ut['meta'][0]
        self.assertEqual(g['campaign']['status'], 'PAUSED'); self.assertEqual(g['ad_groups'][0]['status'], 'PAUSED'); self.assertEqual(g['ad_groups'][0]['ads'][0]['status'], 'PAUSED')
        self.assertEqual(m['campaign']['status'], 'PAUSED'); self.assertEqual(m['adset']['status'], 'PAUSED'); self.assertEqual(m['ad']['status'], 'PAUSED')
        self.assertIn('utm_source=google&utm_medium=cpc&utm_campaign=anl-ggning-provstad', g['ad_groups'][0]['ads'][0]['final_urls'][0])
        self.assertEqual(g['campaign']['campaign_budget']['amount_micros'], 150_000_000)
        self.assertEqual(g['ad_groups'][0]['keywords'][0]['keyword']['match_type'], 'PHRASE')
        self.assertEqual(m['campaign']['objective'], 'OUTCOME_LEADS'); self.assertEqual(m['adset']['daily_budget'], 15000)
        self.assertEqual(ut['landningssidor'][0]['finns_i_bygget'], True)
        self.assertEqual([f for f in ut['fynd'] if 'bär inte annonsens budskap' in f], ['Vårkampanj: landningssidan bär inte annonsens budskap (0/4 ord); annons och sida ska säga samma sak'])
        self.assertEqual(ut['landningssidor'][0]['budskap_overensstammelse'], '4/4 ord')
        self.assertFalse(ut['live'])

    def test_fynd_for_langd_saknad_sida_och_budskap(self):
        kp = kanalplan()
        kp['kampanjer'][0]['rubriker'] = ['x' * 31, 'kort']
        kp['kampanjer'][0]['landningssida'] = 'https://provfirma.se/saknas/'
        kp['kampanjer'][1]['landningssida'] = 'https://provfirma.se/'
        kp['kampanjer'][1]['budskap'] = 'solceller installation garanti batterier'
        ut = ab.bygg(kp, self.v, str(self.d))
        f = ' | '.join(ut['fynd'])
        self.assertIn('rubrik över 30', f); self.assertIn('minst 3 rubriker', f); self.assertIn('finns inte i bygget', f); self.assertIn('bär inte annonsens budskap', f)

    def test_ogiltig_plan_vagras(self):
        for bad, ord in ((kanalplan(mal='sälja'), 'mal'), (kanalplan(budget={'valuta': 'EUR', 'dag_max': 1, 'villkor': 'x'}), 'budget'), (kanalplan(budget={'valuta': 'SEK', 'dag_max': 10, 'villkor': ''}), 'villkor'), (kanalplan(konverteringar=[]), 'konverteringar')):
            with self.assertRaises(ab.Vagrad) as cm:
                ab.bygg(bad, self.v)
            self.assertTrue(any(ord in x for x in cm.exception.args[0]), (ord, cm.exception.args[0]))

    def test_cli_skriver_fyra_filer_och_rapport_laser_export(self):
        kpf = self.d / 'KP.json'; kpf.write_text(json.dumps(kanalplan())); vf = self.d / 'V.json'; vf.write_text(json.dumps(self.v))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ab.main(['bygg', '--kanalplan', str(kpf), '--verksamhet', str(vf), '--bygge', str(self.d), '--ut', str(self.d / 'ANNONSER')]), 0)
        for n in ('google-ads.json', 'meta-ads.json', 'BEREDNING.json', 'BEREDNING.md'):
            self.assertTrue((self.d / 'ANNONSER' / n).is_file(), n)
        self.assertIn('PAUSED', (self.d / 'ANNONSER' / 'BEREDNING.md').read_text())
        with contextlib.redirect_stdout(io.StringIO()) as o:
            self.assertEqual(ab.main(['overfor', '--verksamhet', str(vf), '--ut', str(self.d / 'K.json')]), 2)
        self.assertIn('fiktiv', json.loads(o.getvalue())['vagrad'][0])
        vf2 = self.d / 'V2.json'; vf2.write_text(json.dumps(exempel(fiktiv=False)))
        with contextlib.redirect_stdout(io.StringIO()) as o:
            self.assertEqual(ab.main(['overfor', '--verksamhet', str(vf2), '--ut', str(self.d / 'K.json')]), 2)
        self.assertIn('privat --konfiguration', json.loads(o.getvalue())['vagrad'][0])
        exp = self.d / 'export.csv'; exp.write_text('campaign,cost,clicks,impressions,conversions\nA,120.50,40,1000,2\nA,79.50,10,500,0\nB,10,1,50,0\n')
        r = ab.rapport(str(exp))
        self.assertEqual(r['kampanjer']['A']['kostnad_per_konvertering'], 100.0); self.assertIsNone(r['kampanjer']['B']['kostnad_per_konvertering'])


if __name__ == '__main__':
    unittest.main()
