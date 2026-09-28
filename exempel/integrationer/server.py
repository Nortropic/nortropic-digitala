#!/usr/bin/env python3
"""Körbart loopbackexempel. Kunddrift ska använda kundens host och beständiga DB.

python3 -B exempel/integrationer/server.py --inkorg /privat/prov/inbox.sqlite --port 3182
Inga externa anrop; en sparad förfrågan betyder inte e-post eller personmottagning.
"""
import argparse
import json
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'verktyg'))
from integrationer_adapter import Fel, privat_fil
from integrationer_mottagning import Inkorg, MAX_BODY, las_json, webhook


PAGE = b'''<!doctype html><html lang="sv"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Lokalt integrationsprov</title>
<h1>Lokalt integrationsprov</h1><p>Endast syntetiska uppgifter. Ingen e-post skickas.</p>
<form><label>Namn <input name="name" required maxlength="100"></label><br>
<label>E-post <input name="email" type="email" required></label><br>
<label>Meddelande <textarea name="message" required maxlength="4000"></textarea></label><br>
<button>Spara provfr\xc3\xa5ga</button></form><p role="status" id="status"></p>
<script>let key=crypto.randomUUID();document.querySelector('form').onsubmit=async e=>{e.preventDefault();const s=document.querySelector('#status');s.textContent='Sparar...';try{const r=await fetch('/lead',{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':key},body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});const d=await r.json();s.textContent=r.ok?'Sparad i provets inkorg. Ingen e-post skickad; ingen person har bekr\xc3\xa4ftat mottagning.':'Inte sparad: '+d.error;}catch{s.textContent='Svaret kom inte fram. F\xc3\xb6rs\xc3\xb6k igen med samma uppgifter.'}};</script></html>'''


def handler(inbox, owner, follow_up, webhooks=None):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Ingen body, URL-query eller persondata i terminalen.

        def reply(self, status, body, kind='application/json'):
            raw = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(status)
            self.send_header('Content-Type', kind + '; charset=utf-8')
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            if self.path == '/':
                return self.reply(200, PAGE, 'text/html')
            if self.path == '/health':
                return self.reply(200, {'mode': 'local_contract_example', 'external_calls': False})
            self.reply(404, {'error': 'not_found'})

        def do_POST(self):
            try:
                size = self.headers.get('Content-Length', '')
                if not size.isdigit() or int(size) > MAX_BODY:
                    raise Fel('for_stor_eller_okand_body', 413)
                if self.headers.get('Transfer-Encoding') or self.headers.get_content_type() != 'application/json':
                    raise Fel('application_json_kravs', 415)
                raw = self.rfile.read(int(size))
                if self.path == '/lead':
                    origin = 'http://127.0.0.1:' + str(self.server.server_port)
                    if self.headers.get('Origin') != origin:
                        raise Fel('fel_origin', 403)
                    value = inbox.lead(self.headers.get('Idempotency-Key'), las_json(raw), owner, follow_up)
                elif self.path.startswith('/webhook/') and self.path.count('/') == 2:
                    provider = self.path.rsplit('/', 1)[1]
                    if provider not in (webhooks or {}):
                        raise Fel('webhook_inte_konfigurerad', 404)
                    value = inbox.receive(webhook(provider, raw, dict(self.headers), webhooks[provider]))
                else:
                    raise Fel('not_found', 404)
                self.reply(200, value)
            except Fel as e:
                self.reply(e.status, {'error': e.kod, 'received_by_person': False})
            except sqlite3.Error:
                self.reply(503, {'error': 'lagring_otillganglig', 'received_by_person': False})
    return Handler


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inkorg', required=True)
    p.add_argument('--port', default=3182, type=int)
    p.add_argument('--ansvarig', default='Provansvarig')
    p.add_argument('--uppfoljning', default='Kontrollera eget syntetiskt prov')
    p.add_argument('--webhook-config')
    a = p.parse_args()
    config = json.loads(privat_fil(a.webhook_config).read_text()) if a.webhook_config else {}
    server = ThreadingHTTPServer(('127.0.0.1', a.port), handler(Inkorg(a.inkorg), a.ansvarig, a.uppfoljning, config))
    print('Lokalt kontraktsexempel: http://127.0.0.1:' + str(server.server_port), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
