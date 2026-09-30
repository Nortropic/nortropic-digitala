import http.server
import json
import sys
import tempfile
import threading
import time
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
            {'namn': 'betalning', 'adress': 'https://pay.test/', 'forvantad_slutadress': 'https://pay.test/', 'forvantat': 'Betala'},
            {'namn': 'bokning', 'adress': 'https://book.test/', 'forvantad_slutadress': 'https://book.test/'}]}]}
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
            read1 = read
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


class Lankkontroll(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.counts = {}
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                cls.counts[self.path] = cls.counts.get(self.path, 0) + 1
                if self.path == '/huvud':
                    try:
                        self.wfile.write(b'HTTP/1.1 200 OK\r\nX-Slow: '); self.wfile.flush()
                        for _ in range(10):
                            self.wfile.write(b'x'); self.wfile.flush(); time.sleep(1)
                    except (BrokenPipeError, ConnectionResetError): pass
                    return
                status = 200; headers = {}; body = '<title>Klar</title>Boka'
                if self.path in ('/flytt', '/till-start', '/gammal', '/gammal308', '/a', '/ut'):
                    status = 308 if self.path == '/gammal308' else 301 if self.path == '/gammal' else 302
                    headers['Location'] = {'/flytt': '/ok', '/till-start': '/', '/gammal': '/ok', '/gammal308': '/ok', '/a': '/503-all',
                                           '/ut': 'http://localhost:%d/ok' % self.server.server_port}[self.path]
                elif self.path == '/soft':
                    body = '<title>404 – Sidan <b>hittades inte</b></title>'
                elif self.path == '/sen-soft':
                    body = '<title>' + 'Normal text ' * 10 + 'page does not exist</title>'
                elif self.path == '/503':
                    status = 503 if cls.counts[self.path] <= 2 else 200
                elif self.path in ('/503-all', '/429'):
                    status = 503 if self.path == '/503-all' else 429; headers['Retry-After'] = '999'
                elif self.path == '/404':
                    status = 404
                elif self.path.startswith('/hop/'):
                    status = 301; headers['Location'] = '/hop/%d' % (int(self.path.rsplit('/', 1)[1]) + 1)
                elif self.path == '/sitemap.xml':
                    base = 'http://127.0.0.1:%d' % self.server.server_port
                    body = '<urlset><url><loc>' + base + '/a</loc></url><url><loc>' + base + '/ok</loc></url></urlset>'
                elif self.path == '/robots.txt':
                    body = 'User-agent: *\nAllow: /'
                self.send_response(status)
                for k, v in headers.items(): self.send_header(k, v)
                if self.path != '/dropp': self.send_header('Content-Length', str(len(body.encode())))
                self.end_headers()
                try:
                    if self.path == '/dropp':
                        for _ in range(10):
                            self.wfile.write(b'x'); self.wfile.flush(); time.sleep(1)
                    else:
                        self.wfile.write(body.encode())
                except (BrokenPipeError, ConnectionResetError):
                    pass
            def log_message(self, *args): pass
        cls.srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.base = 'http://127.0.0.1:%d' % cls.srv.server_port
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown(); cls.srv.server_close()

    def setUp(self): self.counts.clear()

    def handling(self, path, expected):
        h = {'namn': 'bokning', 'adress': self.base + path, 'forvantat': 'Boka'}
        if expected is not None: h['forvantad_slutadress'] = self.base + expected
        return dk.kontrollera({'sajter': [{'adress': self.base + '/', 'handlingar': [h]}]}, tillat_http=True)['sajter'][0]['handlingar'][0]

    def test_slutadress_baslinje_och_normalisering(self):
        row = self.handling('/flytt', '/flytt')
        self.assertEqual(row['lage'], 'incident'); self.assertEqual(row['slutadress'], self.base + '/ok')
        self.assertEqual(row['forvantad_slutadress'], self.base + '/flytt')
        self.assertIn('landar på annan adress: ' + self.base + '/ok', row['fynd'])
        self.assertEqual(self.handling('/flytt', '/ok/?')['lage'], 'ok')
        row = self.handling('/ok', None); self.assertEqual(row['lage'], 'okant'); self.assertIn('baslinjen saknas', row['skal'])
        self.assertEqual(dk.normalisera_adress('https://EXAMPLE.com:443/a/?'), dk.normalisera_adress('https://example.com/a'))

    def test_felsida_title_och_startsida_ar_incidenter_utan_omforsok(self):
        for path in ('/soft', '/sen-soft'):
            row = self.handling(path, path)
            self.assertEqual(row['lage'], 'incident'); self.assertIn('felsida med status 200', row['fynd'])
            self.assertLessEqual(len(row['titel']), 80); self.assertNotIn('<', row['titel'])
            self.assertEqual(self.counts[path], 1)
        row = self.handling('/till-start', '/')
        self.assertIn('handlingslänken omdirigerar till startsidan', row['fynd'])
        self.assertEqual(self.handling('/ok', '/ok')['fynd'], [])

    def test_omforsok_bara_tillfalliga_fel_och_forsta_felet_bevaras(self):
        pauses = []
        r = dk.hamta(self.base + '/503', omforsok=2, paus=pauses.append)
        self.assertEqual((r['status'], r['forsok'], self.counts['/503']), (200, 3, 3))
        self.assertEqual(r['forsta_felet'], 'första försöket: svarar 503'); self.assertEqual(pauses, [1, 1])
        r = dk.hamta(self.base + '/404', omforsok=2, paus=pauses.append)
        self.assertEqual((r['status'], r['forsok'], self.counts['/404']), (404, 1, 1))
        r = dk.hamta(self.base + '/503-all', omforsok=2, paus=lambda _: None)
        self.assertEqual((r['status'], r['forsok']), (503, 3))
        self.assertEqual(dk.kontrollera({'sajter': [{'adress': self.base + '/503-all'}]}, hamta=lambda _: r, tillat_http=True)['incidenter'], 1)
        self.counts.clear()
        row = self.handling('/a', '/a')
        self.assertEqual(row['lage'], 'incident'); self.assertEqual(row['forsok'], 1)
        self.assertEqual(self.counts['/a'], 1); self.assertEqual(self.counts['/503-all'], 1)
        pauses.clear(); r = dk.hamta(self.base + '/429', timeout=90, omforsok=2, paus=pauses.append)
        self.assertEqual(pauses, [30, 30]); self.assertEqual(r['forsok'], 3)

    def test_total_tidsgrans_vid_droppande_kropp_och_externt_okant_bevaras(self):
        start = time.monotonic(); r = dk.hamta(self.base + '/dropp', timeout=3, omforsok=2)
        self.assertLess(time.monotonic() - start, 5); self.assertEqual(r['fel'], 'TimeoutError'); self.assertEqual(r['forsok'], 1)
        k = dk.kontrollera({'sajter': [{'adress': self.base + '/dropp'}]}, hamta=lambda _: r, tillat_http=True)
        self.assertEqual(k['incidenter'], 1); self.assertIn('tidsgräns', k['sajter'][0]['fynd'])
        row = dk.handlingskontroll({'namn': 'extern', 'adress': self.base + '/dropp', 'forvantad_slutadress': self.base + '/dropp'},
                                  'https://egen.test/', lambda _: r, True)
        self.assertEqual(row['lage'], 'okant')
        start = time.monotonic(); r = dk.hamta(self.base + '/huvud', timeout=0.1)
        self.assertLess(time.monotonic() - start, 1); self.assertEqual(r['fel'], 'TimeoutError')
        row = dk.handlingskontroll({'namn': 'extern', 'adress': self.base+'/huvud',
            'forvantad_slutadress': self.base+'/annan'}, 'https://egen.test/', lambda _: r, True)
        self.assertEqual(row['lage'], 'okant'); self.assertIsNone(row['slutadress']); self.assertEqual(row['fynd'], [])
        # Allow the local server to deliver headers/body under full-suite load;
        # the deadline must interrupt Retry-After, not race the initial response.
        start = time.monotonic(); r = dk.hamta(self.base + '/503-all', timeout=1, omforsok=2)
        self.assertLess(time.monotonic() - start, 2); self.assertEqual(r['status'], 503)
        self.assertEqual(r['fel'], 'TimeoutError'); self.assertEqual(r['forsok'], 1)
        self.assertEqual(r['forsta_felet'], 'första försöket: svarar 503')

    def test_certifikatets_dns_och_tls_har_total_tidsgrans(self):
        from unittest.mock import patch
        release = threading.Event(); finished = threading.Event()
        original = dk.socket.getaddrinfo
        def slow_dns(*args, **kwargs):
            release.wait(2)
            try: return original(*args, **kwargs)
            finally: finished.set()
        start = time.monotonic()
        try:
            with patch.object(dk.socket, 'getaddrinfo', side_effect=slow_dns):
                with self.assertRaises(TimeoutError): dk.cert_dagar('localhost', self.srv.server_port, timeout=0.1)
            self.assertLess(time.monotonic()-start, 1)
        finally:
            release.set(); finished.wait(1)
        time.sleep(0.05)
        self.assertEqual(self.counts, {})
        # A TCP listener that never answers TLS must also be bounded.
        import socketserver
        class Silent(socketserver.BaseRequestHandler):
            def handle(self): release.wait(2)
        release.clear()
        tls = socketserver.ThreadingTCPServer(('127.0.0.1', 0), Silent); tls.daemon_threads = True
        threading.Thread(target=tls.serve_forever, daemon=True).start()
        try:
            start = time.monotonic()
            with self.assertRaises(TimeoutError): dk.cert_dagar('localhost', tls.server_address[1], timeout=0.1)
            self.assertLess(time.monotonic()-start, 1)
        finally:
            release.set(); tls.shutdown(); tls.server_close()

    def test_dns_och_tls_forsoks_inte_igen_och_dns_kan_inte_halla_kontrollen(self):
        from unittest.mock import patch, Mock
        from types import SimpleNamespace
        for error in (dk.socket.gaierror('synthetic DNS'), dk.ssl.SSLError('synthetic TLS')):
            opening = Mock(side_effect=dk.urllib.error.URLError(error))
            with patch.object(dk.urllib.request, 'build_opener', return_value=SimpleNamespace(open=opening)):
                result = dk.hamta(self.base + '/ok', omforsok=2, paus=lambda _: None)
            self.assertEqual(opening.call_count, 1); self.assertEqual(result['forsok'], 1)
        release = threading.Event(); finished = threading.Event(); original = dk.socket.getaddrinfo
        def slow_dns(*args, **kw):
            release.wait(2)
            try: return original(*args, **kw)
            finally: finished.set()
        start = time.monotonic()
        try:
            with patch.object(dk.socket, 'getaddrinfo', side_effect=slow_dns):
                result = dk.hamta(self.base + '/ok', timeout=0.1)
            self.assertLess(time.monotonic() - start, 1); self.assertEqual(result['fel'], 'TimeoutError')
        finally:
            release.set(); finished.wait(1)
        time.sleep(0.05)
        self.assertEqual(self.counts, {})  # cancelled DNS may finish, but must not send a late GET

    def test_sitemap_budget_omfattar_alla_hopp_och_omforsok_utan_annat_ursprung(self):
        k = dk.kontrollera_sitemap(self.base + '/', 2, dk.hamta)
        self.assertEqual(k['anrop'], 3); self.assertEqual(sum(self.counts.values()), 3)
        self.assertEqual((k['ofullstandiga'], k['over_taket']), (1, 1)); self.assertEqual(k['fynd'], [])
        self.counts.clear()
        r = dk.hamta(self.base + '/ut', max_hopp=5, eget_ursprung=dk.ursprung(self.base))
        self.assertEqual(r['fel'], 'ValueError'); self.assertEqual(self.counts, {'/ut': 1})

    def test_avbruten_redirect_ar_aldrig_observerat_slutsvar(self):
        from unittest.mock import patch, Mock
        from types import SimpleNamespace
        from io import BytesIO
        class Redirect(BytesIO):
            status = 301
            headers = {'Location': '/ny'}
            def geturl(self): return self.base + '/gammal'
        response = Redirect(b''); response.base = self.base
        with patch.object(dk.urllib.request, 'build_opener',
                          return_value=SimpleNamespace(open=Mock(
                              side_effect=[response, TimeoutError()]))):
            row, = la.prova_omdirigeringar(self.base+'/', {'gamla': [{'fran': '/gammal', 'till': '/ny'}]}, True)
        self.assertEqual(row['status'], 301)
        self.assertIsNone(row['slutstatus']); self.assertIsNone(row['slutadress'])
        self.assertEqual(row['hopp'], [{'status': 301, 'fran': self.base+'/gammal', 'till': self.base+'/ny'}])
        self.assertEqual(row['fynd'], ['målet svarar inte 200: TimeoutError'])
        for path, options in [('/hop/0', {}), ('/ut', {'eget_ursprung': dk.ursprung(self.base)})]:
            result = dk.hamta(self.base+path, max_hopp=5, **options)
            self.assertFalse(result['slutadress_observerad']); self.assertIsNone(result['status'])
            self.assertIsNone(dk._meta(result, self.base+path)['slutadress'])
            self.assertFalse(any('annan adress' in f for f in dk._fynd(result, self.base+path, self.base+'/ok')))

    def test_lansering_provar_301_302_404_och_hopptak(self):
        data = {'gamla': [{'fran': p, 'till': '/ok', 'status': 301} for p in ('/gammal', '/till-start', '/404', '/hop/0')]}
        extra = la.prova_omdirigeringar(self.base+'/', {'gamla': [{'fran': '/gammal308', 'till': '/ok'}]}, True)
        self.assertTrue(extra[0]['ok']); self.assertEqual(extra[0]['status'], 308)
        rows = la.prova_omdirigeringar(self.base + '/', data, True)
        self.assertEqual([r['ok'] for r in rows], [True, False, False, False])
        self.assertEqual((rows[0]['status'], rows[0]['slutstatus'], rows[0]['slutadress']), (301, 200, self.base + '/ok'))
        self.assertEqual(len(rows[3]['hopp']), 5); self.assertNotIn('/hop/6', self.counts)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root/'REDIRECTS.json').write_text(json.dumps(data))
            self.assertEqual(la.main(['kontrollera', '--adress', self.base + '/', '--tillat-http', '--omdirigeringar', str(root/'REDIRECTS.json'), '--ut', str(root/'KONTROLL.json')]), 0)
            result = json.loads((root/'KONTROLL.json').read_text())
            self.assertEqual(len(result['omdirigeringar']), 4); self.assertFalse(result['klar_for_sokkonsol'])


class EpostDNS(unittest.TestCase):
    def resolver(self, spf=True, dkim=True, dmarc=True, error=False):
        values = {'firma.test': ['"v=spf1 include:mail.test -all"'] if spf else [],
                  's1._domainkey.firma.test': ['"v=DKIM1; p=" "SyntetiskNyckel"'] if dkim else [],
                  '_dmarc.firma.test': ['"v=DMARC1; p=none"'] if dmarc else []}
        def read(name, typ):
            if error: raise TimeoutError()
            return la.dns_las(name, typ, hamta_json=lambda n,t: {'Status':0,'Question':[{'name':n+'.','type':16}],
                'Answer':[{'name':n+'.','type':16,'TTL':300,'data':x} for x in values[n]]})
        return read

    def test_epostens_fyra_bestallningsfall(self):
        for options,findings,notes,unknown in [({},[],[],[]),
                ({'spf':False,'dkim':False},['varken SPF eller DKIM hittades'],[],[]),
                ({'dkim':False,'dmarc':False},[],['DMARC saknas'],[]),
                ({'error':True},[],[],['SPF: kunde inte kontrolleras','DKIM: kunde inte kontrolleras','DMARC: kunde inte kontrolleras'])]:
            with self.subTest(options=options):
                r=la.epostkontroll({'fiktiv':False},'firma.test','s1',self.resolver(**options))
                self.assertEqual((r['fynd'],r['anmarkningar'],r['okanda']),(findings,notes,unknown))
                self.assertEqual(r['klar'],not findings and not unknown)

    def test_dns_svar_valideras_och_ttl_bevaras(self):
        r=self.resolver()('firma.test','TXT'); self.assertEqual(r['poster'][0]['ttl'],300)
        for raw in ({'Status':2}, {'Status':0,'TC':True}, {'Status':0},
                    {'Status':0,'Question':[{'name':'annan.test','type':16}]},
                    {'Status':0,'Question':[{'name':'firma.test','type':16}],'Answer':[{'type':16,'TTL':-1,'data':'x','name':'firma.test'}]},
                    {'Status':0,'Question':[{'name':'firma.test','type':16}],'Answer':[{'type':16,'TTL':300,'data':'x','name':'annan.test'}]}):
            r=la.dns_las('firma.test','TXT',lambda n,t:raw)
            self.assertEqual((r['lage'],r['skal']),('okant','kunde inte kontrolleras'))
        r=la.dns_las('firma.test','TXT',lambda n,t:{'Status':3,'Question':[{'name':n,'type':16}]})
        self.assertEqual((r['lage'],r['poster']),('ok',[]))
        r=la.dns_las('firma.test','TXT',lambda n,t:{'Status':0,'Question':[{'name':n,'type':16}],
            'Answer':[{'name':n,'type':5,'TTL':300,'data':'mail.test.'},{'name':'mail.test.','type':16,'TTL':300,'data':'"v=spf1 -all"'}]})
        self.assertEqual((r['lage'],r['poster'][0]['namn']),('ok','mail.test'))
        with self.assertRaises(ValueError): la.dns_las('https://firma.test/path','TXT')

    def test_fiktiv_verksamhet_och_cli_gor_inga_dnsanrop(self):
        from unittest.mock import Mock, patch
        resolver=Mock(side_effect=AssertionError('network forbidden'))
        r=la.epostkontroll({'fiktiv':True},'verklig.se','selector',resolver)
        resolver.assert_not_called();self.assertFalse(r['klar']);self.assertEqual(r['lage'],'okant')
        with tempfile.TemporaryDirectory() as td, patch.object(la.vu,'las',return_value={'fiktiv':True}), patch.object(dk,'hamta',side_effect=AssertionError('network forbidden')):
            output=Path(td)/'EPOST.json'
            code=la.main(['epostkontroll','--verksamhet','syntetisk.json','--avsandardoman','verklig.se','--dkim-selektor','s1','--mandat','syntetiskt','--ut',str(output)])
            self.assertEqual(code,2);self.assertFalse(json.loads(output.read_text())['klar'])
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            original=output.read_bytes()
            with self.assertRaises(FileExistsError): la.privat_json(output, {'overskrivning':True})
            self.assertEqual(output.read_bytes(),original)

    def test_planen_lagger_epost_och_arkiv_fore_migrering(self):
        text=la.plan_md({'namn':'Syntetisk','fiktiv':True},'prov')
        self.assertLess(text.index('epostkontroll'),text.index('Domänen kopplad'))
        self.assertLess(text.index('arkivera.mjs'),text.index('Omdirigeringar från gammal sajt'))
        self.assertIn('migrering_adresser',text)


if __name__ == '__main__':
    unittest.main()
