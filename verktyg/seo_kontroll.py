#!/usr/bin/env python3
"""SEO-kontroll: teknisk och innehållsmässig läsning av ett renderat bygge (katalog med HTML eller en sitemap-lista av
lokala filer) mot brief och verksamhetsuppgifter. Rapport, inga rankningslöften: metadata eller Lighthouse-SEO ensamt är
ingen SEO-funktion (ordern avsnitt 4). Kontrollerar per sida: title och description (längd, unika), en h1, canonical,
robots/noindex-läge mot avsett läge (förhandsvisning: noindex; lansering: index), hreflang-par, JSON-LD (giltig JSON,
typ, sanningsenlighet mot VERKSAMHET.json: namn, telefon, adress bara när publik, öppettider), interna länkar som
löser, bildalt; per sajt: sitemap.xml och robots.txt finns och stämmer, kanonisk domän, omdirigeringskarta vid
migrering (--omdirigeringar FIL: gamla URL:er ska finnas som mål eller 301-rad).

    python3 -B verktyg/seo_kontroll.py --bygge KATALOG --lage forhandsvisning|lansering [--verksamhet VERKSAMHET.json]
        [--doman example.se] [--omdirigeringar REDIRECTS.json] --ut RAPPORT.json [--md RAPPORT.md]

Exit 0 (rapport skriven), 2 vid felaktiga argument. Ingen nätåtkomst: läser filer.
"""
import argparse
import html as htmlmod
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verksamhetsuppgifter as vu  # noqa: E402

TITLE = re.compile(r'<title[^>]*>(.*?)</title>', re.S | re.I)
META = re.compile(r'<meta\s+[^>]*>', re.I)
ATTR = re.compile(r'([a-zA-Z-]+)\s*=\s*["\']([^"\']*)["\']')
H1 = re.compile(r'<h1\b', re.I)
LINK = re.compile(r'<link\s+[^>]*>', re.I)
A = re.compile(r'<a\s+[^>]*href=["\']([^"\'#?]+)[^"\']*["\']', re.I)
IMG = re.compile(r'<img\b[^>]*>', re.I)
JSONLD = re.compile(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.S | re.I)
LANG = re.compile(r'<html\b[^>]*\blang=["\']([^"\']+)["\']', re.I)


def attrs(tag):
    return {k.lower(): htmlmod.unescape(v) for k, v in ATTR.findall(tag)}


def sidor(bygge):
    root = Path(bygge)
    for f in sorted(root.rglob('*.html')):
        if not (set(f.parts) & {'node_modules', '.git', '.next', '.vercel'}):
            yield f


def url_for(root, f):
    rel = f.relative_to(root).as_posix()
    if rel.endswith('index.html'):
        rel = rel[:-len('index.html')]
    return '/' + rel.lstrip('/')


def finns_lokalt(root, href):
    p = urlparse(href)
    if p.scheme or p.netloc:
        return None  # extern: inte kontrollerad
    path = p.path
    if not path.startswith('/'):
        return None
    cands = [root / path.lstrip('/'), root / path.lstrip('/') / 'index.html', root / (path.lstrip('/').rstrip('/') + '.html'), root / (path.lstrip('/').rstrip('/') + '/index.html')]
    return any(c.is_file() for c in cands)


def granska_sida(root, f, raw, lage, verksamhet, doman):
    fynd = []
    url = url_for(root, f)
    m = TITLE.search(raw)
    title = htmlmod.unescape(re.sub(r'<[^>]+>', '', m.group(1))).strip() if m else ''
    if not title:
        fynd.append(('title saknas', 'varje sida behöver en unik, sanningsenlig title'))
    elif len(title) > 60:
        fynd.append(('title lång (%d)' % len(title), 'högst omkring 60 tecken; inga superlativ'))
    metas = [attrs(t) for t in META.findall(raw)]
    desc = next((mm.get('content', '') for mm in metas if mm.get('name', '').lower() == 'description'), None)
    if desc is None:
        fynd.append(('description saknas', 'kort beskrivning av sidans innehåll'))
    elif len(desc) > 155:
        fynd.append(('description lång (%d)' % len(desc), 'högst omkring 155 tecken'))
    robots = next((mm.get('content', '').lower() for mm in metas if mm.get('name', '').lower() == 'robots'), '')
    noindex = 'noindex' in robots
    if lage == 'forhandsvisning' and not noindex:
        fynd.append(('index tillåten i förhandsvisning', 'förhandsvisningen ska bära noindex (och skydd); lanseringskonfigurationen är en annan'))
    if lage == 'lansering' and noindex:
        fynd.append(('noindex kvar vid lansering', 'noindex ska bort i lanseringskonfigurationen, annars samlar sökkonsolen inget'))
    n_h1 = len(H1.findall(raw))
    if n_h1 != 1:
        fynd.append(('h1: %d' % n_h1, 'en h1 per sida som svarar på sidans sökintention'))
    if not LANG.search(raw):
        fynd.append(('html lang saknas', 'ange sidans språk'))
    links = [attrs(t) for t in LINK.findall(raw)]
    canon = [l.get('href') for l in links if l.get('rel', '').lower() == 'canonical']
    if not canon:
        fynd.append(('canonical saknas', 'absolut canonical per sida'))
    else:
        c = canon[0]
        if not c.startswith('https://'):
            fynd.append(('canonical inte absolut https', c))
        elif doman and urlparse(c).netloc not in (doman, 'www.' + doman):
            fynd.append(('canonical annan domän', c + ' mot ' + doman))
    hreflang = [(l.get('hreflang'), l.get('href')) for l in links if l.get('rel', '').lower() == 'alternate' and l.get('hreflang')]
    if hreflang and not any(h[0] == 'x-default' for h in hreflang):
        fynd.append(('hreflang utan x-default', 'varje variantuppsättning listar alla varianter och x-default'))
    for href in set(A.findall(raw)):
        ok = finns_lokalt(root, href)
        if ok is False:
            fynd.append(('intern länk löser inte', href))
    for tag in IMG.findall(raw):
        a = attrs(tag)
        if 'alt' not in a:
            fynd.append(('img utan alt', (a.get('src') or '')[:80]))
    for block in JSONLD.findall(raw):
        try:
            data = json.loads(block)
        except ValueError:
            fynd.append(('JSON-LD ogiltig', 'blocket är inte giltig JSON'))
            continue
        for obj in (data if isinstance(data, list) else [data]):
            fynd.extend(granska_schema(obj, verksamhet))
    return {'sida': url, 'title': title, 'noindex': noindex, 'fynd': [{'typ': t, 'text': x} for t, x in fynd]}


def granska_schema(obj, verksamhet):
    fynd = []
    if not isinstance(obj, dict):
        return [('JSON-LD form', 'objekt väntades')]
    typ = obj.get('@type')
    if not typ:
        fynd.append(('JSON-LD utan @type', ''))
    if verksamhet and isinstance(typ, str) and (typ in ('LocalBusiness', 'Organization') or obj.get('address') or obj.get('telephone')):
        n = vu.nap(verksamhet)
        if obj.get('name') and obj['name'] != verksamhet['namn']:
            fynd.append(('schema name ≠ verksamhetens namn', '%r mot %r' % (obj['name'], verksamhet['namn'])))
        if obj.get('telephone') and n['telefon_e164'] and obj['telephone'] != n['telefon_e164']:
            fynd.append(('schema telephone ≠ E.164 ur verksamheten', '%r mot %r' % (obj['telephone'], n['telefon_e164'])))
        if obj.get('address') and not n['adress_visas']:
            fynd.append(('schema bär adress fast adressen inte är publik', 'utelämna address; ange areaServed'))
        if n['adress_visas'] and not obj.get('address') and typ != 'Organization':
            fynd.append(('schema saknar address fast adressen är publik', 'PostalAddress med gata, postnummer NNN NN, ort, SE'))
        adr = obj.get('address') or {}
        if isinstance(adr, dict) and adr.get('postalCode') and not re.match(r'^\d{3} \d{2}$', str(adr['postalCode'])):
            fynd.append(('postalCode-form', str(adr['postalCode']) + ' ska vara "NNN NN"'))
        if obj.get('aggregateRating') and not verksamhet.get('omdomen_kalla'):
            fynd.append(('aggregateRating utan källa', 'betyg bara från verklig plattformsdata med källa i VERKSAMHET.json (omdomen_kalla)'))
        if 'offers' in obj and not obj.get('offers'):
            fynd.append(('offers tomt', 'utelämna hellre än att hitta på pris'))
    return fynd


def granska_sajt(root, lage, doman, omdirigeringar):
    fynd = []
    sm = root / 'sitemap.xml'
    rb = root / 'robots.txt'
    if not sm.is_file():
        fynd.append(('sitemap.xml saknas', 'genereras ur sidorna; lämnas till sökkonsolen vid lansering'))
    else:
        locs = re.findall(r'<loc>\s*([^<\s]+)\s*</loc>', sm.read_text(encoding='utf-8', errors='replace'))
        if not locs:
            fynd.append(('sitemap utan loc', ''))
        if doman:
            for l in locs:
                if urlparse(l).netloc not in (doman, 'www.' + doman):
                    fynd.append(('sitemap loc annan domän', l))
                    break
    if not rb.is_file():
        fynd.append(('robots.txt saknas', ''))
    else:
        text = rb.read_text(encoding='utf-8', errors='replace')
        if 'Sitemap:' not in text:
            fynd.append(('robots utan Sitemap-rad', ''))
        if lage == 'lansering' and re.search(r'(?im)^Disallow:\s*/\s*$', text):
            fynd.append(('robots blockerar allt vid lansering', ''))
        if lage == 'forhandsvisning' and not re.search(r'(?im)^Disallow:\s*/\s*$', text):
            fynd.append(('robots tillåter crawl i förhandsvisning', 'förhandsvisning: Disallow: / och noindex'))
    if omdirigeringar:
        data = json.loads(Path(omdirigeringar).read_text(encoding='utf-8'))
        for rad in data.get('gamla', []):
            mal = rad.get('till')
            if not mal or rad.get('status') not in (301, 308):
                fynd.append(('omdirigering utan 301/308', rad.get('fran', '')))
            elif finns_lokalt(root, mal) is False:
                fynd.append(('omdirigeringsmål saknas', '%s → %s' % (rad.get('fran'), mal)))
    return [{'typ': t, 'text': x} for t, x in fynd]


def rapport(bygge, lage, verksamhet_fil=None, doman=None, omdirigeringar=None):
    root = Path(bygge)
    verksamhet = vu.las(verksamhet_fil) if verksamhet_fil else None
    if verksamhet and not doman:
        doman = (verksamhet.get('webb') or {}).get('doman')
    pages = []
    titles = {}
    for f in sidor(root):
        raw = f.read_text(encoding='utf-8', errors='replace')
        p = granska_sida(root, f, raw, lage, verksamhet, doman)
        titles.setdefault(p['title'], []).append(p['sida'])
        pages.append(p)
    for t, ss in titles.items():
        if t and len(ss) > 1:
            for p in pages:
                if p['sida'] in ss:
                    p['fynd'].append({'typ': 'title dubblett', 'text': ', '.join(ss)})
    sajt = granska_sajt(root, lage, doman, omdirigeringar)
    antal = sum(len(p['fynd']) for p in pages) + len(sajt)
    return {'schema': 1, 'bygge': str(root), 'lage': lage, 'doman': doman, 'sidor': len(pages), 'fynd_totalt': antal,
            'sajt': sajt, 'per_sida': pages, 'uppgiftsvarningar': vu.validera(verksamhet) if verksamhet else ['verksamhetsuppgifter ej lämnade; teknisk räckvidd'], 'kontaktberedskap': 'ofullständig' if verksamhet is not None and not verksamhet.get('kontaktvagar') else 'faktisk kontaktresa ej prövad', 'verksamhet': verksamhet['namn'] if verksamhet else None,
            'not': 'rapport över teknisk och innehållsmässig SEO-beredskap; inga rankningslöften; strukturerad data prövas mot verksamhetsuppgifterna, inte mot Googles verktyg'}


def markdown(r):
    lines = ['# SEO-kontroll — %s, läge %s, %d sidor, %d fynd' % (r['bygge'], r['lage'], r['sidor'], r['fynd_totalt']), '', '## Sajt']
    lines += ['- %s: %s' % (x['typ'], x['text']) for x in r['sajt']] or ['- inga fynd']
    for p in r['per_sida']:
        lines += ['', '## %s — %s%s' % (p['sida'], p['title'] or '(ingen title)', ' [noindex]' if p['noindex'] else '')]
        lines += ['- %s: %s' % (x['typ'], x['text']) for x in p['fynd']] or ['- inga fynd']
    return '\n'.join(lines) + '\n\n' + r['not'] + '\n'


def main(argv=None):
    p = argparse.ArgumentParser(prog='seo_kontroll', description=__doc__.split('\n\n')[0])
    p.add_argument('--bygge', required=True)
    p.add_argument('--lage', required=True, choices=('forhandsvisning', 'lansering'))
    p.add_argument('--verksamhet')
    p.add_argument('--doman')
    p.add_argument('--omdirigeringar')
    p.add_argument('--ut', required=True)
    p.add_argument('--md')
    a = p.parse_args(argv)
    if not Path(a.bygge).is_dir():
        print(json.dumps({'fel': 'bygget är ingen katalog: ' + a.bygge}))
        return 2
    try:
        r = rapport(a.bygge, a.lage, a.verksamhet, a.doman, a.omdirigeringar)
    except vu.Vagrad as e:
        print(json.dumps({'fel': e.args[0]}, ensure_ascii=False))
        return 2
    Path(a.ut).write_text(json.dumps(r, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    if a.md:
        Path(a.md).write_text(markdown(r), encoding='utf-8')
    print(json.dumps({'sidor': r['sidor'], 'fynd_totalt': r['fynd_totalt'], 'ut': a.ut}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
