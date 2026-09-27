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
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verksamhetsuppgifter as vu  # noqa: E402


def plan_md(v, mandat):
    dom = (v.get('webb') or {}).get('doman') or '<domän>'
    lines = ['# Lansering — %s (%s)' % (v['namn'], dom), '', '**Mandat:** %s' % (mandat or 'INGET ANGIVET — lansering får inte utföras utan beställning som namnger lansering (MANDAT.md §2)'),
             '**Fiktiv verksamhet:** %s' % ('ja — ingen verklig lansering, ingen sökkonsol, ingen profil' if v['fiktiv'] else 'nej'), '',
             '## Före lanseringsdagen', '',
             '1. Lanseringskonfiguration skild från förhandsvisning: canonical, sitemap och robots på %s; `noindex` bort BARA i lanseringskonfigurationen.' % dom,
             '2. Kanonisk variant vald (www eller apex); den andra omdirigerar 301 till den valda; båda får inte svara 200.',
             '3. Omdirigeringar från gammal sajt (adresser med trafik eller länkar) i konfigurationen och prövade i förhandsvisning (seo_kontroll --omdirigeringar).',
             '4. Sökkonsolens META-token hämtad (sokkonsol.py token) och renderad i <head>; taggen ligger kvar för alltid.',
             '5. Prelaunch-rapport (prelaunch.py) med grind 0–5 och 7 PASS och juridiken avgjord av människa.',
             '6. Domänen kopplad hos värden (DNS hos kundens registrar, certifikat utfärdat); återgångsväg känd (föregående driftsättning kan pekas tillbaka med värdplattformens CLI).', '',
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


def kontrollera(adress, token=None, tillat_http=False, hamta=hamta):
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
    return {'schema': 1, 'adress': adress, 'tid': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'startsida': {'status': start['status'], 'ms': start['ms'], 'noindex': noindex, 'verifieringstagg': bool(verif)},
            'sitemap': sm['status'], 'robots': rb['status'], 'kanonisk': kanonisk, 'fynd': fynd, 'klar_for_sokkonsol': not fynd,
            'not': 'läsande kontroll; sökkonsolens skrivande steg körs med sokkonsol.py --live efter att fynden är noll'}


def main(argv=None):
    p = argparse.ArgumentParser(prog='lansering', description=__doc__.split('\n\n')[0])
    p.add_argument('kommando', choices=('plan', 'kontrollera'))
    p.add_argument('--verksamhet'); p.add_argument('--mandat'); p.add_argument('--adress'); p.add_argument('--verifieringstoken'); p.add_argument('--tillat-http', action='store_true'); p.add_argument('--ut', required=True)
    a = p.parse_args(argv)
    try:
        if a.kommando == 'plan':
            if not a.verksamhet:
                raise ValueError('plan kräver --verksamhet')
            v = vu.las(a.verksamhet)
            Path(a.ut).write_text(plan_md(v, a.mandat), encoding='utf-8'); print(json.dumps({'ut': a.ut, 'mandat': bool(a.mandat), 'fiktiv': v['fiktiv']}))
        else:
            if not a.adress:
                raise ValueError('kontrollera kräver --adress')
            k = kontrollera(a.adress, a.verifieringstoken, a.tillat_http)
            Path(a.ut).write_text(json.dumps(k, ensure_ascii=False, indent=1) + '\n', encoding='utf-8'); print(json.dumps({'fynd': len(k['fynd']), 'klar_for_sokkonsol': k['klar_for_sokkonsol'], 'ut': a.ut}, ensure_ascii=False))
    except (ValueError, vu.Vagrad) as e:
        print(json.dumps({'vagrad': e.args[0]}, ensure_ascii=False)); return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
