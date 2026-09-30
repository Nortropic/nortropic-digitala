#!/usr/bin/env python3
"""Driftkontroll: övervakning av lanserade sajter — svar, svarstid, förväntat innehåll, sitemap, certifikatets
giltighet — som en körning med kvitto, avsedd att schemaläggas (Runtimes schemalagda körning eller cron) och att läsas
av människa vid incident. Exit 1 när en incident finns, så att en schemaläggare kan larma. Inga skrivningar hos någon
leverantör; ingen självläkning: kvittot namnger vad som avviker och pekar på återgångsvägen (lansering.md).

    python3 -B verktyg/drift_kontroll.py --plan DRIFT.json --ut KATALOG [--tillat-http]

DRIFT.json: {"schema": 1, "kund": "namn", "sajter": [{"adress": "https://d.se/", "forvantat": "text som ska finnas", "max_ms": 3000, "sitemap": true, "cert_dagar_min": 14}]}
"""
import argparse
import http.client
import json
import queue
import re
import socket
import ssl
import sys
import threading
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

MAX_BODY = 300000


def ursprung(url):
    u = urlsplit(url)
    if u.scheme not in ('http', 'https') or not u.hostname or u.username or u.password:
        raise ValueError('ogiltig http-adress')
    return u.scheme, u.hostname.lower(), u.port or (443 if u.scheme == 'https' else 80)


class IngenRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Anropstak(ValueError):
    pass


def _ta_anrop(budget):
    if budget is not None:
        if budget['kvar'] <= 0:
            raise Anropstak()
        budget['kvar'] -= 1


def _retry_after(value):
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        try:
            seconds = (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds()
        except (TypeError, ValueError, OverflowError):
            seconds = 1
    return min(30, max(0, seconds))


def _opener(state):
    def connection(kind, host, **kwargs):
        if state['stop'].is_set(): raise TimeoutError()
        conn = kind(host, **kwargs); state['connections'].append(conn)
        original = conn.connect
        def connect():
            if state['stop'].is_set(): raise TimeoutError()
            original()
            if state['stop'].is_set():
                conn.close(); raise TimeoutError()
        conn.connect = connect
        return conn
    class HTTP(urllib.request.HTTPHandler):
        def http_open(self, req):
            return self.do_open(lambda host, **kw: connection(http.client.HTTPConnection, host, **kw), req)
    class HTTPS(urllib.request.HTTPSHandler):
        def https_open(self, req):
            return self.do_open(lambda host, **kw: connection(http.client.HTTPSConnection, host, **kw), req,
                                context=ssl.create_default_context())
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), IngenRedirect(), HTTP(), HTTPS())


def _socket(response):
    # HTTPError wraps HTTPResponse, which wraps a buffered socket file.
    obj = response
    for _ in range(6):
        sock = getattr(obj, '_sock', None)
        if sock is not None: return sock
        obj = getattr(obj, 'fp', None) or getattr(obj, 'raw', None)
        if obj is None: return None
    return None


def _hamta(url, timeout=20, *, max_hopp=0, omforsok=0, paus=time.sleep,
           klocka=time.monotonic, budget=None, eget_ursprung=None,
           forvantad_slutadress=None, handlingslank=False, state):
    """En deadline delas av kropp, hopp, pauser och omförsök. Bara GET."""
    start = klocka(); deadline = start + timeout
    total_anrop = 0; first_error = None
    for attempt in range(1, min(2, max(0, omforsok)) + 2):
        state['progress'].update(forsok=attempt, forsta_felet=first_error,
                                 slutadress_observerad=False, status=None, url=url, hopp=[])
        current = url; hops = []; status = None; first_status = None; retry = None
        result = {'status': None, 'url': current, 'slutadress_observerad': False, 'body': '', 'for_stor': False}
        try:
            while True:
                ursprung(current)
                if eget_ursprung is not None and ursprung(current) != eget_ursprung:
                    raise ValueError('annat ursprung vägras före nätkontakt')
                remaining = deadline - klocka()
                if remaining <= 0 or state['stop'].is_set():
                    raise TimeoutError()
                _ta_anrop(budget); total_anrop += 1
                state['progress']['anrop'] = total_anrop
                req = urllib.request.Request(current, method='GET', headers={'User-Agent': 'nortropic-digitala drift'})
                try:
                    response = _opener(state).open(req, timeout=remaining)
                except urllib.error.HTTPError as error:
                    response = error
                with response as r:
                    status = r.status
                    if first_status is None:
                        first_status = status
                    redirect = status in (301, 302, 303, 307, 308) and bool(max_hopp)
                    # A redirect is an observed intermediate response, never a final
                    # destination, even if its target or the hop limit is refused.
                    result.update(status=None if redirect else status, slutadress_observerad=not redirect,
                                  url=r.geturl() if hasattr(r, 'geturl') else current)
                    state['progress'].update(status=result['status'], url=result['url'],
                                             slutadress_observerad=not redirect, forsta_status=first_status, hopp=list(hops))
                    active_socket = _socket(r)
                    if active_socket is not None: state['sockets'].append(active_socket)
                    headers = getattr(r, 'headers', {})
                    retry = headers.get('Retry-After')
                    if redirect:
                        target = urljoin(current, headers.get('Location', ''))
                        if not headers.get('Location') or len(hops) >= max_hopp:
                            raise ValueError('omdirigering saknar mål eller har för många hopp')
                        if eget_ursprung is not None and ursprung(target) != eget_ursprung:
                            result['vagrad_omdirigering'] = target
                            raise ValueError('annat ursprung vägras före nätkontakt')
                        hops.append({'status': status, 'fran': current, 'till': target})
                        current = target
                        result.update(url=current, slutadress_observerad=False)
                        state['progress'].update(url=current, slutadress_observerad=False, hopp=list(hops))
                        continue
                    raw = bytearray()
                    while len(raw) <= MAX_BODY:
                        remaining = deadline - klocka()
                        if remaining <= 0:
                            raise TimeoutError()
                        sock = active_socket
                        if sock is not None and sock.fileno() >= 0:
                            sock.settimeout(remaining)
                        # read1 returns available bytes, unlike read(n) waiting for a full chunk.
                        reader = getattr(r, 'read1', r.read)
                        chunk = reader(min(8192, MAX_BODY + 1 - len(raw)))
                        if klocka() >= deadline:
                            raise TimeoutError()
                        if not chunk:
                            info = r.fp if isinstance(r, urllib.error.HTTPError) else r
                            if (getattr(info, 'length', None) or 0) > 0:
                                raise http.client.IncompleteRead(bytes(raw), info.length)
                            break
                        raw.extend(chunk)
                    result.update(body=raw[:MAX_BODY].decode('utf-8', 'replace'), for_stor=len(raw) > MAX_BODY)
                    break
        except Exception as error:  # noqa: BLE001
            reason = error.reason if isinstance(error, urllib.error.URLError) else error
            result['fel'] = 'TimeoutError' if isinstance(reason, (TimeoutError, socket.timeout)) else error.__class__.__name__
        result.update(ms=int((klocka() - start) * 1000), forsok=attempt, anrop=total_anrop,
                      forsta_status=first_status, hopp=hops, forsta_felet=first_error)
        retryable = result.get('fel') == 'TimeoutError' or (not result.get('fel') and status in (429, 500, 502, 503, 504))
        wrong_destination = (result['slutadress_observerad'] and forvantad_slutadress and normalisera_adress(result['url']) != normalisera_adress(forvantad_slutadress))
        action_root = handlingslank and hops and (urlsplit(result['url']).path or '/') == '/'
        if wrong_destination or action_root or not retryable or attempt > omforsok or klocka() >= deadline:
            return result
        if first_error is None:
            first_error = 'första försöket: ' + ('tidsgräns' if result.get('fel') == 'TimeoutError' else 'svarar %s' % status)
        state['progress'].update(result, forsta_felet=first_error)
        if budget is not None and budget['kvar'] <= 0:
            result.update(fel='Anropstak', forsta_felet=first_error)
            return result
        paus(min(_retry_after(retry), max(0, deadline - klocka())))
        if state['stop'].is_set() or klocka() >= deadline:
            result.update(fel='TimeoutError', forsta_felet=first_error, ms=int((klocka()-start)*1000))
            return result
    return result


def hamta(url, timeout=20, **options):
    """Wall-clock guard also covers DNS, TLS and slow headers; it never waits for cleanup."""
    if options.get('forvantad_slutadress'):
        normalisera_adress(options['forvantad_slutadress'])
    started = time.monotonic(); answer = queue.Queue(maxsize=1)
    state = {'stop': threading.Event(), 'connections': [], 'sockets': [], 'progress': {
        'status': None, 'url': url, 'slutadress_observerad': False, 'body': '', 'for_stor': False, 'forsok': 0,
        'anrop': 0, 'forsta_status': None, 'hopp': [], 'forsta_felet': None}}
    def read():
        answer.put(_hamta(url, timeout, state=state, **options))
    thread = threading.Thread(target=read, daemon=True)
    thread.start()
    try:
        return answer.get(timeout=max(0, timeout - (time.monotonic() - started)))
    except queue.Empty:
        state['stop'].set()
        sockets = list(state['sockets']) + [c.sock for c in list(state['connections']) if c.sock is not None]
        for sock in sockets:
            try: sock.shutdown(socket.SHUT_RDWR)
            except OSError: pass
        # An OS DNS call cannot be cancelled by Python. Its daemon may finish later,
        # but connect() checks cancellation before any HTTP request is sent.
        return {**state['progress'], 'fel': 'TimeoutError', 'ms': int((time.monotonic() - started) * 1000)}


def _las(fetch, url, *, budget=None, origin=None, expected=None, action=False):
    if fetch is hamta:
        return fetch(url, max_hopp=5, omforsok=2, budget=budget, eget_ursprung=origin,
                     forvantad_slutadress=expected, handlingslank=action)
    # The injected seam represents exactly one read; production owns every hop/retry.
    _ta_anrop(budget)
    return fetch(url)


class _Titel(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True); self.inside = False; self.parts = []
        self.feed(text); self.close()
    def handle_starttag(self, tag, attrs):
        if tag == 'title': self.inside = True
    def handle_endtag(self, tag):
        if tag == 'title': self.inside = False
    def handle_data(self, text):
        if self.inside: self.parts.append(text)


FELTITLAR = ('not found', '404', 'finns inte', 'hittades inte', 'kunde inte hittas',
             'no longer available', 'page does not exist', "page doesn't exist")


def normalisera_adress(url):
    u = urlsplit(url)
    return ursprung(url), u.path.rstrip('/') or '/', u.query


def _titeltext(r):
    # Title is RCDATA in HTML: literal tag-like text inside it must also be removed.
    text = ''.join(_Titel(r.get('body', '')).parts)
    return ' '.join(re.sub(r'<[^>]*>', '', text).split())


def _meta(r, adress, expected=None):
    title = _titeltext(r)
    actual = r.get('url', adress) if r.get('slutadress_observerad', r.get('status') is not None) else None
    return {'forvantad_slutadress': expected, 'slutadress': actual, 'titel': title[:80],
            'forsok': r.get('forsok', 1), 'forsta_felet': r.get('forsta_felet')}


def _fynd(r, adress, expected=None, text=None):
    found = []
    if r['status'] != 200 or r.get('fel'):
        found.append('tidsgräns' if r.get('fel') == 'TimeoutError' else 'svarar %s' % (r.get('fel') or r['status']))
    elif text and text not in r.get('body', ''):
        found.append('förväntad text saknas')
    title = _titeltext(r).lower()
    if r['status'] == 200 and any(word in title for word in FELTITLAR):
        found.append('felsida med status 200')
    if expected and r.get('slutadress_observerad', r.get('status') is not None) and normalisera_adress(r.get('url', adress)) != normalisera_adress(expected):
        found.append('landar på annan adress: ' + r.get('url', adress))
    return found


def cert_dagar(host, port=443, timeout=10):
    """Certificate read bounded across DNS, connect and TLS handshake, not only socket calls."""
    deadline = time.monotonic() + timeout
    stop = threading.Event(); sockets = []; answer = queue.Queue(maxsize=1)
    def read():
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((host, port), timeout=max(0.001, deadline-time.monotonic())) as raw:
                sockets.append(raw)
                if stop.is_set() or time.monotonic() >= deadline: raise TimeoutError()
                with ctx.wrap_socket(raw, server_hostname=host, do_handshake_on_connect=False) as secure:
                    sockets.append(secure)
                    if stop.is_set() or time.monotonic() >= deadline: raise TimeoutError()
                    secure.settimeout(max(0.001, deadline-time.monotonic()))
                    secure.do_handshake()
                    cert = secure.getpeercert()
            end = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z').replace(tzinfo=timezone.utc)
            answer.put(((end-datetime.now(timezone.utc)).days, None))
        except Exception as error:
            answer.put((None, error))
    threading.Thread(target=read, daemon=True).start()
    try:
        value, error = answer.get(timeout=max(0, deadline-time.monotonic()))
    except queue.Empty:
        stop.set()
        for sock in list(sockets):
            try: sock.shutdown(socket.SHUT_RDWR)
            except OSError: pass
        raise TimeoutError() from None
    if error: raise error
    return value


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


def kontrollera_sitemap(adress, tak, hamta, slutadresser=None):
    """Ett indexled. Alla extra GET, även hopp/omförsök, delar samma budget."""
    origin = ursprung(adress); u = urlsplit(adress)
    root_url = urlunsplit((u.scheme, u.netloc, '/sitemap.xml', '', ''))
    budget = {'kvar': tak + 1}; slutadresser = slutadresser or {}
    k = {'tak': tak, 'provade': 0, 'over_taket': 0, 'annat_ursprung': 0,
         'indexfiler_provade': 0, 'indexfiler_oprovade': 0, 'sidor': [], 'kartor': [], 'fynd': [], 'ofullstandiga': 0}
    urls = set()
    def las_karta(url):
        r = _las(hamta, url, budget=budget, origin=origin, expected=slutadresser.get(url))
        k['kartor'].append({'adress': url, 'status': r['status'], **_meta(r, url, slutadresser.get(url))})
        if r.get('fel') == 'Anropstak':
            raise Anropstak()
        findings = _fynd(r, url, slutadresser.get(url))
        if findings:
            raise ValueError('; '.join(findings))
        return sitemap_adresser(r)
    try:
        index, locs = las_karta(root_url)
        if index:
            for loc in locs:
                if ursprung(loc) != origin:
                    k['annat_ursprung'] += 1; continue
                if budget['kvar'] <= 0:
                    k['indexfiler_oprovade'] += 1; continue
                k['indexfiler_provade'] += 1
                try:
                    child_index, child_urls = las_karta(loc)
                    if child_index:
                        raise ValueError('index djupare än ett led stöds inte')
                    urls.update(child_urls)
                except Anropstak:
                    k['ofullstandiga'] += 1
                except ValueError as e:
                    k['fynd'].append('sitemap %s: %s' % (loc, e))
        else:
            urls.update(locs)
    except Anropstak:
        k['ofullstandiga'] += 1
    except ValueError as e:
        k['fynd'].append('sitemap %s: %s' % (root_url, e))
    own = []
    for loc in sorted(urls):
        if ursprung(loc) != origin:
            k['annat_ursprung'] += 1
        else:
            own.append(loc)
    for loc in own:
        if budget['kvar'] <= 0:
            k['over_taket'] += 1; continue
        r = _las(hamta, loc, budget=budget, origin=origin, expected=slutadresser.get(loc)); k['provade'] += 1
        k['sidor'].append({'adress': loc, 'status': r['status'], 'ms': r['ms'], **_meta(r, loc, slutadresser.get(loc))})
        if r.get('fel') == 'Anropstak':
            k['ofullstandiga'] += 1
        else:
            k['fynd'].extend(loc + ': ' + f for f in _fynd(r, loc, slutadresser.get(loc)))
    k['anrop'] = tak + 1 - budget['kvar']
    return k


def handlingskontroll(h, site, hamta, tillat_http=False):
    row = {'namn': h['namn'], 'adress': h['adress'], 'lage': 'ok', 'fynd': [], 'skal': None}
    try:
        external = ursprung(h['adress']) != ursprung(site)
        if urlsplit(h['adress']).scheme != 'https' and not tillat_http:
            raise ValueError('adressen är inte https')
    except ValueError as e:
        row.update(lage='incident', fynd=[str(e)]); return row
    expected = h.get('forvantad_slutadress')
    r = _las(hamta, h['adress'], expected=expected, action=True)
    row.update(status=r['status'], ms=r['ms'], **_meta(r, h['adress'], expected))
    challenge = r['status'] == 403 or any(x in r.get('body', '').lower() for x in
        ('cf-chl-', 'challenge-platform', 'verify you are human', 'checking your browser'))
    timeout = r.get('fel') in ('TimeoutError', 'timeout', 'SocketTimeout', 'tidsgrans')
    # A known wrong destination/soft-404 remains an incident even with an uncertain response.
    semantic = [f for f in _fynd(r, h['adress'], expected) if f == 'felsida med status 200' or f.startswith('landar på annan adress:')]
    landed_root = (r.get('slutadress_observerad', r.get('status') is not None) and r.get('hopp') and (urlsplit(r.get('url', h['adress'])).path or '/') == '/')
    if landed_root:
        semantic.append('handlingslänken omdirigerar till startsidan')
    if external and (challenge or r['status'] == 429 or timeout) and not semantic:
        row.update(lage='okant', skal='skydd/utmaning' if challenge else '429' if r['status'] == 429 else 'tidsgräns')
    else:
        row['fynd'] = _fynd(r, h['adress'], expected, h.get('forvantat'))
        if landed_root:
            row['fynd'].append('handlingslänken omdirigerar till startsidan')
        row['lage'] = 'incident' if row['fynd'] else 'ok'
    if not expected:
        row['skal'] = (row['skal'] + '; ' if row['skal'] else '') + 'baslinjen saknas: förväntad slutadress från lanseringsdagen'
        if row['lage'] == 'ok':
            row['lage'] = 'okant'
    return row


def kontrollera(plan, hamta=hamta, cert_dagar=cert_dagar, tillat_http=False):
    rader = []
    for s in plan['sajter']:
        u = urlsplit(s['adress'])
        if u.scheme != 'https' and not tillat_http:
            rader.append({'adress': s['adress'], 'incident': True, 'fynd': ['adressen är inte https']}); continue
        r = _las(hamta, s['adress'], expected=s.get('forvantad_slutadress'))
        fynd = _fynd(r, s['adress'], s.get('forvantad_slutadress'), s.get('forvantat'))
        if r['status'] == 200 and s.get('max_ms') and r['ms'] > s['max_ms']:
            fynd.append('svarstid %d ms över %d ms' % (r['ms'], s['max_ms']))
        sm = None
        okanda = []
        if s.get('sitemap'):
            tak = s.get('sitemap_tak', 50)
            if type(tak) is not int or not 1 <= tak <= 10000:
                raise ValueError('sitemap_tak ska vara heltal 1–10000')
            sm = kontrollera_sitemap(s['adress'], tak, hamta, s.get('slutadresser'))
            fynd.extend(sm['fynd'])
            if sm['over_taket'] or sm['indexfiler_oprovade'] or sm['ofullstandiga']:
                okanda.append('sitemap: %d kända sidrutter och %d indexfiler oprövade, %d avbrutna på grund av taket' % (sm['over_taket'], sm['indexfiler_oprovade'], sm['ofullstandiga']))
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
        rader.append({'adress': s['adress'], 'status': r['status'], 'ms': r['ms'], **_meta(r, s['adress'], s.get('forvantad_slutadress')), 'cert_dagar': dagar, 'incident': bool(fynd), 'fynd': fynd,
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
