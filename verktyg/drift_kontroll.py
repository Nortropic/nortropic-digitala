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
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

MAX_BODY = 300000


def ursprung(url):
    u = urlsplit(url)
    if u.scheme not in ('http', 'https') or not u.hostname or u.username or u.password:
        raise ValueError('ogiltig http-adress')
    return u.scheme, u.hostname.lower(), u.port or (443 if u.scheme == 'https' else 80)


class IngenRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def hamta(url, timeout=20):
    req = urllib.request.Request(url, method='GET', headers={'User-Agent': 'nortropic-digitala drift'})
    t0 = time.time()
    status = None
    try:
        try:
            response = urllib.request.build_opener(IngenRedirect()).open(req, timeout=timeout)
        except urllib.error.HTTPError as error:
            response = error
        with response as r:
            status = r.status
            raw = r.read(MAX_BODY + 1)
            return {'status': status, 'ms': int((time.time() - t0) * 1000), 'body': raw[:MAX_BODY].decode('utf-8', 'replace'), 'for_stor': len(raw) > MAX_BODY}
    except Exception as e:  # noqa: BLE001
        reason = e.reason if isinstance(e, urllib.error.URLError) else e
        return {'status': status, 'ms': int((time.time() - t0) * 1000), 'body': '',
                'fel': 'TimeoutError' if isinstance(reason, (TimeoutError, socket.timeout)) else e.__class__.__name__}


def cert_dagar(host, port=443, timeout=10):
    ctx = ssl.create_default_context()
    with socket.create_connection((host, port), timeout=timeout) as s:
        with ctx.wrap_socket(s, server_hostname=host) as ss:
            cert = ss.getpeercert()
    slut = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z').replace(tzinfo=timezone.utc)
    return (slut - datetime.now(timezone.utc)).days


def sitemap_adresser(resultat):
    if resultat['status'] != 200 or resultat.get('fel'):
        raise ValueError('svarar %s' % (resultat.get('fel') or resultat['status']))
    text = resultat.get('body', '')
    if resultat.get('for_stor') or len(text.encode('utf-8')) > MAX_BODY:
        raise ValueError('över storleksgränsen')
    if '\x00' in text or '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
        raise ValueError('DTD/ENTITY vägras')
    try:
        root = ET.fromstring(text)
        ns = '{http://www.sitemaps.org/schemas/sitemap/0.9}' if root.tag.startswith('{') else ''
        if root.tag not in (ns + 'urlset', ns + 'sitemapindex'):
            raise ValueError('okänt sitemapformat')
        index = root.tag == ns + 'sitemapindex'
        urls = []
        for row in root.findall(ns + ('sitemap' if index else 'url')):
            nodes = row.findall(ns + 'loc')
            if len(nodes) != 1 or not nodes[0].text:
                raise ValueError('loc saknas eller är tvetydig')
            u = nodes[0].text.strip(); ursprung(u)
            p = urlsplit(u)
            urls.append(urlunsplit((p.scheme, p.netloc, p.path or '/', p.query, '')))
        return index, sorted(set(urls))
    except ET.ParseError:
        raise ValueError('oläsbar XML') from None


def kontrollera_sitemap(adress, tak, hamta):
    """Ett indexled. Barnkartor och sidprov delar taket för extra GET-anrop."""
    origin = ursprung(adress); u = urlsplit(adress)
    root_url = urlunsplit((u.scheme, u.netloc, '/sitemap.xml', '', ''))
    k = {'tak': tak, 'provade': 0, 'over_taket': 0, 'annat_ursprung': 0,
         'indexfiler_provade': 0, 'indexfiler_oprovade': 0, 'sidor': [], 'fynd': []}
    urls = set()
    try:
        index, locs = sitemap_adresser(hamta(root_url))
        if index:
            for loc in locs:
                if ursprung(loc) != origin:
                    k['annat_ursprung'] += 1; continue
                if k['indexfiler_provade'] >= tak:
                    k['indexfiler_oprovade'] += 1; continue
                k['indexfiler_provade'] += 1
                try:
                    child_index, child_urls = sitemap_adresser(hamta(loc))
                    if child_index:
                        raise ValueError('index djupare än ett led stöds inte')
                    urls.update(child_urls)
                except ValueError as e:
                    k['fynd'].append('sitemap %s: %s' % (loc, e))
        else:
            urls.update(locs)
    except ValueError as e:
        k['fynd'].append('sitemap %s: %s' % (root_url, e))
    own = []
    for loc in sorted(urls):
        if ursprung(loc) != origin:
            k['annat_ursprung'] += 1
        else:
            own.append(loc)
    available = max(0, tak - k['indexfiler_provade'])
    k['over_taket'] = max(0, len(own) - available)
    for loc in own[:available]:
        r = hamta(loc); k['provade'] += 1
        k['sidor'].append({'adress': loc, 'status': r['status'], 'ms': r['ms']})
        if r['status'] != 200 or r.get('fel'):
            k['fynd'].append('%s: svarar %s' % (loc, r.get('fel') or r['status']))
    return k


def handlingskontroll(h, site, hamta, tillat_http=False):
    row = {'namn': h['namn'], 'adress': h['adress'], 'lage': 'ok', 'fynd': [], 'skal': None}
    try:
        external = ursprung(h['adress']) != ursprung(site)
        if urlsplit(h['adress']).scheme != 'https' and not tillat_http:
            raise ValueError('adressen är inte https')
    except ValueError as e:
        row.update(lage='incident', fynd=[str(e)]); return row
    r = hamta(h['adress']); row.update(status=r['status'], ms=r['ms'])
    challenge = r['status'] == 403 or any(x in r.get('body', '').lower() for x in
        ('cf-chl-', 'challenge-platform', 'verify you are human', 'checking your browser'))
    timeout = r.get('fel') in ('TimeoutError', 'timeout', 'SocketTimeout', 'tidsgrans')
    if external and (challenge or r['status'] == 429 or timeout):
        row.update(lage='okant', skal='skydd/utmaning' if challenge else '429' if r['status'] == 429 else 'tidsgräns')
    else:
        if r['status'] != 200 or r.get('fel'):
            row['fynd'].append('svarar %s' % (r.get('fel') or r['status']))
        elif h.get('forvantat') and h['forvantat'] not in r.get('body', ''):
            row['fynd'].append('förväntad text saknas')
        row['lage'] = 'incident' if row['fynd'] else 'ok'
    return row


def kontrollera(plan, hamta=hamta, cert_dagar=cert_dagar, tillat_http=False):
    rader = []
    for s in plan['sajter']:
        u = urlsplit(s['adress'])
        if u.scheme != 'https' and not tillat_http:
            rader.append({'adress': s['adress'], 'incident': True, 'fynd': ['adressen är inte https']}); continue
        r = hamta(s['adress'])
        fynd = []
        if r['status'] != 200 or r.get('fel'):
            fynd.append('svarar %s' % (r.get('fel') or r['status']))
        elif s.get('forvantat') and s['forvantat'] not in r['body']:
            fynd.append('förväntad text saknas')
        if r['status'] == 200 and s.get('max_ms') and r['ms'] > s['max_ms']:
            fynd.append('svarstid %d ms över %d ms' % (r['ms'], s['max_ms']))
        sm = None
        okanda = []
        if s.get('sitemap'):
            tak = s.get('sitemap_tak', 50)
            if type(tak) is not int or not 1 <= tak <= 10000:
                raise ValueError('sitemap_tak ska vara heltal 1–10000')
            sm = kontrollera_sitemap(s['adress'], tak, hamta)
            fynd.extend(sm['fynd'])
            if sm['over_taket'] or sm['indexfiler_oprovade']:
                okanda.append('sitemap: %d kända sidrutter och %d indexfiler oprövade på grund av taket' % (sm['over_taket'], sm['indexfiler_oprovade']))
        handlingar = [handlingskontroll(h, s['adress'], hamta, tillat_http) for h in s.get('handlingar', [])]
        for h in handlingar:
            fynd.extend(h['namn'] + ': ' + f for f in h['fynd'])
            if h['lage'] == 'okant':
                okanda.append(h['namn'] + ': ' + h['skal'])
        dagar = None
        if u.scheme == 'https' and s.get('cert_dagar_min') is not None:
            try:
                dagar = cert_dagar(u.hostname)
                if dagar < s['cert_dagar_min']:
                    fynd.append('certifikatet går ut om %d dagar' % dagar)
            except Exception as e:  # noqa: BLE001
                fynd.append('certifikatet kunde inte läsas: %s' % e.__class__.__name__)
        rader.append({'adress': s['adress'], 'status': r['status'], 'ms': r['ms'], 'cert_dagar': dagar, 'incident': bool(fynd), 'fynd': fynd,
                      'lage': 'incident' if fynd else 'okant' if okanda else 'ok', 'okanda': okanda, 'sitemap': sm, 'handlingar': handlingar})
    return {'schema': 1, 'kund': plan.get('kund'), 'tid': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'sajter': rader, 'incidenter': sum(1 for r in rader if r['incident']), 'okanda': sum(len(r.get('okanda', [])) for r in rader),
            'not': 'läsande kontroll; vid incident: läs kvittot, kontrollera värdplattformens status, återgång enligt lansering.md; ingen automatisk åtgärd'}


def main(argv=None):
    p = argparse.ArgumentParser(prog='drift_kontroll', description=__doc__.split('\n\n')[0])
    p.add_argument('--plan', required=True); p.add_argument('--ut', required=True); p.add_argument('--tillat-http', action='store_true')
    a = p.parse_args(argv)
    plan = json.loads(Path(a.plan).read_text(encoding='utf-8'))
    if plan.get('schema') != 1 or not isinstance(plan.get('sajter'), list) or not plan['sajter']:
        print(json.dumps({'vagrad': 'DRIFT.json: schema 1 och minst en sajt'})); return 2
    try:
        k = kontrollera(plan, tillat_http=a.tillat_http)
    except (ValueError, KeyError, TypeError) as e:
        print(json.dumps({'vagrad': 'ogiltig DRIFT.json: ' + str(e)}, ensure_ascii=False)); return 2
    d = Path(a.ut); d.mkdir(parents=True, exist_ok=True)
    f = d / ('DRIFT-%s.json' % re.sub(r'[^0-9TZ]', '', k['tid']))
    f.write_text(json.dumps(k, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'incidenter': k['incidenter'], 'ut': str(f)}))
    return 1 if k['incidenter'] else 0


if __name__ == '__main__':
    sys.exit(main())
