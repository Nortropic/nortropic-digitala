import http.server
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lansering as la  # noqa: E402
import drift_kontroll as dk  # noqa: E402
from test_verksamhetsuppgifter import exempel  # noqa: E402

SIDOR = {'/': ('<html><head><meta name="robots" content="noindex"><meta name="google-site-verification" content="tok-1"></head><body>Testfirma Nord</body></html>', {}),
         '/sitemap.xml': ('<urlset><url><loc>https://x/</loc></url></urlset>', {}), '/robots.txt': ('User-agent: *\nDisallow: /\n', {})}


class Handler(http.server.BaseHTTPRequestHandler):
    def _svara(self, body=True):
        if self.path in SIDOR:
            text, hdr = SIDOR[self.path]
            self.send_response(200); [self.send_header(k, v) for k, v in hdr.items()]; self.send_header('Content-Type', 'text/html'); self.end_headers()
            if body:
                self.wfile.write(text.encode())
        else:
            self.send_response(404); self.end_headers()

    def do_GET(self):
        self._svara()

    def do_HEAD(self):
        self._svara(False)

    def log_message(self, *a):
        pass


class Server(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = http.server.HTTPServer(('127.0.0.1', 0), Handler); cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_lanseringsplan_kraver_mandat_i_texten(self):
        md = la.plan_md(exempel(fiktiv=False, webb={'doman': 'provfirma.se'}), None)
        self.assertIn('INGET ANGIVET', md); self.assertIn('noindex', md); self.assertIn('Återgång', md)
        self.assertIn('**Mandat:** DIGITALA-2-X', la.plan_md(exempel(fiktiv=False), 'DIGITALA-2-X'))

    def test_kontrollen_hittar_noindex_robots_och_token(self):
        bas = 'http://127.0.0.1:%d' % self.port
        with self.assertRaises(ValueError):
            la.kontrollera(bas + '/')
        k = la.kontrollera(bas + '/', token='tok-1', tillat_http=True)
        self.assertEqual(k['startsida']['status'], 200); self.assertTrue(k['startsida']['noindex']); self.assertTrue(k['startsida']['verifieringstagg'])
        self.assertIn('noindex kvar på startsidan (meta eller X-Robots-Tag)', k['fynd']); self.assertIn('robots.txt blockerar allt', k['fynd'])
        self.assertFalse(k['klar_for_sokkonsol'])
        k2 = la.kontrollera(bas + '/', token='annan', tillat_http=True)
        self.assertTrue(any('verifieringstaggen' in f for f in k2['fynd']))
        SIDOR['/'] = ('<html><head></head><body>Testfirma Nord</body></html>', {}); SIDOR['/robots.txt'] = ('User-agent: *\nAllow: /\nSitemap: x\n', {})
        try:
            k3 = la.kontrollera(bas + '/', tillat_http=True)
            self.assertEqual(k3['fynd'], []); self.assertTrue(k3['klar_for_sokkonsol'])
        finally:
            SIDOR['/'] = ('<html><head><meta name="robots" content="noindex"><meta name="google-site-verification" content="tok-1"></head><body>Testfirma Nord</body></html>', {}); SIDOR['/robots.txt'] = ('User-agent: *\nDisallow: /\n', {})

    def test_driftkontroll_kvitto_och_incident(self):
        bas = 'http://127.0.0.1:%d' % self.port
        plan = {'schema': 1, 'kund': 'test', 'sajter': [{'adress': bas + '/', 'forvantat': 'Testfirma Nord', 'max_ms': 5000, 'sitemap': True}, {'adress': bas + '/saknas', 'forvantat': 'x'}]}
        k = dk.kontrollera(plan, tillat_http=True)
        self.assertEqual([r['incident'] for r in k['sajter']], [False, True]); self.assertEqual(k['incidenter'], 1)
        self.assertEqual(k['sajter'][1]['fynd'], ['svarar 404'])
        k = dk.kontrollera({'schema': 1, 'sajter': [{'adress': 'https://provfirma.se/', 'cert_dagar_min': 14}]}, hamta=lambda u, timeout=20: {'status': 200, 'ms': 10, 'body': ''}, cert_dagar=lambda h: 5)
        self.assertEqual(k['sajter'][0]['fynd'], ['certifikatet går ut om 5 dagar'])
        with tempfile.TemporaryDirectory() as d:
            pf = Path(d) / 'DRIFT.json'; pf.write_text(json.dumps(plan))
            import io, contextlib
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(dk.main(['--plan', str(pf), '--ut', str(Path(d) / 'ut'), '--tillat-http']), 1)
            self.assertEqual(len(list((Path(d) / 'ut').glob('DRIFT-*.json'))), 1)


if __name__ == '__main__':
    unittest.main()
