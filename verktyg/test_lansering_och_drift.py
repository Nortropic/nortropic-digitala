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
    def test_sitemap_sidor_ursprung_tak_och_dtd(self):
        calls = []; status = [404]
        def fetch(url):
            calls.append(url)
            body = '<urlset>' + ''.join('<url><loc>' + u + '</loc></url>' for u in
                ('https://x/c', 'https://x/b', 'https://x/a', 'https://other/a')) + '</urlset>'
            return {'status': status[0] if url == 'https://x/b' else 200, 'ms': 1, 'body': body if url.endswith('.xml') else 'OK'}
        plan = {'sajter': [{'adress': 'https://x/', 'sitemap': True}]}
        r = dk.kontrollera(plan, hamta=fetch)
        self.assertEqual(r['incidenter'], 1); self.assertIn('https://x/b: svarar 404', r['sajter'][0]['fynd'])
        self.assertEqual(calls, ['https://x/', 'https://x/sitemap.xml', 'https://x/a', 'https://x/b', 'https://x/c'])
        sm = r['sajter'][0]['sitemap']; self.assertEqual((sm['provade'], sm['annat_ursprung'], sm['over_taket']), (3, 1, 0))
        status[0] = 200; self.assertEqual(dk.kontrollera(plan, hamta=fetch)['incidenter'], 0)
        plan['sajter'][0]['sitemap_tak'] = 2
        r = dk.kontrollera(plan, hamta=fetch)['sajter'][0]
        self.assertEqual((r['sitemap']['provade'], r['sitemap']['over_taket'], r['lage']), (2, 1, 'okant'))
        for body, fragment in (('<!DOCTYPE urlset><urlset/>', 'DTD'), ('x' * (dk.MAX_BODY + 1), 'storleksgränsen')):
            sm = dk.kontrollera_sitemap('https://x/', 50, lambda u: {'status': 200, 'body': body})
            self.assertIn(fragment, str(sm['fynd'])); self.assertEqual(sm['provade'], 0)

    def test_sitemapindex_ett_led_och_begransat_anropstal(self):
        calls = []
        bodies = {'https://x/sitemap.xml': '<sitemapindex><sitemap><loc>https://x/child.xml</loc></sitemap></sitemapindex>',
                  'https://x/child.xml': '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://x/a</loc></url></urlset>'}
        def fetch(url):
            calls.append(url); return {'status': 200, 'ms': 1, 'body': bodies.get(url, 'OK')}
        r = dk.kontrollera_sitemap('https://x/', 50, fetch)
        self.assertEqual(r['fynd'], []); self.assertEqual(r['provade'], 1); self.assertEqual(r['indexfiler_provade'], 1)
        self.assertEqual(calls, ['https://x/sitemap.xml', 'https://x/child.xml', 'https://x/a'])
        bodies['https://x/child.xml'] = bodies['https://x/sitemap.xml']
        self.assertIn('djupare', str(dk.kontrollera_sitemap('https://x/', 50, fetch)['fynd']))
        bodies['https://x/sitemap.xml'] = '<sitemapindex>' + ''.join('<sitemap><loc>https://x/%d.xml</loc></sitemap>' % i for i in range(5)) + '</sitemapindex>'
        calls.clear(); r = dk.kontrollera_sitemap('https://x/', 2, fetch)
        self.assertEqual(len(calls), 3); self.assertEqual(r['indexfiler_oprovade'], 3)

    def test_handlingar_skiljer_incident_och_okant(self):
        plan = {'sajter': [{'adress': 'https://x/', 'handlingar': [
            {'namn': 'betalning', 'adress': 'https://pay.test/', 'forvantat': 'Betala'},
            {'namn': 'bokning', 'adress': 'https://book.test/'}]}]}
        responses = {'https://x/': {'status': 200, 'body': 'OK', 'ms': 1},
                     'https://pay.test/': {'status': 200, 'body': 'Fel', 'ms': 1},
                     'https://book.test/': {'status': 404, 'body': '', 'ms': 1}}
        fetch = lambda u: responses[u]
        r = dk.kontrollera(plan, hamta=fetch)
        self.assertEqual(r['sajter'][0]['fynd'], ['betalning: förväntad text saknas', 'bokning: svarar 404'])
        responses['https://pay.test/']['body'] = 'Betala'
        for status, body, fel in ((403, 'Verify you are human', None), (429, '', None), (None, '', 'TimeoutError')):
            responses['https://book.test/'] = {'status': status, 'body': body, 'fel': fel, 'ms': 1}
            r = dk.kontrollera(plan, hamta=fetch)
            self.assertEqual((r['incidenter'], r['okanda'], r['sajter'][0]['lage']), (0, 1, 'okant'))
        responses['https://book.test/'] = {'status': 200, 'body': 'Boka', 'ms': 1}
        self.assertEqual(dk.kontrollera(plan, hamta=fetch)['okanda'], 0)
        responses['https://x/'] = {'status': 403, 'body': 'Verify you are human', 'ms': 1}
        self.assertEqual(dk.kontrollera(plan, hamta=fetch)['incidenter'], 1)

    def test_drift_hamta_ar_get_och_okant_exit_noll(self):
        from unittest.mock import patch
        from io import BytesIO, StringIO
        import contextlib
        class Response(BytesIO):
            status = 200
        from types import SimpleNamespace
        from unittest.mock import Mock
        request = Mock(return_value=Response(b'OK'))
        with patch.object(dk.urllib.request, 'build_opener', return_value=SimpleNamespace(open=request)):
            self.assertEqual(dk.hamta('https://x/')['status'], 200)
            self.assertEqual(request.call_args.args[0].get_method(), 'GET')
        # Ett HTTP-felsvar vars kropp dröjer ska fortfarande bli ett kvitto.
        class SlowErrorBody(BytesIO):
            def read(self, *args):
                raise TimeoutError()
        for code in (200, 403, 429):
            error = dk.urllib.error.HTTPError('https://third.test/', code, 'syntetiskt', {}, SlowErrorBody())
            with patch.object(dk.urllib.request, 'build_opener', return_value=SimpleNamespace(open=Mock(side_effect=error))):
                response = dk.hamta('https://third.test/')
            self.assertEqual(response['status'], code); self.assertEqual(response['fel'], 'TimeoutError')
            external = dk.handlingskontroll({'namn': 'bokning', 'adress': 'https://third.test/'}, 'https://own.test/', lambda u: response)
            own = dk.handlingskontroll({'namn': 'bokning', 'adress': 'https://own.test/'}, 'https://own.test/', lambda u: response)
            self.assertEqual(external['lage'], 'okant'); self.assertEqual(own['lage'], 'incident')
            self.assertEqual(dk.kontrollera({'sajter': [{'adress': 'https://own.test/'}]}, hamta=lambda u: response)['incidenter'], 1)
        # Riktig transport: ingen redirect följs, inte ens till annat ursprung.
        got = []
        class Redirect(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                got.append(self.path)
                self.send_response(302)
                self.send_header('Location', 'http://localhost:%d/next' % self.server.server_port)
                self.send_header('Content-Length', '0'); self.end_headers()
            def log_message(self, *args):
                pass
        srv = http.server.HTTPServer(('127.0.0.1', 0), Redirect)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            response = dk.hamta('http://127.0.0.1:%d/start' % srv.server_port)
            self.assertEqual(response['status'], 302); self.assertEqual(got, ['/start'])
        finally:
            srv.shutdown(); srv.server_close()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp); (p / 'plan.json').write_text(json.dumps({'schema': 1, 'sajter': [{'adress': 'https://x/'}]}))
            result = {'tid': '2026-09-30T12:00:00Z', 'incidenter': 0, 'okanda': 1, 'sajter': []}
            with patch.object(dk, 'kontrollera', return_value=result), contextlib.redirect_stdout(StringIO()):
                self.assertEqual(dk.main(['--plan', str(p / 'plan.json'), '--ut', str(p / 'ut')]), 0)

    @classmethod
    def setUpClass(cls):
        cls.srv = http.server.HTTPServer(('127.0.0.1', 0), Handler); cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

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
