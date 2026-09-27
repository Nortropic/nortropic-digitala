import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import uppfoljning as up  # noqa: E402


def matplan(**o):
    mp = {'schema': 1, 'verktyg': 'vercel-analytics', 'samtycke_kravs': False,
          'handelser': [{'namn': 'quote_submit', 'utlosare': 'offertformulär skickat', 'var': '/kontakt', 'konvertering': True, 'parametrar': ['tjanst']},
                        {'namn': 'phone_click', 'utlosare': 'tel-länk klickad', 'var': 'alla sidor', 'konvertering': True}],
          'kedja': ['besök', 'kontaktsida', 'formulär skickat', 'mejl levererat', 'svar till kund'], 'affarsmatt': ['offertförfrågningar']}
    mp.update(o)
    return mp


class Prov(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_validering(self):
        up.validera(matplan())
        for bad, ord in ((matplan(verktyg='ga4'), 'samtycke'), (matplan(handelser=[{'namn': 'Bad Name', 'utlosare': 'x', 'var': 'y', 'konvertering': False}]), 'snake_case'),
                         (matplan(handelser=[{'namn': 'page_view', 'utlosare': 'x', 'var': 'y', 'konvertering': False}]), 'konvertering'), (matplan(affarsmatt=[]), 'affarsmatt')):
            with self.assertRaises(up.Vagrad) as cm:
                up.validera(bad)
            self.assertTrue(any(ord in x for x in cm.exception.args[0]), (ord, cm.exception.args[0]))

    def test_plan_och_kontroll_mot_bygge(self):
        md = up.handelseplan_md(matplan())
        self.assertIn('| `quote_submit` |', md); self.assertIn('Ingen spårning före samtycke', md)
        (self.d / 'a.js').write_text("track('quote_submit', {tjanst: t}); fbq('init', '1');")
        k = up.kontrollera(matplan(), str(self.d))
        self.assertEqual([h['finns_i_koden'] for h in k['handelser']], [True, False])
        self.assertEqual(k['sparare'], ['Meta-pixel'])
        self.assertTrue(any('utan spår av samtyckesmekanism' in f for f in k['fynd']))
        self.assertTrue(any('phone_click finns inte' in f for f in k['fynd']))
        (self.d / 'b.js').write_text("if (consent.granted) { track('phone_click') }")
        k = up.kontrollera(matplan(verktyg='ingen'), str(self.d))
        self.assertFalse(any('samtyckesmekanism' in f for f in k['fynd']))
        self.assertTrue(any('säger inget verktyg men bygget laddar' in f for f in k['fynd']))

    def test_utm_och_lasning(self):
        self.assertEqual(up.utm('https://provfirma.se/?a=1', 'Google', 'cpc', 'Vår Kampanj 2026'), 'https://provfirma.se/?a=1&utm_source=google&utm_medium=cpc&utm_campaign=v-r-kampanj-2026')
        with self.assertRaises(up.Vagrad):
            up.utm('http://provfirma.se/', 'g', 'cpc', 'k')
        exp = self.d / 'e.csv'; exp.write_text('event,count\nquote_submit,3\npage_view,500\nphone_click,4\n')
        l = up.las(str(exp), matplan())
        self.assertEqual(l['affarsnytta'], {'quote_submit': 3.0, 'phone_click': 4.0}); self.assertEqual(l['proxy'], {'page_view': 500.0})


if __name__ == '__main__':
    unittest.main()
