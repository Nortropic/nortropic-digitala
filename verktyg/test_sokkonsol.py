import io
import contextlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sokkonsol as sk  # noqa: E402
from test_verksamhetsuppgifter import exempel  # noqa: E402


class Fejk:
    """Inspelad transport: inga nätanrop i prov."""
    def __init__(self, svar):
        self.svar = svar; self.logg = []

    def __call__(self, metod, url, body=None, headers=None, timeout=30):
        self.logg.append((metod, url, body, headers))
        for nyckel, (status, s) in self.svar.items():
            if nyckel in url:
                return status, s
        return 404, {'error': 'okänd'}


class Plan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.d = Path(self.tmp.name)
        self.v = self.d / 'V.json'; self.v.write_text(json.dumps(exempel(fiktiv=False, webb={'doman': 'provfirma.se'})))
        self.atk = self.d / 'atk.json'; self.atk.write_text(json.dumps({'typ': 'oauth', 'client_id': 'id-1234567', 'client_secret': 'hemlig-secret-1234', 'refresh_token': 'refresh-token-9999'})); self.atk.chmod(0o600)

    def tearDown(self):
        self.tmp.cleanup()

    def test_planen_namnger_alla_anrop_utan_nat(self):
        ut = self.d / 'K.json'
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(sk.main(['plan', '--verksamhet', str(self.v), '--urler', '/,/tjanster/', '--ut', str(ut)]), 0)
        k = json.loads(ut.read_text())
        self.assertEqual([p['steg'] for p in k['plan']], ['token', 'verifiera', 'agare', 'egenskap', 'sitemap', 'inspektera', 'sokdata'])
        self.assertEqual(k['anrop'], []); self.assertFalse(k['live'])
        self.assertEqual(len(k['plan'][5]['nyttolast']), 2)
        self.assertIn('inte en verifierad integration', k['not'])

    def test_live_vagras_utan_atkomst_for_fiktiv_och_for_forhandsvisningsdoman(self):
        ut = self.d / 'K.json'
        with contextlib.redirect_stdout(io.StringIO()) as o:
            self.assertEqual(sk.main(['token', '--verksamhet', str(self.v), '--ut', str(ut)]), 2)
        self.assertIn('kräver --live', json.loads(o.getvalue())['vagrad'])
        with contextlib.redirect_stdout(io.StringIO()) as o:
            self.assertEqual(sk.main(['token', '--verksamhet', str(self.v), '--ut', str(ut), '--live']), 2)
        self.assertIn('--atkomst saknas', json.loads(o.getvalue())['vagrad'])
        fik = self.d / 'F.json'; fik.write_text(json.dumps(exempel(fiktiv=True, webb={'doman': 'provfirma.se'})))
        with self.assertRaises(sk.vu.Vagrad):
            sk.kontroll_fore_live(json.loads(fik.read_text()), 'provfirma.se', 'token', Fejk({}))
        with self.assertRaises(sk.Vagrad):
            sk.kontroll_fore_live(json.loads(self.v.read_text()), 'x' + sk.FORHANDSVISNINGSSUFFIX, 'token', Fejk({}))
        with self.assertRaises(sk.Vagrad):
            sk.kontroll_fore_live(json.loads(self.v.read_text()), 'provfirma.se', 'verifiera', Fejk({'provfirma.se': (401, {})}))
        self.atk.chmod(0o644)
        with self.assertRaises(sk.Vagrad):
            sk.las_atkomst(str(self.atk))

    def test_verifiera_kedjan_mot_inspelad_transport_och_kvitto_utan_hemligheter(self):
        f = Fejk({'oauth2.googleapis.com/token': (200, {'access_token': 'ya29.abc'}),
                  '/webResource?verificationMethod=META': (200, {'id': 'https%3A%2F%2Fprovfirma.se%2F', 'site': {'type': 'SITE', 'identifier': 'https://provfirma.se/'}, 'owners': ['konto@example.com']}),
                  '/webResource/': (200, {'owners': ['konto@example.com', 'kund@example.com']}),
                  '/sitemaps/': (204, {}), '/sites/': (204, {})})
        atk = json.loads(self.atk.read_text())
        rader = sk.kor('verifiera', json.loads(self.v.read_text()), 'provfirma.se', ['/'], atk, f, agare=['kund@example.com'])
        self.assertEqual([r['steg'] for r in rader], ['verifiera', 'agare', 'egenskap', 'sitemap'])
        self.assertEqual(f.logg[0][0], 'POST')
        self.assertIn('refresh_token=refresh-token-9999', f.logg[0][2].decode())
        self.assertEqual(f.logg[1][3]['Authorization'], 'Bearer ya29.abc')
        text = json.dumps(rader)
        self.assertNotIn('hemlig-secret-1234', text); self.assertNotIn('refresh-token-9999', text)
        insp = Fejk({'oauth2.googleapis.com/token': (200, {'access_token': 't'}), 'index:inspect': (200, {'inspectionResult': {'indexStatusResult': {'verdict': 'NEUTRAL', 'coverageState': 'Discovered - currently not indexed'}}})})
        rader = sk.kor('inspektera', json.loads(self.v.read_text()), 'provfirma.se', ['/', '/tjanster/'], atk, insp)
        self.assertEqual(len(rader), 2)
        t = sk.tolkning(rader)
        self.assertEqual(t[0]['verdict'], 'NEUTRAL'); self.assertIn('begär indexering', t[0]['atgard'])

    def journal_args(self, ut, command='verifiera'):
        return [command, '--verksamhet', str(self.v), '--ut', str(ut), '--live', '--atkomst', str(self.atk)]

    def transport(self, fail=None, stop=False):
        calls = []
        def api(method, url, body=None, headers=None, timeout=30):
            calls.append((method, url, body))
            saved = json.loads(self.journal_path.read_text())
            self.assertEqual(saved['transport'][-1]['status'], None, 'avsikten finns på disk före varje anrop')
            self.assertEqual(saved['transport'][-1]['url'], url)
            if fail and fail in url:
                if stop:
                    raise KeyboardInterrupt('syntetiskt hårt avbrott')
                raise sk.urllib.error.URLError('hemlig-secret-1234 får inte skrivas ut')
            if url == sk.TOKEN_URL:
                return 200, {'access_token': 'bearer-test-secret'}
            if 'webResource?' in url:
                return 200, {'id': 'resource-1', 'site': {'type': 'SITE', 'identifier': 'https://provfirma.se/'}, 'owners': ['konto@example.com']}
            return (200 if method == 'GET' else 204), {}
        return api, calls

    def test_journal_bindning_och_positiv_kedja(self):
        self.journal_path = self.d/'positive.json'
        v = json.loads(self.v.read_text()); v['sokkonsol_agare'] = ['kund@example.com']; self.v.write_text(json.dumps(v))
        api, calls = self.transport()
        with contextlib.redirect_stdout(io.StringIO()):
            code = sk.main(self.journal_args(self.journal_path), transport=api)
        q = json.loads(self.journal_path.read_text())
        self.assertEqual(code, 0)
        self.assertEqual(q['lage'], 'API-anrop besvarade')
        self.assertEqual(q['provniva'], 'testtransport')
        self.assertEqual([r['steg'] for r in q['anrop']], ['verifiera', 'agare', 'egenskap', 'sitemap'])
        self.assertEqual(len(q['transport']), 6)
        self.assertEqual(q['bindning']['verksamhet_sha256'], sk.sha(self.v.read_bytes()))
        self.assertEqual(q['bindning']['atkomst_sha256'], sk.sha(self.atk.read_bytes()))
        self.assertEqual(q['bindning']['kod']['sokkonsol.py'], sk.sha(Path(sk.__file__).read_bytes()))
        self.assertEqual(q['bindning']['plan_sha256'], sk.sha(sk.json_bytes(q['plan'])))
        owner = next(r for r in q['transport'] if '/webResource/resource-1' in r['url'])
        body = next(r[2] for r in calls if '/webResource/resource-1' in r[1])
        self.assertEqual(owner['kropp_sha256'], sk.sha(body))
        self.assertEqual(owner['begaran_sha256'], sk.sha(sk.json_bytes({k: owner[k] for k in ('metod','url','kropp_sha256')})))
        text = self.journal_path.read_text()
        for secret in ('hemlig-secret-1234', 'refresh-token-9999', 'bearer-test-secret'):
            self.assertNotIn(secret, text)
        self.assertEqual(self.journal_path.stat().st_mode & 0o777, 0o600)

    def test_tappat_svar_efter_verifiering_bevaras_och_upprepning_vagras(self):
        self.journal_path = self.d/'unknown.json'
        api, calls = self.transport(fail='/sites/')
        with contextlib.redirect_stdout(io.StringIO()):
            code = sk.main(self.journal_args(self.journal_path), transport=api)
        q = json.loads(self.journal_path.read_text())
        self.assertEqual(code, 2)
        self.assertEqual([(r['steg'], r['status']) for r in q['anrop']], [('verifiera',200), ('egenskap',0)])
        self.assertIn('okänt', q['lage'])
        self.assertIn('okänt', q['transport'][-1]['utfall'])
        self.assertEqual(sum('webResource?' in r[1] for r in calls), 1)
        before = self.journal_path.read_bytes(); n = len(calls)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(sk.main(self.journal_args(self.journal_path), transport=api), 2)
        self.assertIn('finns redan', out.getvalue())
        self.assertEqual(len(calls), n)
        self.assertEqual(self.journal_path.read_bytes(), before)
        self.assertNotIn('hemlig-secret-1234', before.decode())

    def test_preflight_och_verifiering_timeout_samt_hart_avbrott(self):
        for fail, stop in [('https://provfirma.se/',False), ('webResource?',False), ('webResource?',True)]:
            with self.subTest(fail=fail, stop=stop):
                self.journal_path = self.d/('kvitto-%s.json' % len(list(self.d.glob('kvitto-*'))))
                api, calls = self.transport(fail=fail, stop=stop)
                with contextlib.redirect_stdout(io.StringIO()):
                    if stop:
                        with self.assertRaises(KeyboardInterrupt):
                            sk.main(self.journal_args(self.journal_path), transport=api)
                    else:
                        self.assertEqual(sk.main(self.journal_args(self.journal_path), transport=api), 2)
                q = json.loads(self.journal_path.read_text())
                self.assertNotEqual(q['lage'], 'API-anrop besvarade')
                self.assertIn('okänt', q['transport'][-1]['utfall'])
                n = len(calls)
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(sk.main(self.journal_args(self.journal_path), transport=api), 2)
                self.assertEqual(len(calls), n)
                self.assertFalse(any('/sitemaps/' in x[1] for x in calls))

    def test_http_timeout_returns_observed_unknown_without_exception_text(self):
        from unittest.mock import patch
        for error in (TimeoutError('secret detail'), sk.urllib.error.URLError('secret detail')):
            with patch.object(sk.urllib.request, 'urlopen', side_effect=error):
                status, reply = sk.http_oppna('POST', sk.SV + '/webResource', b'{}')
            self.assertEqual(status, 0)
            self.assertEqual(reply['utfall'], 'okänt')
            self.assertNotIn('secret detail', json.dumps(reply))

    def test_tjanstekonto_signerar_med_openssl(self):
        import subprocess
        key = subprocess.run(['openssl', 'genrsa', '2048'], capture_output=True, check=True).stdout.decode()
        f = Fejk({'oauth2.googleapis.com/token': (200, {'access_token': 'sa-token'})})
        tok = sk.access_token({'typ': 'tjanstekonto', 'client_email': 'sa@example.iam', 'private_key': key}, f)
        self.assertEqual(tok, 'sa-token')
        body = f.logg[0][2].decode()
        self.assertIn('grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer', body)
        self.assertEqual(body.count('.'), 2)


if __name__ == '__main__':
    unittest.main()
