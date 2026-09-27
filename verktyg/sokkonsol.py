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


def kor(kommando, v, doman, urler, atkomst, oppna, meta_token=None, agare=None):
    """Utför ett kommando live; returnerar kvittorader (hemligheter aldrig med)."""
    plan = {p['steg']: p for p in anropsplan(doman, urler)}
    rader = []
    tok = access_token(atkomst, oppna)
    auth = {'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json'}
    def call(steg, url=None, nyttolast=None):
        p = plan[steg]
        body = json.dumps(nyttolast if nyttolast is not None else p['nyttolast']).encode() if (nyttolast is not None or p['nyttolast'] is not None) else None
        status, svar = oppna(p['metod'], url or p['url'], body, auth)
        rader.append({'steg': steg, 'metod': p['metod'], 'url': url or p['url'], 'status': status, 'svar': svar})
        return status, svar
    if kommando == 'token':
        status, svar = call('token')
        if status == 200:
            rader[-1]['meta_tagg'] = svar.get('token')
    elif kommando == 'verifiera':
        status, svar = call('verifiera')
        if status == 200 and agare:
            rid = svar.get('id'); befintliga = svar.get('owners') or []
            nya = [a for a in agare if a not in befintliga]
            if nya:
                call('agare', SV + '/webResource/' + urllib.parse.quote(rid, safe=''), {'site': svar.get('site'), 'owners': befintliga + nya})
        if status == 200:
            call('egenskap'); call('sitemap')
    elif kommando == 'sitemap':
        call('sitemap')
    elif kommando == 'inspektera':
        for nl in plan['inspektera']['nyttolast']:
            call('inspektera', nyttolast=nl)
    elif kommando == 'sokdata':
        call('sokdata')
    return rader


def tolkning(rader):
    """Observationer att omsätta i åtgärder (kunskap/sokkonsol.md), inte betyg."""
    ut = []
    for r in rader:
        s = r.get('svar') or {}
        if r['steg'] == 'inspektera' and isinstance(s, dict):
            res = (s.get('inspectionResult') or {}).get('indexStatusResult') or {}
            ut.append({'adress': '', 'verdict': res.get('verdict'), 'coverage': res.get('coverageState'), 'senast_crawlad': res.get('lastCrawlTime'),
                       'atgard': 'ingen' if res.get('verdict') == 'PASS' else 'läs coverageState: "upptäckt, inte indexerad" > 2 veckor på viktiga sidor → begär indexering igen och stärk intern länkning; "genomsökt, inte indexerad" → tunt innehåll, fördjupa'})
        if r['steg'] == 'sokdata' and isinstance(s, dict) and s.get('rows'):
            kand = [x for x in s['rows'] if 5 <= (x.get('position') or 0) <= 20]
            ut.append({'rader': len(s['rows']), 'sidforbattringskandidater_position_5_20': len(kand), 'atgard': 'frågor i position 5–20 med visningar: lägg frasens lydelse i sida eller FAQ; visningar utan klick: skriv om description; återkommande nya frågor: ny sida bara med genuint innehåll'})
    return ut


def main(argv=None):
    p = argparse.ArgumentParser(prog='sokkonsol', description=__doc__.split('\n\n')[0])
    p.add_argument('kommando', choices=('plan', 'token', 'verifiera', 'sitemap', 'inspektera', 'sokdata'))
    p.add_argument('--verksamhet', required=True)
    p.add_argument('--doman')
    p.add_argument('--urler', default='/')
    p.add_argument('--atkomst')
    p.add_argument('--live', action='store_true')
    p.add_argument('--ut', required=True)
    a = p.parse_args(argv)
    try:
        v = vu.las(a.verksamhet)
        doman = a.doman or (v.get('webb') or {}).get('doman')
        if not doman:
            raise Vagrad('ingen domän: --doman eller webb.doman i VERKSAMHET.json')
        urler = [u.strip() for u in a.urler.split(',') if u.strip()]
        kvitto = {'schema': 1, 'verksamhet': v['namn'], 'fiktiv': v['fiktiv'], 'doman': doman, 'kommando': a.kommando, 'tid': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                  'live': bool(a.live), 'plan': anropsplan(doman, urler), 'dokumentation': DOK, 'anrop': [], 'tolkning': [],
                  'not': 'plan = vad som skulle göras; live = vad som gjordes med statuskoder. En plan är inte en verifierad integration.'}
        if a.kommando != 'plan':
            if not a.live:
                raise Vagrad('%s kräver --live och --atkomst; utan åtkomst: kör plan' % a.kommando)
            if not a.atkomst:
                raise Vagrad('--atkomst saknas (privat fil 0600); extern aktivering: OAuth-klient eller tjänstekonto med scopes webmasters och siteverification')
            atk = las_atkomst(a.atkomst)
            kontroll_fore_live(v, doman, a.kommando, http_oppna)
            kvitto['anrop'] = kor(a.kommando, v, doman, urler, atk, http_oppna, agare=v.get('sokkonsol_agare'))
            kvitto['tolkning'] = tolkning(kvitto['anrop'])
    except (Vagrad, vu.Vagrad) as e:
        print(json.dumps({'vagrad': e.args[0]}, ensure_ascii=False))
        return 2
    text = json.dumps(kvitto, ensure_ascii=False, indent=1)
    if a.atkomst:
        for hemligt in (json.loads(Path(a.atkomst).read_text()).values() if Path(a.atkomst).is_file() else []):
            if isinstance(hemligt, str) and len(hemligt) >= 8:
                assert hemligt not in text, 'hemlighet i kvitto'
    Path(a.ut).write_text(text + '\n', encoding='utf-8')
    print(json.dumps({'kommando': a.kommando, 'live': bool(a.live), 'anrop': len(kvitto['anrop']), 'ut': a.ut}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
