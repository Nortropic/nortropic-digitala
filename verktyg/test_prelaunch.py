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

    def test_korning_fran_kor_profil_laser_runtimes_sammanfattning_och_inspektionen_ger_spill(self):
        """Fynd ur slutprovet HELHET-20260927: KORNING-kvittot bär inte mätvärdena; de ligger i körkatalogens SAMMANFATTNING.json."""
        run = self.d / 'run'; run.mkdir()
        (run / 'SAMMANFATTNING.json').write_text(json.dumps({'views': {'mobil-390': {'axe': {'violations': [], 'incomplete': ['color-contrast']}, 'h1': [{'lines': 3}]}, 'desktop-1440': {'axe': {'violations': []}}},
            'lighthouse': {'mobil': {'scores': {'performance': 100, 'accessibility': 100, 'best-practices': 100, 'seo': 58}, 'lcp_ms': 754, 'cls': 0}, 'desktop': {'scores': {'performance': 100, 'accessibility': 100, 'best-practices': 100, 'seo': 58}, 'lcp_ms': 202, 'cls': 0}}}))
        (run / 'KVITTO.json').write_text(json.dumps({'outcome': 'klar', 'viewports': {'mobil-390': {'width': 390}, 'desktop-1440': {'width': 1440}}}))
        k = self.d / 'KORNING.json'; k.write_text(json.dumps({'schema': 1, 'profil': 'matning', 'resultat': {'run': str(run), 'outcome': 'klar'}}))
        insp = self.d / 'INSPEKTION.json'; insp.write_text(json.dumps({'vyer': {'390': {'spill': {'spill': False, 'scrollWidth': 390, 'clientWidth': 390}}, '1440': {'spill': {'spill': False, 'scrollWidth': 1440, 'clientWidth': 1440}}}}))
        r = self.kor(matning=k, inspektion=insp)
        st = {g['grind'][:1]: g for g in r['grindar']}
        self.assertEqual((st['2']['status'], st['3']['status'], st['4']['status']), ('PASS', 'PASS', 'PASS'), st)
        self.assertIn('SEO-poängen avgör inte i förhandsvisning', st['2']['belagg']); self.assertIn('mobil seo', st['2']['belagg']); self.assertIn('layoutvyns bredd', st['3']['belagg'])
        # samma mätning i lanseringsläge: Lighthouse-SEO 58 faller grinden
        ut = self.d / 'P2.json'
        with contextlib.redirect_stdout(io.StringIO()):
            pl.main(['--bygge', str(self.b), '--lage', 'lansering', '--verksamhet', str(self.v), '--matning', str(k), '--inspektion', str(insp), '--ut', str(ut)])
        r2 = json.loads(ut.read_text()); g2 = next(g for g in r2['grindar'] if g['grind'].startswith('2'))
        self.assertEqual(g2['status'], 'FAIL'); self.assertIn('seo', g2['atgard'])
        # spill i en vy faller responsiviteten; utan inspektion är den EJ_MATT med anvisning
        insp.write_text(json.dumps({'vyer': {'390': {'spill': {'spill': True, 'scrollWidth': 412, 'clientWidth': 390}}}}))
        r3 = self.kor(matning=k, inspektion=insp); self.assertEqual(next(g for g in r3['grindar'] if g['grind'].startswith('3'))['status'], 'FAIL')
        r4 = self.kor(matning=k); g3 = next(g for g in r4['grindar'] if g['grind'].startswith('3')); self.assertEqual(g3['status'], 'EJ_MATT'); self.assertIn('--inspektion', g3['belagg'])
        # ofullständig mätning (outcome ≠ klar) ger EJ_MATT på grind 2–4; axe som antal tolereras
        k.write_text(json.dumps({'schema': 1, 'profil': 'matning', 'resultat': {'run': str(run), 'outcome': 'tidsgrans'}}))
        r5 = self.kor(matning=k); st5 = {g['grind'][:1]: g['status'] for g in r5['grindar']}; self.assertEqual((st5['2'], st5['3'], st5['4']), ('EJ_MATT', 'EJ_MATT', 'EJ_MATT'))
        k.write_text(json.dumps({'schema': 1, 'profil': 'matning', 'resultat': {'run': str(run), 'outcome': 'klar'}}))
        (run / 'SAMMANFATTNING.json').write_text(json.dumps({'views': {'mobil-390': {'axe': {'violations': 2, 'incomplete': 1}}}, 'lighthouse': {'mobil': {'scores': {'performance': 100}}}}))
        r6 = self.kor(matning=k); self.assertEqual(next(g for g in r6['grindar'] if g['grind'].startswith('4'))['status'], 'FAIL')


if __name__ == '__main__':
    unittest.main()
