#!/usr/bin/env python3
"""Sökkonsol (Google Search Console): ägarskapsväg, egenskap, sitemap, URL-inspektion och sökdata genom Googles
publika REST-API:er, med kvitto per anrop. Ingen mockad "framgång": utan åtkomst skrivs en anropsplan (--plan) som
visar exakt vilka anrop som skulle göras; med åtkomst (--live) görs anropen och kvittot bär statuskoder och svar.

    python3 -B verktyg/sokkonsol.py plan   --verksamhet VERKSAMHET.json [--doman d.se] [--urler /,/tjanster/] --ut KVITTO.json
    python3 -B verktyg/sokkonsol.py token  --verksamhet … --ut KVITTO.json --live            # META-token att rendera i <head>
    python3 -B verktyg/sokkonsol.py verifiera --verksamhet … --ut KVITTO.json --live         # kräver taggen live på kanonisk domän
    python3 -B verktyg/sokkonsol.py sitemap|inspektera|sokdata … --live

Åtkomst (aldrig utskriven): en privat fil (rättighet 0600) angiven med --atkomst, i formen
{"typ": "oauth", "client_id": …, "client_secret": …, "refresh_token": …} (OAuth 2.0-klient med scopes webmasters och
siteverification) eller {"typ": "tjanstekonto", "client_email": …, "private_key": …} (tjänstekontonyckel; JWT signeras
med systemets openssl). Utan --atkomst vägras --live. Verksamheter med fiktiv: true vägras alltid för live
(ingen verklig egenskap för fiktiva verksamheter). Värdplattformens förhandsvisningsdomäner vägras.

API-referens (Google, lästa 2026-09-27): Site Verification API v1 (webResource getToken/insert/update, metod META),
Search Console API (webmasters v3: sites.add, sitemaps.submit/list, searchanalytics.query; v1: urlInspection.index.inspect).
"""
import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verksamhetsuppgifter as vu  # noqa: E402

SCOPES = 'https://www.googleapis.com/auth/webmasters https://www.googleapis.com/auth/siteverification'
TOKEN_URL = 'https://oauth2.googleapis.com/token'
SV = 'https://www.googleapis.com/siteVerification/v1'
WM = 'https://www.googleapis.com/webmasters/v3'
SC = 'https://searchconsole.googleapis.com/v1'
FORHANDSVISNINGSSUFFIX = '.vercel.app'  # värdplattformens förhandsvisningsdomäner får aldrig bli sökkonsol-egenskaper
DOK = {'siteverification': 'https://developers.google.com/site-verification/v1/getting_started',
       'searchconsole': 'https://developers.google.com/webmaster-tools/v1/api_reference_index',
       'errors': 'https://developers.google.com/webmaster-tools/v1/errors',
       'urlinspection': 'https://developers.google.com/webmaster-tools/v1/urlInspection.index/inspect'}


class Vagrad(Exception):
    pass


def site_url(doman):
    return 'https://%s/' % doman


def anropsplan(doman, urler, dagar=28):
    """Anropen i ordning, med nyttolast; det som --live gör och inget annat."""
    s = site_url(doman)
    slut = time.strftime('%Y-%m-%d', time.gmtime()); start = time.strftime('%Y-%m-%d', time.gmtime(time.time() - dagar * 86400))
    return [
        {'steg': 'token', 'metod': 'POST', 'url': SV + '/token', 'nyttolast': {'site': {'type': 'SITE', 'identifier': s}, 'verificationMethod': 'META'}, 'ger': 'meta-taggen som ska renderas i <head> på kanonisk domän', 'skriver': False},
        {'steg': 'verifiera', 'metod': 'POST', 'url': SV + '/webResource?verificationMethod=META', 'nyttolast': {'site': {'type': 'SITE', 'identifier': s}}, 'ger': 'ägarskap för åtkomstens konto (irreversibelt tills ägaren tas bort)', 'skriver': True},
        {'steg': 'agare', 'metod': 'PUT', 'url': SV + '/webResource/{id}', 'nyttolast': {'site': {'type': 'SITE', 'identifier': s}, 'owners': ['<befintliga> + kundens och kontorets adresser ur VERKSAMHET.json sokkonsol_agare']}, 'ger': 'kunden som ägare av egenskapen', 'skriver': True},
        {'steg': 'egenskap', 'metod': 'PUT', 'url': WM + '/sites/' + urllib.parse.quote(s, safe=''), 'nyttolast': None, 'ger': 'egenskapen tillagd i sökkonsolen', 'skriver': True},
        {'steg': 'sitemap', 'metod': 'PUT', 'url': WM + '/sites/' + urllib.parse.quote(s, safe='') + '/sitemaps/' + urllib.parse.quote(s + 'sitemap.xml', safe=''), 'nyttolast': None, 'ger': 'sitemap inskickad', 'skriver': True},
        {'steg': 'inspektera', 'metod': 'POST', 'url': SC + '/urlInspection/index:inspect', 'nyttolast': [{'inspectionUrl': s.rstrip('/') + u, 'siteUrl': s} for u in (urler or ['/'])], 'ger': 'indexeringsstatus per adress (verdict, coverageState, lastCrawlTime)', 'skriver': False},
        {'steg': 'sokdata', 'metod': 'POST', 'url': WM + '/sites/' + urllib.parse.quote(s, safe='') + '/searchAnalytics/query', 'nyttolast': {'startDate': start, 'endDate': slut, 'dimensions': ['query', 'page'], 'rowLimit': 250}, 'ger': 'frågor och sidor med klick, visningar, ctr, position (ofullständig lista: Google döljer sällsynta frågor)', 'skriver': False},
    ]


def las_atkomst(path):
    p = Path(path)
    if not p.is_file():
        raise Vagrad('åtkomstfilen finns inte')
    if p.stat().st_mode & 0o077:
        raise Vagrad('åtkomstfilen ska ha rättighet 0600')
    d = json.loads(p.read_text(encoding='utf-8'))
    if d.get('typ') not in ('oauth', 'tjanstekonto'):
        raise Vagrad('åtkomstfilens typ ska vara oauth eller tjanstekonto')
    return d


def _b64(b):
    return base64.urlsafe_b64encode(b).rstrip(b'=').decode()


def access_token(atkomst, oppna):
    """Bearer-token. oauth: refresh-token-flödet. tjanstekonto: RS256-JWT signerad med openssl, bytt mot token."""
    if atkomst['typ'] == 'oauth':
        body = urllib.parse.urlencode({'client_id': atkomst['client_id'], 'client_secret': atkomst['client_secret'], 'refresh_token': atkomst['refresh_token'], 'grant_type': 'refresh_token'}).encode()
        status, svar = oppna('POST', TOKEN_URL, body, {'Content-Type': 'application/x-www-form-urlencoded'})
    else:
        now = int(time.time())
        header = _b64(json.dumps({'alg': 'RS256', 'typ': 'JWT'}).encode())
        claims = _b64(json.dumps({'iss': atkomst['client_email'], 'scope': SCOPES, 'aud': TOKEN_URL, 'iat': now, 'exp': now + 3600}).encode())
        signing = ('%s.%s' % (header, claims)).encode()
        with tempfile.TemporaryDirectory() as td:
            key = Path(td) / 'k.pem'; key.write_text(atkomst['private_key']); key.chmod(0o600)
            sig = subprocess.run(['openssl', 'dgst', '-sha256', '-sign', str(key)], input=signing, capture_output=True, check=True).stdout
        jwt = '%s.%s.%s' % (header, claims, _b64(sig))
        body = urllib.parse.urlencode({'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer', 'assertion': jwt}).encode()
        status, svar = oppna('POST', TOKEN_URL, body, {'Content-Type': 'application/x-www-form-urlencoded'})
    if status != 200 or 'access_token' not in svar:
        raise Vagrad('token-anropet misslyckades (status %s)' % status)
    return svar['access_token']


def http_oppna(metod, url, body=None, headers=None, timeout=30):
    req = urllib.request.Request(url, data=body, method=metod, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode('utf-8', 'replace')
            status = r.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', 'replace'); status = e.code
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return 0, {'utfall': 'okänt', 'feltyp': type(e).__name__}
    try:
        return status, json.loads(raw) if raw.strip() else {}
    except ValueError:
        return status, {'text': raw[:2000]}


def kontroll_fore_live(v, doman, kommando, oppna):
    vu.kraver_verklig(v, 'sökkonsol ' + kommando)
    if doman.endswith(FORHANDSVISNINGSSUFFIX):
        raise Vagrad('%s är en förhandsvisningsdomän; koppla kundens riktiga domän först' % doman)
    if kommando in ('verifiera', 'sitemap', 'inspektera', 'sokdata'):
        status, _ = oppna('GET', site_url(doman), None, {'User-Agent': 'nortropic-digitala sokkonsol'})
        if status != 200:
            raise Vagrad('https://%s/ svarar %s; kanonisk domän måste svara 200 före %s' % (doman, status, kommando))


def kor(kommando, v, doman, urler, atkomst, oppna, meta_token=None, agare=None, sov=time.sleep, rader=None, spara=lambda: None):
    """Utför ett kommando live; returnerar kvittorader (hemligheter aldrig med)."""
    plan = {p['steg']: p for p in anropsplan(doman, urler)}
    rader = rader if rader is not None else []
    tok = access_token(atkomst, oppna)
    auth = {'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json'}
    def call(steg, url=None, nyttolast=None):
        p = plan[steg]
        payload = nyttolast if nyttolast is not None else p['nyttolast']
        body = json.dumps(payload).encode() if payload is not None else None
        # Read-only POSTs and idempotent PUTs only. Verification POST has external side effects:
        # its uncertain outcome requires observation rather than blind repetition.
        retry_safe = steg in ('inspektera', 'sokdata', 'token', 'agare', 'egenskap', 'sitemap')
        for attempt in range(1, 4):
            status, svar = oppna(p['metod'], url or p['url'], body, auth)
            reasons = felorsaker(svar)
            transient = status in (429, 500, 502, 503, 504) or (status == 403 and bool(reasons & {'rateLimitExceeded', 'userRateLimitExceeded'}))
            retry = retry_safe and transient and attempt < 3
            row = {'steg': steg, 'metod': p['metod'], 'url': url or p['url'], 'status': status, 'svar': svar,
                   'forsok': attempt, 'slutligt': not retry, 'inspectionUrl': (payload or {}).get('inspectionUrl') if isinstance(payload, dict) else None,
                   'siteUrl': (payload or {}).get('siteUrl') if isinstance(payload, dict) else None,
                   'felorsaker': sorted(reasons), 'retry': retry}
            rader.append(row)
            spara()
            if not retry:
                return status, svar
            row['vantan_sekunder'] = 2 ** (attempt - 1)
            sov(row['vantan_sekunder'])
    if kommando == 'token':
        status, svar = call('token')
        if status == 200:
            rader[-1]['meta_tagg'] = svar.get('token')
            spara()
    elif kommando == 'verifiera':
        status, svar = call('verifiera')
        if not 200 <= status < 300:
            return rader
        if agare:
            rid = svar.get('id'); befintliga = svar.get('owners')
            if not rid or not isinstance(befintliga, list) or not isinstance(svar.get('site'), dict):
                rader[-1]['fel'] = 'verifieringssvaret saknar id/site/owners; ägarskap och efterföljande steg ej utförda'
                spara()
                return rader
            nya = [a for a in agare if a not in befintliga]
            if nya:
                status, _ = call('agare', SV + '/webResource/' + urllib.parse.quote(rid, safe=''), {'site': svar['site'], 'owners': befintliga + nya})
                if not 200 <= status < 300:
                    return rader
        status, _ = call('egenskap')
        if 200 <= status < 300:
            call('sitemap')
    elif kommando == 'sitemap':
        call('sitemap')
    elif kommando == 'inspektera':
        for nl in plan['inspektera']['nyttolast']:
            call('inspektera', nyttolast=nl)
    elif kommando == 'sokdata':
        call('sokdata')
    return rader


def felorsaker(svar):
    error = svar.get('error') if isinstance(svar, dict) else None
    if not isinstance(error, dict):
        return set()
    return {str(r['reason']) for r in error.get('errors', []) if isinstance(r, dict) and r.get('reason')}


def tolkning(rader):
    """Observationer att omsätta i åtgärder (kunskap/sokkonsol.md), inte betyg."""
    ut = []
    for r in rader:
        if not r.get('slutligt', True):
            continue
        s = r.get('svar') or {}
        context = {'adress': r.get('inspectionUrl'), 'egenskap': r.get('siteUrl'), 'http_status': r.get('status')}
        if not 200 <= r.get('status', 0) < 300 or r.get('fel'):
            code = r.get('status'); reasons = felorsaker(s)
            action = ('utfallet är okänt; stäm av leverantörens faktiska tillstånd och detta kvitto före nytt försök'
                      if code == 0 else 'kontrollera autentisering, behörighet och aktiverat API; ingen indexeringsbedömning kan göras'
                      if code in (401, 403) and not reasons & {'rateLimitExceeded', 'userRateLimitExceeded'}
                      else 'kontrollera kvot eller övergående leverantörsfel; begränsade försök är slut, planera senare omprov'
                      if code in (429, 500, 502, 503, 504) or reasons & {'rateLimitExceeded', 'userRateLimitExceeded'}
                      else 'kontrollera anropets data och råsvaret; ingen indexeringsbedömning kan göras')
            ut.append({**context, 'status': 'utfall okänt' if code == 0 else 'API-fel', 'steg': r['steg'], 'felorsaker': sorted(reasons), 'atgard': r.get('fel') or action})
            continue
        if r['steg'] == 'inspektera' and isinstance(s, dict):
            res = (s.get('inspectionResult') or {}).get('indexStatusResult') or {}
            ut.append({**context, 'status': 'observerat indexeringssvar' if res else 'ofullständigt API-svar', 'verdict': res.get('verdict'), 'coverage': res.get('coverageState'), 'senast_crawlad': res.get('lastCrawlTime'),
                       'atgard': 'indexStatusResult saknas; gör ingen innehållsdiagnos' if not res else 'ingen' if res.get('verdict') == 'PASS' else 'läs coverageState: "upptäckt, inte indexerad" > 2 veckor på viktiga sidor → begär indexering igen och stärk intern länkning; "genomsökt, inte indexerad" → tunt innehåll, fördjupa'})
        if r['steg'] == 'sokdata' and isinstance(s, dict) and s.get('rows'):
            kand = [x for x in s['rows'] if 5 <= (x.get('position') or 0) <= 20]
            ut.append({'rader': len(s['rows']), 'sidforbattringskandidater_position_5_20': len(kand), 'atgard': 'frågor i position 5–20 med visningar: lägg frasens lydelse i sida eller FAQ; visningar utan klick: skriv om description; återkommande nya frågor: ny sida bara med genuint innehåll'})
    return ut


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True).encode('utf-8')


class Journal:
    """Engångskvitto. Avsikt före transport, svar före nästa steg; inga credentials lagras."""
    def __init__(self, path, kvitto, transport, atkomst):
        self.path = Path(path)
        self.q = kvitto
        self.transport = transport
        self.hemliga = [x for x in atkomst.values() if isinstance(x, str) and len(x) >= 8]
        try:
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as e:
            raise Vagrad('kvittofilen finns redan; ingen upprepning. Läs kvittot och stäm av verkligt tillstånd före ett uttryckligt nytt försök med ny kvittofil') from e
        os.close(fd)
        self.spara()

    def sanera(self, data):
        if isinstance(data, dict):
            return {k: '[maskerat]' if k in ('access_token', 'refresh_token', 'client_secret', 'private_key', 'assertion') else self.sanera(v) for k, v in data.items()}
        if isinstance(data, list):
            return [self.sanera(x) for x in data]
        if isinstance(data, str):
            for value in sorted(self.hemliga, key=len, reverse=True):
                data = data.replace(value, '[maskerat]')
        return data

    def spara(self):
        # Keep a valid last journal even if interrupted during serialization/write.
        tmp = self.path.with_name(self.path.name + '.tmp-' + str(os.getpid()))
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            out.write(json.dumps(self.sanera(self.q), ensure_ascii=False, indent=1) + '\n')
            out.flush(); os.fsync(out.fileno())
        os.replace(tmp, self.path)
        fd = os.open(self.path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def __call__(self, metod, url, body=None, headers=None, timeout=30):
        # Hash includes actual dynamic owners/resource-id payload, not only the template plan.
        request = {'metod': metod, 'url': url, 'kropp_sha256': sha(body or b'')}
        row = {**request, 'begaran_sha256': sha(json_bytes(request)), 'nummer': len(self.q['transport']) + 1,
               'tid': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
               'status': None, 'utfall': 'okänt; avsikt sparad före anrop'}
        self.q['transport'].append(row)
        self.q['lage'] = 'pågår; senaste anropets utfall okänt'
        self.spara()
        try:
            status, svar = self.transport(metod, url, body, headers, timeout)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            status, svar = 0, {'utfall': 'okänt', 'feltyp': type(e).__name__}
        if url == TOKEN_URL and isinstance(svar, dict) and isinstance(svar.get('access_token'), str):
            self.hemliga.append(svar['access_token'])
        row.update(status=status, utfall='svar mottaget' if status else 'okänt',
                   svar_sha256=sha(json_bytes(svar)), svar=self.sanera(svar))
        self.spara()
        return status, svar


def main(argv=None, *, transport=None):
    p = argparse.ArgumentParser(prog='sokkonsol', description=__doc__.split('\n\n')[0])
    p.add_argument('kommando', choices=('plan', 'token', 'verifiera', 'sitemap', 'inspektera', 'sokdata'))
    p.add_argument('--verksamhet', required=True)
    p.add_argument('--doman')
    p.add_argument('--urler', default='/')
    p.add_argument('--atkomst')
    p.add_argument('--live', action='store_true')
    p.add_argument('--ut', required=True)
    a = p.parse_args(argv)
    journal = None
    try:
        v = vu.las(a.verksamhet)
        doman = a.doman or (v.get('webb') or {}).get('doman')
        if not doman:
            raise Vagrad('ingen domän: --doman eller webb.doman i VERKSAMHET.json')
        urler = [u.strip() for u in a.urler.split(',') if u.strip()]
        plan = anropsplan(doman, urler)
        atk = {}
        if a.kommando != 'plan':
            if not a.live:
                raise Vagrad('%s kräver --live och --atkomst; utan åtkomst: kör plan' % a.kommando)
            if not a.atkomst:
                raise Vagrad('--atkomst saknas (privat fil 0600); extern aktivering: OAuth-klient eller tjänstekonto med scopes webmasters och siteverification')
            atk = las_atkomst(a.atkomst)
        kvitto = {'schema': 2, 'verksamhet': v['namn'], 'fiktiv': v['fiktiv'], 'doman': doman, 'kommando': a.kommando,
                  'tid': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'live': bool(a.live),
                  'provniva': 'plan' if a.kommando == 'plan' else 'testtransport' if transport else 'externa API-anrop',
                  'bindning': {'verksamhet_sha256': sha(Path(a.verksamhet).read_bytes()),
                               'atkomst_sha256': sha(Path(a.atkomst).read_bytes()) if atk else None,
                               'kod': {p.name: sha(p.read_bytes()) for p in (Path(__file__), Path(vu.__file__))},
                               'plan_sha256': sha(json_bytes(plan)), 'kommando': a.kommando, 'doman': doman},
                  'plan': plan, 'dokumentation': DOK, 'anrop': [], 'transport': [], 'tolkning': [], 'lage': 'förberedd',
                  'not': 'En plan är inte en verifierad integration. API-svar avser endast dessa anrop, inte indexering eller drift. Testtransport är inte extern framgång. Okänt utfall kräver avstämning före nytt försök; ett nytt filnamn gör ingen avstämning.'}
        journal = Journal(a.ut, kvitto, transport or http_oppna, atk)
        if a.kommando != 'plan':
            kontroll_fore_live(v, doman, a.kommando, journal)
            kor(a.kommando, v, doman, urler, atk, journal, agare=v.get('sokkonsol_agare'), rader=kvitto['anrop'], spara=journal.spara)
            kvitto['tolkning'] = tolkning(kvitto['anrop'])
        unknown = any(not r.get('status') for r in kvitto['transport'])
        failed = any((not 200 <= r['status'] < 300 or r.get('fel')) for r in kvitto['anrop'] if r.get('slutligt', True))
        kvitto['lage'] = 'utfall okänt; avstämning krävs' if unknown else 'API-fel' if failed else 'plan' if a.kommando == 'plan' else 'API-anrop besvarade'
        journal.spara()
        code = 2 if unknown else 1 if failed else 0
    except (Vagrad, vu.Vagrad, OSError) as e:
        if journal:
            # Never turn an exception into success or erase already journalled observations.
            journal.q['lage'] = 'avbruten; läs transportens utfall'
            journal.q['feltyp'] = type(e).__name__
            journal.spara()
        msg = e.args[0] if isinstance(e, (Vagrad, vu.Vagrad)) else type(e).__name__
        print(json.dumps({'vagrad': msg}, ensure_ascii=False))
        return 2
    print(json.dumps({'kommando': a.kommando, 'live': bool(a.live), 'anrop': len(kvitto['anrop']), 'lage': kvitto['lage'], 'ut': a.ut}, ensure_ascii=False))
    return code


if __name__ == '__main__':
    sys.exit(main())
