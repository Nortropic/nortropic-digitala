#!/usr/bin/env python3
"""Lansering: procedur, förkontroll och kontroll på lanseringsdagen, återgång och det som är oåterkalleligt.
Lansering sker bara enligt gällande mandat (MANDAT.md: en beställning som namnger lansering); verktyget skriver
inget hos någon leverantör — det läser (HTTP GET/HEAD mot kundens publika domän) och skriver checklista och kontroll.
Sökkonsolens skrivande steg görs med verktyg/sokkonsol.py, driftsättning och domänkoppling med värdplattformens CLI.

    python3 -B verktyg/lansering.py plan --verksamhet VERKSAMHET.json [--mandat POST-ID] --ut LANSERING.md
    python3 -B verktyg/lansering.py kontrollera --adress https://domän.se [--verifieringstoken TOKEN] [--tillat-http] --ut KONTROLL.json
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlencode, urljoin, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verksamhetsuppgifter as vu  # noqa: E402
import drift_kontroll as dk  # noqa: E402

DNS_RESOLVER = 'https://cloudflare-dns.com/dns-query'
DNS_TYPER = {'A': 1, 'NS': 2, 'CNAME': 5, 'MX': 15, 'TXT': 16, 'AAAA': 28, 'CAA': 257}


def privat_json(path, value):
    """New receipt only; private bytes before the first write, never follow a link."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as out:
        out.write(json.dumps(value, ensure_ascii=False, indent=2)+'\n')


def dns_namn(value, service=False):
    name = str(value).strip().rstrip('.').encode('idna').decode('ascii').lower()
    pattern = r'[a-z0-9_](?:[a-z0-9_-]{0,61}[a-z0-9_])?' if service else r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?'
    if len(name) > 253 or '.' not in name or not all(re.fullmatch(pattern, label) for label in name.split('.')):
        raise ValueError('ogiltigt DNS-namn')
    return name


def _doh_json(name, typ):
    # Reuse the bounded stdlib GET transport; fixed resolver, no redirects or credentials.
    r = dk.hamta(DNS_RESOLVER+'?'+urlencode({'name': name, 'type': typ}), timeout=10, accept='application/dns-json')
    if r['status'] != 200 or r.get('fel') or r.get('for_stor'):
        raise ValueError('DNS-svaret kunde inte läsas')
    return json.loads(r['body'])


def dns_las(namn, typ, hamta_json=_doh_json):
    name = dns_namn(namn, service=True)
    if typ not in DNS_TYPER: raise ValueError('okänd DNS-typ')
    result = {'namn': name, 'typ': typ, 'resolver': DNS_RESOLVER, 'lage': 'okant', 'poster': [], 'skal': None}
    try:
        raw = hamta_json(name, typ)
        code = raw.get('Status')
        if type(code) is not int or code not in (0, 3) or raw.get('TC', False) is not False:
            raise ValueError('DNS-felkod eller trunkerat svar')
        question = raw.get('Question')
        if (not isinstance(question, list) or len(question) != 1 or
                dns_namn(question[0]['name'], service=True) != name or type(question[0]['type']) is not int or question[0]['type'] != DNS_TYPER[typ]):
            raise ValueError('DNS-svaret gäller annan fråga')
        answers = raw.get('Answer', [])
        if not isinstance(answers, list) or (code == 3 and answers): raise ValueError('tvetydigt DNS-svar')
        reachable = {name}
        aliases = {}
        for row in answers:
            if not isinstance(row, dict) or type(row.get('type')) is not int: raise ValueError('ogiltig DNS-post')
            if row['type'] == DNS_TYPER['CNAME']:
                owner, target = dns_namn(row['name'], service=True), dns_namn(row['data'], service=True)
                if owner in aliases and aliases[owner] != target: raise ValueError('tvetydigt CNAME')
                aliases[owner] = target
        current = name
        while current in aliases:
            current = aliases[current]
            if current in reachable: raise ValueError('cykliskt CNAME')
            reachable.add(current)
        for row in answers:
            if not isinstance(row, dict) or type(row.get('type')) is not int: raise ValueError('ogiltig DNS-post')
            if row['type'] != DNS_TYPER[typ]: continue
            if type(row.get('TTL')) is not int or row['TTL'] < 0 or not isinstance(row.get('data'), str):
                raise ValueError('ogiltig DNS-post')
            owner = dns_namn(row['name'], service=True)
            if owner not in reachable: raise ValueError('DNS-posten saknar samband med frågan')
            result['poster'].append({'namn': owner, 'data': row['data'], 'ttl': row['TTL']})
        result.update(lage='ok', rcode=code)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, UnicodeError):
        result.update(poster=[], skal='kunde inte kontrolleras')
    return result


def _txt(data):
    # TXT RDATA may contain multiple quoted character-strings; concatenate them.
    if not data.startswith('"'): return data.strip()
    pieces = re.findall(r'"((?:[^"\\]|\\.)*)"', data)
    if not pieces or re.sub(r'"(?:[^"\\]|\\.)*"', '', data).strip(): return ''
    return ''.join(re.sub(r'\\(.)', r'\1', piece) for piece in pieces).strip()


def epostkontroll(verksamhet, doman, selektor, resolver=dns_las):
    result = {'schema': 1, 'doman': doman, 'selektor': selektor, 'resolver': DNS_RESOLVER,
              'lage': 'okant', 'klar': False, 'fynd': [], 'anmarkningar': [], 'okanda': [], 'uppslag': {}}
    if verksamhet.get('fiktiv') is not False:
        result['okanda'].append('fiktiv eller okänd verksamhet: ingen verklig DNS-kontroll'); return result
    doman = dns_namn(doman); result['doman'] = doman
    if not isinstance(selektor, str) or not selektor or not all(re.fullmatch(r'[a-zA-Z0-9_-]{1,63}', p) for p in selektor.split('.')):
        raise ValueError('DKIM-selektor från leverantören krävs')
    for key, name in [('spf', doman), ('dkim', selektor+'._domainkey.'+doman), ('dmarc', '_dmarc.'+doman)]:
        try:
            r = resolver(name, 'TXT')
            if not isinstance(r, dict) or r.get('lage') not in ('ok', 'okant') or not isinstance(r.get('poster'), list):
                raise ValueError('oläsbart resolversvar')
            if any(not isinstance(p, dict) or not isinstance(p.get('data'), str) for p in r['poster']):
                raise ValueError('oläsbar DNS-post')
        except (OSError, ValueError, TypeError):
            r = {'namn': name, 'typ': 'TXT', 'lage': 'okant', 'poster': [], 'skal': 'kunde inte kontrolleras'}
        result['uppslag'][key] = r
        if r['lage'] != 'ok': result['okanda'].append(key.upper()+': kunde inte kontrolleras')
    values = {k: [_txt(p['data']) for p in v['poster']] for k, v in result['uppslag'].items()}
    spf = [x for x in values['spf'] if re.match(r'^v=spf1(?:\s|$)', x, re.I)]
    dkim = [x for x in values['dkim'] if re.search(r'(?:^|;)\s*p\s*=\s*[^;\s]+', x, re.I)]
    dmarc = [x for x in values['dmarc'] if re.match(r'^v=DMARC1\s*;', x, re.I)]
    if not spf and not dkim and all(result['uppslag'][k]['lage'] == 'ok' for k in ('spf', 'dkim')):
        result['fynd'].append('varken SPF eller DKIM hittades')
    if len(spf) > 1: result['fynd'].append('flera SPF-poster: behöver rättas')
    if not dmarc and result['uppslag']['dmarc']['lage'] == 'ok': result['anmarkningar'].append('DMARC saknas')
    result['klar'] = not result['fynd'] and not result['okanda']
    result['lage'] = 'fynd' if result['fynd'] else 'okant' if result['okanda'] else 'ok'
    result['not'] = 'Kontrollerar publicerade DNS-poster, inte faktisk signering, alignment eller leverans. Gmail rekommenderar alla tre; över 5000 meddelanden per dygn krävs SPF, DKIM och DMARC.'
    return result


def plan_md(v, mandat):
    dom = (v.get('webb') or {}).get('doman') or '<domän>'
    lines = ['# Lansering — %s (%s)' % (v['namn'], dom), '', '**Mandat:** %s' % (mandat or 'INGET ANGIVET — lansering får inte utföras utan beställning som namnger lansering (MANDAT.md §2)'),
             '**Fiktiv verksamhet:** %s' % ('ja — ingen verklig lansering, ingen sökkonsol, ingen profil' if v['fiktiv'] else 'nej'), '',
             '## Före lanseringsdagen', '',
             '1. Lanseringskonfiguration skild från förhandsvisning: canonical, sitemap och robots på %s; `noindex` bort BARA i lanseringskonfigurationen.' % dom,
             '2. Kanonisk variant vald (www eller apex); den andra omdirigerar 301 till den valda; båda får inte svara 200.',
             '3. Kontrollera avsändningsdomänens SPF, leverantörens DKIM-selektor och DMARC med lansering.py epostkontroll; spara kvittot privat. Fiktiv verksamhet gör ingen verklig DNS-läsning.',
             '4. Arkivera den gamla sajtens sitemapadresser och intervjuns migrering_adresser med webblasare/arkivera.mjs i kundmappen FÖRE DNS-omläggning. Läs manifestet och varje misslyckad adress.',
             '5. Omdirigeringar från gammal sajt (adresser med trafik eller länkar) i konfigurationen och prövade i förhandsvisning (seo_kontroll --omdirigeringar).',
             '6. Sökkonsolens META-token hämtad (sokkonsol.py token) och renderad i <head>; taggen ligger kvar för alltid.',
             '7. Prelaunch-rapport (prelaunch.py) med grind 0–5 och 7 PASS och juridiken avgjord av människa.',
             '8. Domänen kopplad hos värden (DNS hos kundens registrar, certifikat utfärdat); återgångsväg känd (föregående driftsättning kan pekas tillbaka med värdplattformens CLI).', '',
             '## Lanseringsdagen', '',
             '1. Driftsätt lanseringskonfigurationen till produktionsdomänen; kontrollera att https://%s/ svarar 200 med rätt innehåll.' % dom,
             '2. Kontrollera att noindex är borta (meta robots och X-Robots-Tag) på startsidan och de viktigaste sidorna: lansering.py kontrollera.',
             '3. Sökkonsol: verifiera egenskapen, lägg till kunden som ägare, skicka in sitemap (sokkonsol.py verifiera --live); inspektera startsidan och de viktigaste sidorna (sokkonsol.py inspektera).',
             '4. Bing Webmaster Tools: importera egenskapen från sökkonsolen (människa); IndexNow-nyckelfil om värden stöder det (valfritt).',
             '5. Mätverktyget: kontrollera att konverteringshändelserna syns i felsökningsläget på produktionsdomänen (uppfoljning.md).', '',
             '## Oåterkalleligt', '', '- Sökmotorernas första indexering av fel innehåll (därför noindex-kontrollen före sökkonsolen).', '- Ägarskap i sökkonsolen (tas bort manuellt vid avslut).', '- Omdirigeringar som ändrat inkommande länkars mål.', '',
             '## Återgång', '', '- Peka produktionsdomänen till föregående driftsättning (värdplattformens CLI), återställ noindex om innehållet inte får indexeras, skriv en not i ARBETSLOGG.md med tid och orsak.', '',
             '## Veckorna efter', '', '- Dag 2–3 och därefter varannan dag i två veckor: sökkonsolens indexeringsrapport (uppfoljning.md, sokkonsol.md); månadsvis: frågor i position 5–20, visningar utan klick, Core Web Vitals-rapporten.']
    return '\n'.join(lines) + '\n'


def hamta(url, metod='GET', timeout=20):
    req = urllib.request.Request(url, method=metod, headers={'User-Agent': 'nortropic-digitala lansering'})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(400000).decode('utf-8', 'replace') if metod == 'GET' else ''
            return {'status': r.status, 'url': r.geturl(), 'headers': {k.lower(): v for k, v in r.headers.items()}, 'body': body, 'ms': int((time.time() - t0) * 1000)}
    except urllib.error.HTTPError as e:
        return {'status': e.code, 'url': url, 'headers': {k.lower(): v for k, v in e.headers.items()}, 'body': '', 'ms': int((time.time() - t0) * 1000)}
    except Exception as e:  # noqa: BLE001
        return {'status': None, 'url': url, 'headers': {}, 'body': '', 'fel': e.__class__.__name__, 'ms': int((time.time() - t0) * 1000)}


def prova_omdirigeringar(adress, data, tillat_http=False, las=dk.hamta):
    if not isinstance(data, dict) or not isinstance(data.get('gamla'), list):
        raise ValueError('REDIRECTS.json kräver listan gamla')
    rows = []
    for row in data['gamla']:
        if not isinstance(row, dict) or not all(isinstance(row.get(k), str) and row[k].strip() for k in ('fran', 'till')):
            raise ValueError('omdirigering kräver fran och till')
        source, target = (urljoin(adress, row[k]) for k in ('fran', 'till'))
        for url in (source, target):
            dk.ursprung(url)
            if urlsplit(url).scheme != 'https' and not tillat_http:
                raise ValueError('omdirigeringens adresser ska vara https')
        r = las(source, max_hopp=5, omforsok=0)
        findings = []
        if r.get('forsta_status') not in (301, 308):
            findings.append('första svaret är inte 301/308')
        if r['status'] != 200 or r.get('fel'):
            findings.append('målet svarar inte 200: %s' % (r.get('fel') or r['status']))
        observed = r.get('slutadress_observerad', r.get('status') is not None)
        if observed and r.get('url') != target:
            findings.append('landar inte på exakt målet')
        rows.append({'fran': source, 'till': target, 'status': r.get('forsta_status'),
                     'slutstatus': r['status'] if observed else None,
                     'slutadress': r.get('url') if observed else None,
                     'hopp': r.get('hopp', []), 'fynd': findings, 'ok': not findings})
    return rows


def kontrollera(adress, token=None, tillat_http=False, hamta=hamta, omdirigeringar=None):
    u = urlsplit(adress)
    if u.scheme != 'https' and not tillat_http:
        raise ValueError('adressen ska vara https (--tillat-http bara för lokala prov)')
    bas = '%s://%s' % (u.scheme, u.netloc)
    fynd = []
    start = hamta(bas + '/')
    if start['status'] != 200:
        fynd.append('startsidan svarar %s' % (start['status'] or start.get('fel')))
    if urlsplit(start['url']).netloc not in (u.netloc,):
        fynd.append('startsidan omdirigerar till annan värd: %s' % start['url'])
    robots_meta = re.search(r'<meta\s+name=["\']robots["\']\s+content=["\']([^"\']*)["\']', start['body'], re.I)
    noindex = bool(robots_meta and 'noindex' in robots_meta.group(1).lower()) or 'noindex' in start['headers'].get('x-robots-tag', '').lower()
    if noindex:
        fynd.append('noindex kvar på startsidan (meta eller X-Robots-Tag)')
    verif = re.search(r'<meta\s+name=["\']google-site-verification["\']\s+content=["\']([^"\']*)["\']', start['body'], re.I)
    if token and (not verif or verif.group(1) != token):
        fynd.append('verifieringstaggen syns inte med rätt token i produktions-HTML')
    sm = hamta(bas + '/sitemap.xml')
    if sm['status'] != 200 or '<loc>' not in sm['body']:
        fynd.append('sitemap.xml svarar %s eller saknar loc' % (sm['status'] or sm.get('fel')))
    rb = hamta(bas + '/robots.txt')
    if rb['status'] != 200:
        fynd.append('robots.txt svarar %s' % (rb['status'] or rb.get('fel')))
    elif re.search(r'(?im)^Disallow:\s*/\s*$', rb['body']):
        fynd.append('robots.txt blockerar allt')
    host = u.netloc
    annan = host[4:] if host.startswith('www.') else 'www.' + host
    alt = hamta('%s://%s/' % (u.scheme, annan), 'HEAD') if u.scheme == 'https' else {'status': None, 'url': None}
    kanonisk = {'vald': host, 'andra_varianten': annan, 'andra_svarar': alt['status'], 'andra_landar_pa': alt.get('url')}
    if alt['status'] == 200 and alt.get('url') and urlsplit(alt['url']).netloc == annan:
        fynd.append('båda varianterna svarar 200: %s ska omdirigera 301 till %s' % (annan, host))
    redirects = prova_omdirigeringar(adress, omdirigeringar, tillat_http) if omdirigeringar is not None else []
    for row in redirects:
        fynd.extend(row['fran'] + ': ' + f for f in row['fynd'])
    return {'schema': 1, 'adress': adress, 'tid': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'startsida': {'status': start['status'], 'ms': start['ms'], 'noindex': noindex, 'verifieringstagg': bool(verif)},
            'sitemap': sm['status'], 'robots': rb['status'], 'kanonisk': kanonisk, 'fynd': fynd, 'klar_for_sokkonsol': not fynd,
            'omdirigeringar': redirects,
            'not': 'läsande kontroll; sökkonsolens skrivande steg körs med sokkonsol.py --live efter att fynden är noll'}


def main(argv=None):
    p = argparse.ArgumentParser(prog='lansering', description=__doc__.split('\n\n')[0])
    p.add_argument('kommando', choices=('plan', 'kontrollera', 'epostkontroll'))
    p.add_argument('--verksamhet'); p.add_argument('--mandat'); p.add_argument('--adress'); p.add_argument('--verifieringstoken'); p.add_argument('--tillat-http', action='store_true'); p.add_argument('--ut', required=True); p.add_argument('--omdirigeringar')
    p.add_argument('--avsandardoman'); p.add_argument('--dkim-selektor')
    a = p.parse_args(argv)
    try:
        if a.kommando == 'plan':
            if not a.verksamhet:
                raise ValueError('plan kräver --verksamhet')
            v = vu.las(a.verksamhet)
            Path(a.ut).write_text(plan_md(v, a.mandat), encoding='utf-8'); print(json.dumps({'ut': a.ut, 'mandat': bool(a.mandat), 'fiktiv': v['fiktiv']}))
        elif a.kommando == 'epostkontroll':
            if not all((a.verksamhet, a.avsandardoman, a.dkim_selektor, a.mandat)):
                raise ValueError('epostkontroll kraver --verksamhet, --avsandardoman, --dkim-selektor och --mandat')
            result = epostkontroll(vu.las(a.verksamhet), a.avsandardoman, a.dkim_selektor)
            result['mandat'] = a.mandat
            privat_json(a.ut, result)
            print(json.dumps({'lage': result['lage'], 'ut': a.ut}))
            return 2 if result['okanda'] else 1 if result['fynd'] else 0
        else:
            if not a.adress:
                raise ValueError('kontrollera kräver --adress')
            redirects = json.loads(Path(a.omdirigeringar).read_text(encoding='utf-8')) if a.omdirigeringar else None
            k = kontrollera(a.adress, a.verifieringstoken, a.tillat_http, omdirigeringar=redirects)
            Path(a.ut).write_text(json.dumps(k, ensure_ascii=False, indent=1) + '\n', encoding='utf-8'); print(json.dumps({'fynd': len(k['fynd']), 'klar_for_sokkonsol': k['klar_for_sokkonsol'], 'ut': a.ut}, ensure_ascii=False))
    except (ValueError, OSError, vu.Vagrad) as e:
        print(json.dumps({'vagrad': e.args[0]}, ensure_ascii=False)); return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
