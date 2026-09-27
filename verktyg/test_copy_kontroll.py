import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import copy_kontroll as ck  # noqa: E402


class Rapport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.d = Path(self.tmp.name)
        (self.d / 'index.html').write_text('<html><head><title>' + 'Lång titel ' * 8 + '</title><meta name="description" content="' + 'x' * 160 + '"></head>'
                                           '<body><script>var a="Vi förstår att";</script><h1>Välkommen till Firma AB</h1><p>Vi erbjuder skräddarsydda lösningar — snabbt — säkert!</p>'
                                           '<p>Ring 070-123 45 67!</p><p>Seamless service.</p></body></html>', encoding='utf-8')
        (self.d / 'om.md').write_text('# Om oss\n\nVi är ett företag som arbetar i Provstad sedan länge och trivs med det.\nVi har många kunder som återkommer år efter år till oss.\nVi brinner för trädgårdar och allt som växer i dem, lorem ipsum.\n', encoding='utf-8')
        (self.d / 'node_modules').mkdir(); (self.d / 'node_modules' / 'x.js').write_text('"Vi förstår att detta ignoreras"')

    def tearDown(self):
        self.tmp.cleanup()

    def test_fynd_per_typ_utan_poang(self):
        r = ck.rapport([str(self.d)])
        typer = r['sammanfattning']
        self.assertEqual(r['filer'], 2)
        for t in ('fras', 'engelskt läckage', 'platshållare', 'hälsningsrubrik', 'tankstreckskedja', 'utropstecken', 'spegelöppningar', 'metalängd'):
            self.assertIn(t, typer, t)
        self.assertIsNone(r['poang'])
        self.assertEqual([x for x in r['fynd'] if x['text'] == 'vi förstår att'], [], 'script-innehåll räknas inte som synlig text')
        self.assertEqual(sum(1 for x in r['fynd'] if x['typ'] == 'metalängd'), 2)

    def test_krav_och_brieffraser(self):
        krav = self.d / 'KRAV.json'
        krav.write_text(json.dumps({'krav': [{'namn': 'telefon', 'var': 'varje sida', 'regex': r'070-123 45 67', 'skal': 't'}, {'namn': 'orgnr', 'var': 'nagon sida', 'regex': r'556677-8899', 'skal': 'o'}]}))
        fraser = self.d / 'FRASER.txt'; fraser.write_text('# branschfraser\ntrivs med det\n')
        r = ck.rapport([str(self.d)], str(fraser), str(krav))
        saknade = [(x['fil'].split('/')[-1], x['text']) for x in r['fynd'] if x['typ'] == 'saknat element']
        self.assertIn(('om.md', 'telefon'), saknade)
        self.assertIn(('(alla)', 'orgnr'), saknade)
        self.assertNotIn(('index.html', 'telefon'), saknade)
        self.assertTrue(any(x['text'] == 'trivs med det' for x in r['fynd']))

    def test_cli_skriver_rapport_och_strikt_ger_1(self):
        ut = self.d / 'R.json'; md = self.d / 'R.md'
        import io, contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ck.main(['--kalla', str(self.d), '--ut', str(ut), '--md', str(md), '--strikt']), 1)
        self.assertTrue(ut.is_file() and md.is_file())
        self.assertIn('| Fil |', md.read_text())
        ren = self.d / 'ren'; ren.mkdir(); (ren / 'a.md').write_text('# Trädgård i Provstad\n\nAnläggning och skötsel. Ring 070-123 45 67.\n')
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ck.main(['--kalla', str(ren), '--ut', str(ut), '--strikt']), 0)


if __name__ == '__main__':
    unittest.main()
