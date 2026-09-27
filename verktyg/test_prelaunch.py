import io
import contextlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import prelaunch as pl  # noqa: E402
from test_verksamhetsuppgifter import exempel  # noqa: E402
from test_seo_kontroll import skriv  # noqa: E402


class Grindar(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.d = Path(self.tmp.name); self.b = self.d / 'bygge'; self.b.mkdir()
        skriv(self.b, '/', robots='<meta name="robots" content="noindex">')
        (self.b / 'sitemap.xml').write_text('<urlset><url><loc>https://provfirma.se/</loc></url></urlset>'); (self.b / 'robots.txt').write_text('User-agent: *\nDisallow: /\nSitemap: https://provfirma.se/sitemap.xml\n')
        self.v = self.d / 'V.json'; self.v.write_text(json.dumps(exempel(fiktiv=False, webb={'doman': 'provfirma.se'})))

    def tearDown(self):
        self.tmp.cleanup()

    def kor(self, **extra):
        ut = self.d / 'P.json'
        args = ['--bygge', str(self.b), '--lage', 'forhandsvisning', '--verksamhet', str(self.v), '--ut', str(ut), '--md', str(self.d / 'P.md')]
        for k, v in extra.items():
            args += ['--' + k, str(v)]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(pl.main(args), 0)
        return json.loads(ut.read_text())

    def test_utan_matning_ar_det_mesta_ej_matt_och_inte_redo(self):
        r = self.kor()
        st = {g['grind'][:1]: g['status'] for g in r['grindar']}
        self.assertEqual(st, {'0': 'PASS', '1': 'EJ_MATT', '2': 'EJ_MATT', '3': 'EJ_MATT', '4': 'EJ_MATT', '5': 'FAIL', '6': 'MANNISKA', '7': 'EJ_MATT'})
        self.assertFalse(r['redo_for_lansering'])
        self.assertIn('EJ_MATT är inte PASS', r['not'])

    def test_hemlighet_och_platshallare_faller_grind_0(self):
        (self.b / 'app.js').write_text('const k = "re_ABCDEFGHIJKLMNOPQRSTUVWXYZ12"; // lorem ipsum')
        r = self.kor()
        g0 = r['grindar'][0]
        self.assertEqual(g0['status'], 'FAIL'); self.assertIn('hemligheter i bygget: 1', g0['belagg'])

    def test_matning_handlingar_juridik_och_huvuden(self):
        m = self.d / 'K.json'; m.write_text(json.dumps({'utfall': 'klar', 'resultat': {'lighthouse': {'performance': 0.93, 'accessibility': 0.97, 'best_practices': 1, 'seo': 0.96}, 'lcp_ms': 1800, 'cls': 0.02, 'axe': {'violations': []}, 'vyer': {'390': {}, '1440': {}}, 'horisontell_spill': False}}))
        kv = self.d / 'prov.json'; kv.write_text(json.dumps({'utfall': 'klar'}))
        h = self.d / 'H.json'; h.write_text(json.dumps({'handlingar': [{'namn': 'offert', 'typ': 'formulär', 'prov': 'provare', 'kvitto': str(kv)}, {'namn': 'ring', 'typ': 'tel', 'prov': 'manuell', 'utfall': 'godkänd 2026-09-27'}]}))
        j = self.d / 'J.json'; j.write_text(json.dumps({'flaggor': [{'flagga': 'hälsa/kropp/medicin', 'status': 'rapporterad', 'citat': 'x'}]}))
        hv = self.d / 'huvud.txt'; hv.write_text('HTTP/2 200\ncontent-security-policy: default-src \'self\'; frame-ancestors \'none\'\nstrict-transport-security: max-age=63072000\nx-content-type-options: nosniff\nreferrer-policy: strict-origin-when-cross-origin\n')
        au = self.d / 'audit.json'; au.write_text(json.dumps({'metadata': {'vulnerabilities': {'high': 0, 'critical': 0}}}))
        (self.b / 'index.html').write_text((self.b / 'index.html').read_text().replace('<img src="/b.jpg">', '').replace('<a href="/tjanster/">Tjänster</a><a href="/tjanster/">x</a>', ''))
        r = self.kor(matning=m, handlingar=h, juridik=j, huvuden=hv, audit=au)
        st = {g['grind'][:1]: g['status'] for g in r['grindar']}
        self.assertEqual(st, {'0': 'PASS', '1': 'PASS', '2': 'PASS', '3': 'PASS', '4': 'PASS', '5': 'PASS', '6': 'MANNISKA', '7': 'PASS'})
        self.assertFalse(r['redo_for_lansering'], 'ohanterad juridikflagga hindrar redo')
        j.write_text(json.dumps({'flaggor': [{'flagga': 'hälsa/kropp/medicin', 'status': 'hanterad'}]}))
        r = self.kor(matning=m, handlingar=h, juridik=j, huvuden=hv, audit=au)
        self.assertTrue(r['redo_for_lansering'])
        r = self.kor(matning=m, handlingar=h, huvuden=hv, audit=au)
        self.assertFalse(r['redo_for_lansering'], 'utan JURIDIK.json är sajten inte redo, även om alla tekniska grindar är PASS')
        self.assertFalse(r['juridik_lamnad'])
        m.write_text(json.dumps({'resultat': {'lighthouse': {'performance': 0.7}, 'axe': {'violations': [{'id': 'x'}]}, 'vyer': ['390']}}))
        hv.write_text('HTTP/2 200\ncontent-type: text/html\n')
        r = self.kor(matning=m, handlingar=h, juridik=j, huvuden=hv)
        st = {g['grind'][:1]: g['status'] for g in r['grindar']}
        self.assertEqual((st['2'], st['3'], st['4'], st['7']), ('FAIL', 'EJ_MATT', 'FAIL', 'FAIL'))
        self.assertIn('Content-Security-Policy', r['grindar'][7]['atgard'])


if __name__ == '__main__':
    unittest.main()
