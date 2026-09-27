# -*- coding: utf-8 -*-
"""Webbläsarvägen (HELHET etapp 4): inspektera, utforska och besok mot en lokal provsajt; värdverkställd ursprungsgräns,
redigerade hemligheter, formulär som inte skickas utan tillåtelse, fynd som regressionsprov, avskärmning av besökarprovet."""
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROT = HERE.parent
WB = HERE / 'webblasare'
NODE = 'node'

SIDOR = {
    '/': '<!doctype html><html lang="sv"><head><meta name="viewport" content="width=device-width"><title>Provfirma</title><style>a.osynlig:focus{outline:none}</style></head>'
         '<body><header><button id="meny" aria-expanded="false" aria-controls="nav" onclick="this.setAttribute(\'aria-expanded\', this.getAttribute(\'aria-expanded\')===\'true\'?\'false\':\'true\')">Meny</button>'
         '<nav id="nav"><a href="/kontakt/">Kontakt</a> <a href="/trasig/">Trasig</a> <a class="osynlig" href="/om/">Om</a></nav></header>'
         '<main><h1>Trädgård i Provstad</h1><p>Anläggning och skötsel.</p><img src="http://localhost:1/extern.png" alt="extern"></main></body></html>',
    '/om/': '<!doctype html><html lang="sv"><head><title>Om</title></head><body><h1>Om</h1><h1>Två</h1><a href="/">Hem</a></body></html>',
    '/kontakt/': '<!doctype html><html lang="sv"><head><title>Kontakt</title></head><body><h1>Kontakt</h1>'
                 '<form method="post" action="/skicka"><label>Namn <input name="namn" required></label><label>E-post <input type="email" name="epost" required></label>'
                 '<label>Meddelande <textarea name="msg" required></textarea></label><button type="submit">Skicka</button></form><a href="/">Hem</a></body></html>',
}


class Handler(http.server.BaseHTTPRequestHandler):
    poster = []
    huvuden = []

    def do_GET(self):
        Handler.huvuden.append(dict(self.headers))
        if self.path == '/tredje/':
            body = ('<!doctype html><html lang="sv"><head><title>Tredje</title></head><body><h1>Tredje part</h1><img src="http://localhost:%d/kontakt/" alt="tredje"><a href="/">Hem</a></body></html>' % self.server.server_address[1]).encode('utf-8')
            self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body); return
        if self.path in SIDOR:
            body = SIDOR[self.path].encode('utf-8')
            self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
        else:
            body = '<html lang="sv"><body><h1>Sidan finns inte</h1><a href="/">Till startsidan</a></body></html>'.encode()
            self.send_response(404); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)

    def do_POST(self):
        n = int(self.headers.get('Content-Length') or 0); data = self.rfile.read(n).decode('utf-8', 'replace')
        Handler.poster.append(data)
        body = '<html lang="sv"><body><h1>Tack, vi hör av oss</h1></body></html>'.encode()
        self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)

    def log_message(self, *a):
        pass


def kor(*args, timeout=180):
    extra = ['--experimental-strip-types'] if args and args[0] == 'prova_init.mjs' else []  # init-page-filen är .ts (som MCP kräver); harnessen läser den med Nodes typavskalning
    p = subprocess.run([NODE, *extra, *args], cwd=WB, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


class Webblasare(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = http.server.HTTPServer(('127.0.0.1', 0), Handler); cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.bas = 'http://127.0.0.1:%d' % cls.port

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown(); cls.srv.server_close()

    def setUp(self):
        Handler.poster = []; Handler.huvuden = []
        self.tmp = tempfile.TemporaryDirectory(); self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_inspektera_med_kontext_grans_tillstand_och_redigerat_undantag(self):
        brief = self.d / 'PROJECT-BRIEF.md'; brief.write_text('# Brief\n§7 riktning: lugn.\n')
        hem = Path.home() / '.nortropic-hemligheter' / 'test-webblasare'; hem.mkdir(parents=True, exist_ok=True)
        und = hem / 'undantag.txt'; und.write_text('provhemlighet-ABCDEFGHIJ-0123456789\n'); und.chmod(0o600)
        try:
            code, out, err = kor('inspektera.mjs', '--adress', self.bas + '/', '--ut', str(self.d / 'insp'), '--vyer', '390', '--kontext', str(brief), '--meny', '#meny', '--undantag-fil', str(und))
            self.assertEqual(code, 0, err[-800:])
            r = json.loads((self.d / 'insp' / 'INSPEKTION.json').read_text())
            v = r['vyer']['390']
            self.assertEqual((v['status'], v['h1'], v['spill']['spill']), (200, 1, False))
            self.assertEqual(r['kontext'][0]['namn'], 'PROJECT-BRIEF.md'); self.assertEqual(len(r['kontext'][0]['sha256']), 64)
            self.assertTrue(any('localhost:1' in b['url'] for b in v['natverk']['blockerade']), 'extern bild ska blockeras och listas')
            self.assertGreaterEqual(len(v['tillstand']['tangentbord']), 3); self.assertGreaterEqual(v['tillstand']['tangentbord_utan_synlig_fokus'], 1)
            self.assertEqual(v['tillstand']['meny']['expanded'], 'true'); self.assertFalse(v['tillstand']['reflow_320']['spill']); self.assertEqual(v['tillstand']['reload_status'], 200)
            self.assertIn('efter_bakat', v['tillstand']['bakat'])
            for f in ('vy-390-forsta.png', 'vy-390-hela.png', 'vy-390-aria.txt', 'vy-390-spar.zip', 'INSPEKTION.md'):
                self.assertTrue((self.d / 'insp' / f).is_file(), f)
            self.assertIn('heading', (self.d / 'insp' / 'vy-390-aria.txt').read_text())
            text = (self.d / 'insp' / 'INSPEKTION.json').read_text() + (self.d / 'insp' / 'INSPEKTION.md').read_text()
            self.assertNotIn('provhemlighet-ABCDEFGHIJ', text); self.assertTrue(r['spar_privat'])
            self.assertTrue(any(h.get('x-vercel-protection-bypass') == 'provhemlighet-ABCDEFGHIJ-0123456789' for h in Handler.huvuden), 'undantaget ska nå målet som header')
            # tillåten tredje part får aldrig undantaget: sidan /tredje/ hämtar en bild från den andra tillåtna originen (localhost)
            Handler.huvuden = []
            code, out, err = kor('inspektera.mjs', '--adress', self.bas + '/tredje/', '--ut', str(self.d / 'insp2'), '--vyer', '1440', '--tillat', 'http://localhost:%d' % self.port, '--tillstand', 'reload', '--undantag-fil', str(und))
            self.assertEqual(code, 0, err[-400:])
            r2 = json.loads((self.d / 'insp2' / 'INSPEKTION.json').read_text())
            self.assertFalse(any('localhost' in b['url'] for b in r2['vyer']['1440']['natverk']['blockerade']), 'den tillåtna tredje parten ska inte blockeras')
            mal = [h for h in Handler.huvuden if h.get('Host') == '127.0.0.1:%d' % self.port]
            tredje = [h for h in Handler.huvuden if h.get('Host') == 'localhost:%d' % self.port]
            self.assertTrue(mal and all(h.get('x-vercel-protection-bypass') for h in mal), 'målet får undantaget')
            self.assertTrue(tredje and not any(h.get('x-vercel-protection-bypass') for h in tredje), 'tredje part får aldrig undantaget')
        finally:
            und.unlink(missing_ok=True)
            try:
                hem.rmdir()
            except OSError:
                pass

    def test_utforska_hittar_fynd_skickar_inte_utan_tillatelse_och_skriver_regressionsprov(self):
        code, out, err = kor('utforska.mjs', '--adress', self.bas + '/', '--ut', str(self.d / 'qa'), '--max-sidor', '6')
        self.assertEqual(code, 0, err[-800:])
        r = json.loads((self.d / 'qa' / 'UTFORSKNING.json').read_text())
        self.assertGreaterEqual(r['sidor'].__len__(), 4)
        vad = ' | '.join(f['vad'] for f in r['fynd'])
        self.assertIn('sidan svarar 404', vad); self.assertIn('h1-antal 2', vad); self.assertIn('utan synlig fokusmarkering', vad)
        self.assertEqual(Handler.poster, [], 'formuläret får inte skickas utan tillåtelse')
        kontakt = next(s for s in r['sidor'] if s['url'].endswith('/kontakt/'))
        self.assertEqual(kontakt['formular'][0]['tomt']['giltigt_tomt'], False); self.assertFalse(kontakt['formular'][0]['skickat']); self.assertFalse(kontakt['formular'][0]['ogiltig_epost']['giltig'])
        self.assertTrue(any('localhost:1' in b['url'] for b in r['blockerade']))
        reg = json.loads((self.d / 'qa' / 'REGRESSION.json').read_text()); self.assertGreaterEqual(len(reg['prov']), 3)
        self.assertTrue((self.d / 'qa' / 'utforskning-spar.zip').is_file())
        code, out, err = kor('utforska.mjs', '--adress', self.bas + '/kontakt/', '--ut', str(self.d / 'qa2'), '--max-sidor', '1', '--formular-far-skickas', '--testmarkering', 'TEST nortropic')
        self.assertEqual(code, 0, err[-800:])
        self.assertEqual(len(Handler.poster), 2, 'ett inskick plus ett dubbelt inskick'); self.assertIn('TEST+nortropic', Handler.poster[0])
        r2 = json.loads((self.d / 'qa2' / 'UTFORSKNING.json').read_text())
        f0 = next(s for s in r2['sidor'] if s['url'].endswith('/kontakt/'))['formular'][0]
        self.assertTrue(f0['skickat']); self.assertIn('Tack', f0['besked'] or '')
        code, out, err = kor('utforska.mjs', '--adress', self.bas + '/', '--ut', str(self.d / 'qa3'), '--regression', str(self.d / 'qa' / 'REGRESSION.json'))
        self.assertEqual(code, 0, err[-800:]); r3 = json.loads((self.d / 'qa3' / 'UTFORSKNING.json').read_text()); self.assertGreaterEqual(len(r3['sidor']), 2)

    def test_besok_avskarmar_uppgiften_bygger_konfig_och_efterkontrollerar(self):
        upp = self.d / 'UPPGIFT.md'; upp.write_text('Uppgift: hitta hur man ber om en offert och beskriv vad som hände.\nTestdata: namn Test Testsson, e-post test@example.com.\n')
        code, out, err = kor('besok.mjs', '--adress', self.bas + '/', '--uppgift', str(upp), '--ut', str(self.d / 'besok'), '--torr')
        self.assertEqual(code, 0, err[-800:])
        r = json.loads((self.d / 'besok' / 'BESOK.json').read_text())
        self.assertTrue(r['torr']); cfg = json.loads((self.d / 'besok' / 'mcp.json').read_text())
        args = cfg['mcpServers']['webblasare']['args']
        for flagga in ('--isolated', '--headless', '--allowed-origins', '--save-session', '--output-dir', '--init-page'):
            self.assertIn(flagga, args, flagga)
        self.assertIn(self.bas, args)
        prompt = (self.d / 'besok' / 'BESOKARE.md').read_text()
        self.assertIn('Uppgift: hitta hur man ber om en offert', prompt); self.assertNotIn('brief', prompt.lower())
        for dalig in ('Uppgift: läs PROJECT-BRIEF.md och bedöm sidan.', 'Uppgift: enligt briefen ska knappen vara gul.', 'Uppgift: kolla src/app/page.tsx', 'Uppgift: facit är att formuläret finns på /kontakt.'):
            upp.write_text(dalig + '\n')
            code, out, err = kor('besok.mjs', '--adress', self.bas + '/', '--uppgift', str(upp), '--ut', str(self.d / 'besok-x'), '--torr')
            self.assertEqual(code, 2, dalig)
        # qa-läge: bara mcp.json, ingen uppgift, ingen avskärmning
        code, out, err = kor('besok.mjs', '--qa', '--adress', self.bas + '/', '--ut', str(self.d / 'qa-mcp'))
        self.assertEqual(code, 0, err[-400:]); rq = json.loads((self.d / 'qa-mcp' / 'BESOK.json').read_text()); self.assertEqual(rq['lage'], 'qa'); self.assertTrue((self.d / 'qa-mcp' / 'mcp.json').is_file()); self.assertFalse((self.d / 'qa-mcp' / 'BESOKARE.md').exists())
        # MCP-flaggorna i konfigurationen finns i den pinnade versionens --help
        hjalp = subprocess.run([NODE, str(WB / 'node_modules' / '@playwright' / 'mcp' / 'cli.js'), '--help'], capture_output=True, text=True, timeout=60).stdout
        for flagga in [x for x in args if x.startswith('--')]:
            self.assertIn(flagga, hjalp, flagga)
        # init-page-filen verkställer gränsen i en riktig sida: tredje part blockeras och loggas, målet nås, undantaget bara till målet
        init = self.d / 'besok' / 'init-grans.ts'; self.assertTrue(init.is_file())
        logg = self.d / 'besok' / 'mcp-ut' / 'natverk.jsonl'
        Handler.huvuden = []
        code, out, err = kor('prova_init.mjs', '--init', str(init), '--adresser', self.bas + '/tredje/,http://localhost:%d/om/' % self.port, '--ut', str(self.d / 'init-ut.json'))
        self.assertEqual(code, 0, err[-400:])
        rader = [json.loads(l) for l in logg.read_text().splitlines() if l.strip()]
        self.assertTrue(any(r['ursprung'] == self.bas and not r['blockerad'] for r in rader)); self.assertTrue(any(r['ursprung'] == 'http://localhost:%d' % self.port and r['blockerad'] for r in rader))
        self.assertFalse(any(h.get('Host', '').startswith('localhost') for h in Handler.huvuden), 'blockerad förfrågan når aldrig servern')
        code, out, err = kor('besok.mjs', '--efterkontroll', str(logg), '--adress', self.bas + '/', '--ut', str(self.d / 'besok-e'))
        self.assertEqual(code, 1, err[-400:]); e = json.loads((self.d / 'besok-e' / 'EFTERKONTROLL.json').read_text())
        self.assertEqual(e['ursprung_utanfor'], ['http://localhost:%d' % self.port]); self.assertFalse(e['inom_gransen']); self.assertGreaterEqual(e['blockerade'], 1)
        # med undantag: initfilen privat utanför fallet, headern bara till målet
        hem = Path.home() / '.nortropic-hemligheter' / 'test-webblasare'; hem.mkdir(parents=True, exist_ok=True)
        und = hem / 'undantag2.txt'; und.write_text('provhemlighet-KLMNOPQRST-9876543210\n'); und.chmod(0o600)
        upp.write_text('Uppgift: hitta hur man ber om en offert och beskriv vad som hände.\nTestdata: namn Test Testsson, e-post test@example.com.\n')
        try:
            code, out, err = kor('besok.mjs', '--adress', self.bas + '/tredje/', '--uppgift', str(upp), '--ut', str(self.d / 'besok-u'), '--torr', '--undantag-fil', str(und), '--tillat', 'http://localhost:%d' % self.port)
            self.assertEqual(code, 0, err[-400:]); ru = json.loads((self.d / 'besok-u' / 'BESOK.json').read_text()); self.assertTrue(ru['spar_privat'])
            cfgu = json.loads((self.d / 'besok-u' / 'mcp.json').read_text()); initu = cfgu['mcpServers']['webblasare']['args'][cfgu['mcpServers']['webblasare']['args'].index('--init-page') + 1]
            self.assertFalse(Path(initu).is_relative_to(self.d), 'initfilen med undantag ligger utanför fallet'); self.assertEqual(oct(Path(initu).stat().st_mode & 0o777), '0o600')
            self.assertNotIn('provhemlighet-KLMNOPQRST', (self.d / 'besok-u' / 'BESOK.json').read_text() + (self.d / 'besok-u' / 'mcp.json').read_text())
            Handler.huvuden = []
            code, out, err = kor('prova_init.mjs', '--init', initu, '--adresser', self.bas + '/tredje/', '--ut', str(self.d / 'init-ut2.json'))
            self.assertEqual(code, 0, err[-400:])
            mal = [h for h in Handler.huvuden if h.get('Host') == '127.0.0.1:%d' % self.port]; tredje = [h for h in Handler.huvuden if h.get('Host') == 'localhost:%d' % self.port]
            self.assertTrue(mal and all(h.get('x-vercel-protection-bypass') == 'provhemlighet-KLMNOPQRST-9876543210' for h in mal))
            self.assertTrue(tredje and not any(h.get('x-vercel-protection-bypass') for h in tredje))
            import shutil; shutil.rmtree(Path(initu).parent, ignore_errors=True)
        finally:
            und.unlink(missing_ok=True)


if __name__ == '__main__':
    unittest.main()
