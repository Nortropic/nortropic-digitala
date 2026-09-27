#!/usr/bin/env python3
"""Driftkontroll: övervakning av lanserade sajter — svar, svarstid, förväntat innehåll, sitemap, certifikatets
giltighet — som en körning med kvitto, avsedd att schemaläggas (Runtimes schemalagda körning eller cron) och att läsas
av människa vid incident. Exit 1 när en incident finns, så att en schemaläggare kan larma. Inga skrivningar hos någon
leverantör; ingen självläkning: kvittot namnger vad som avviker och pekar på återgångsvägen (lansering.md).

    python3 -B verktyg/drift_kontroll.py --plan DRIFT.json --ut KATALOG [--tillat-http]

DRIFT.json: {"schema": 1, "kund": "namn", "sajter": [{"adress": "https://d.se/", "forvantat": "text som ska finnas", "max_ms": 3000, "sitemap": true, "cert_dagar_min": 14}]}
"""
import argparse
import json
import re
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit


def hamta(url, timeout=20):
    req = urllib.request.Request(url, headers={'User-Agent': 'nortropic-digitala drift'})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return {'status': r.status, 'ms': int((time.time() - t0) * 1000), 'body': r.read(300000).decode('utf-8', 'replace')}
    except urllib.error.HTTPError as e:
        return {'status': e.code, 'ms': int((time.time() - t0) * 1000), 'body': ''}
    except Exception as e:  # noqa: BLE001
        return {'status': None, 'ms': int((time.time() - t0) * 1000), 'body': '', 'fel': e.__class__.__name__}


def cert_dagar(host, port=443, timeout=10):
    ctx = ssl.create_default_context()
    with socket.create_connection((host, port), timeout=timeout) as s:
        with ctx.wrap_socket(s, server_hostname=host) as ss:
            cert = ss.getpeercert()
    slut = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z').replace(tzinfo=timezone.utc)
    return (slut - datetime.now(timezone.utc)).days


def kontrollera(plan, hamta=hamta, cert_dagar=cert_dagar, tillat_http=False):
    rader = []
    for s in plan['sajter']:
        u = urlsplit(s['adress'])
        if u.scheme != 'https' and not tillat_http:
            rader.append({'adress': s['adress'], 'incident': True, 'fynd': ['adressen är inte https']}); continue
        r = hamta(s['adress'])
        fynd = []
        if r['status'] != 200:
            fynd.append('svarar %s' % (r['status'] or r.get('fel')))
        elif s.get('forvantat') and s['forvantat'] not in r['body']:
            fynd.append('förväntad text saknas')
        if r['status'] == 200 and s.get('max_ms') and r['ms'] > s['max_ms']:
            fynd.append('svarstid %d ms över %d ms' % (r['ms'], s['max_ms']))
        if s.get('sitemap'):
            sm = hamta('%s://%s/sitemap.xml' % (u.scheme, u.netloc))
            if sm['status'] != 200:
                fynd.append('sitemap svarar %s' % (sm['status'] or sm.get('fel')))
        dagar = None
        if u.scheme == 'https' and s.get('cert_dagar_min') is not None:
            try:
                dagar = cert_dagar(u.hostname)
                if dagar < s['cert_dagar_min']:
                    fynd.append('certifikatet går ut om %d dagar' % dagar)
            except Exception as e:  # noqa: BLE001
                fynd.append('certifikatet kunde inte läsas: %s' % e.__class__.__name__)
        rader.append({'adress': s['adress'], 'status': r['status'], 'ms': r['ms'], 'cert_dagar': dagar, 'incident': bool(fynd), 'fynd': fynd})
    return {'schema': 1, 'kund': plan.get('kund'), 'tid': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'sajter': rader, 'incidenter': sum(1 for r in rader if r['incident']),
            'not': 'läsande kontroll; vid incident: läs kvittot, kontrollera värdplattformens status, återgång enligt lansering.md; ingen automatisk åtgärd'}


def main(argv=None):
    p = argparse.ArgumentParser(prog='drift_kontroll', description=__doc__.split('\n\n')[0])
    p.add_argument('--plan', required=True); p.add_argument('--ut', required=True); p.add_argument('--tillat-http', action='store_true')
    a = p.parse_args(argv)
    plan = json.loads(Path(a.plan).read_text(encoding='utf-8'))
    if plan.get('schema') != 1 or not isinstance(plan.get('sajter'), list) or not plan['sajter']:
        print(json.dumps({'vagrad': 'DRIFT.json: schema 1 och minst en sajt'})); return 2
    k = kontrollera(plan, tillat_http=a.tillat_http)
    d = Path(a.ut); d.mkdir(parents=True, exist_ok=True)
    f = d / ('DRIFT-%s.json' % re.sub(r'[^0-9TZ]', '', k['tid']))
    f.write_text(json.dumps(k, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'incidenter': k['incidenter'], 'ut': str(f)}))
    return 1 if k['incidenter'] else 0


if __name__ == '__main__':
    sys.exit(main())
