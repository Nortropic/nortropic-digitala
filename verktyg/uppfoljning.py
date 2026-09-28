#!/usr/bin/env python3
"""Mätning och uppföljning: händelseplan, lead-/konverteringskedja, kampanjmärkning, felsökning av mätningen och
samtyckesläge. Skiljer verklig affärsnytta (offert, bokning, samtal som besvarats) från proxyvärden (sidvisningar,
klick). Ingen spårning före samtycke; serverbaserad spårning är ingen genväg runt samtycket.

    python3 -B verktyg/uppfoljning.py plan --matplan MATPLAN.json --ut HANDELSEPLAN.md
    python3 -B verktyg/uppfoljning.py kontrollera --matplan MATPLAN.json --bygge DIR --ut KONTROLL.json
    python3 -B verktyg/uppfoljning.py utm --url https://… --kalla google --medium cpc --kampanj namn
    python3 -B verktyg/uppfoljning.py las --export FIL.csv --matplan MATPLAN.json --ut LASNING.json

MATPLAN.json: {"schema": 1, "verktyg": "vercel-analytics|ga4|plausible|matomo|ingen", "samtycke_kravs": bool,
"handelser": [{"namn": "quote_submit", "utlosare": "formulär skickat", "var": "/kontakt", "konvertering": true, "parametrar": [...]}],
"kedja": ["besök", "kontaktsida", "formulär skickat", "mejl levererat", "svar till kund"], "affarsmatt": ["offertförfrågningar", "bokningar"]}
"""
import argparse
import csv
import json
import re
import sys
import urllib.parse
from pathlib import Path

SPARARE = {'gtag(': 'GA4/gtag', 'googletagmanager.com': 'Google Tag Manager', 'fbq(': 'Meta-pixel', 'connect.facebook.net': 'Meta-pixel', 'ttq.': 'TikTok-pixel', 'hotjar': 'Hotjar', 'clarity.ms': 'Microsoft Clarity'}
SAMTYCKE = re.compile(r'consent|samtycke|cookie', re.I)
VERKTYG = ('vercel-analytics', 'ga4', 'plausible', 'matomo', 'ingen')


class Vagrad(Exception):
    pass


def validera(mp):
    fel = []
    if mp.get('schema') != 1:
        fel.append('schema ska vara 1')
    if mp.get('verktyg') not in VERKTYG:
        fel.append('verktyg ska vara en av ' + ', '.join(VERKTYG))
    if not isinstance(mp.get('samtycke_kravs'), bool):
        fel.append('samtycke_kravs ska vara true eller false')
    if mp.get('verktyg') == 'ga4' and mp.get('samtycke_kravs') is False:
        fel.append('ga4 sätter kakor: samtycke_kravs måste vara true (Consent Mode med nekat som standard)')
    h = mp.get('handelser')
    if not isinstance(h, list) or not h:
        fel.append('handelser: minst en händelse')
    else:
        namn = set()
        for i, e in enumerate(h):
            if not re.fullmatch(r'[a-z][a-z0-9_]{2,39}', str(e.get('namn', ''))):
                fel.append('handelser[%d].namn ska vara snake_case, 3–40 tecken' % i)
            if e.get('namn') in namn:
                fel.append('handelser[%d].namn dubblett' % i)
            namn.add(e.get('namn'))
            for f in ('utlosare', 'var'):
                if not str(e.get(f, '')).strip():
                    fel.append('handelser[%d].%s saknas' % (i, f))
            if not isinstance(e.get('konvertering'), bool):
                fel.append('handelser[%d].konvertering ska vara true eller false' % i)
        if not any(e.get('konvertering') for e in h):
            fel.append('minst en händelse ska vara en konvertering, annars mäts ingen affärsnytta')
    if not isinstance(mp.get('kedja'), list) or len(mp.get('kedja') or []) < 2:
        fel.append('kedja: minst två steg från besök till affärsutfall')
    if not isinstance(mp.get('affarsmatt'), list) or not mp.get('affarsmatt'):
        fel.append('affarsmatt: minst ett verkligt affärsmått (offerter, bokningar, samtal)')
    if fel:
        raise Vagrad(fel)


def handelseplan_md(mp):
    lines = ['# Händelseplan', '', 'Verktyg: %s · samtycke krävs: %s' % (mp['verktyg'], 'ja' if mp['samtycke_kravs'] else 'nej (kakfritt verktyg)'), '',
             '| Händelse | Utlösare | Var | Konvertering | Parametrar |', '|---|---|---|---|---|']
    lines += ['| `%s` | %s | %s | %s | %s |' % (e['namn'], e['utlosare'], e['var'], 'ja' if e['konvertering'] else 'nej', ', '.join(e.get('parametrar') or [])) for e in mp['handelser']]
    lines += ['', '## Kedja från besök till affärsutfall', ''] + ['%d. %s' % (i + 1, s) for i, s in enumerate(mp['kedja'])]
    lines += ['', '## Affärsmått (verklig nytta)', ''] + ['- ' + m for m in mp['affarsmatt']]
    lines += ['', '## Proxyvärden (stöd, inte mål)', '', '- sidvisningar, klick, tid på sidan, ctr', '', '## Regler', '',
              '- Ingen spårning före samtycke när samtycke krävs; nekat som standard; neka lika lätt som acceptera.',
              '- Serverbaserad spårning ändrar inte samtyckeskravet.', '- Kampanjmärkning med utm_source, utm_medium, utm_campaign (utm_content vid varianter).',
              '- Felsökning: händelsen ska synas i verktygets felsökningsläge innan den kallas mätt; en händelse i koden är inte en mätt händelse.',
              '- Läsning: sök- och kampanjdata omsätts i innehålls- och upplevelseändringar (uppfoljning.md), inte i rapporter för sin egen skull.']
    return '\n'.join(lines) + '\n'


def kontrollera(mp, bygge):
    root = Path(bygge)
    filer = [f for f in root.rglob('*') if f.is_file() and f.suffix in ('.html', '.js', '.mjs', '.tsx', '.jsx', '.ts') and not (set(f.parts) & {'node_modules', '.git', '.next'})]
    texter = {f: f.read_text(encoding='utf-8', errors='replace') for f in filer}
    allt = '\n'.join(texter.values())
    ut = {'schema': 2, 'niva': 'statisk textsökning — inga körda händelser', 'bygge': str(root), 'filer': len(filer), 'handelser': [], 'sparare': [], 'samtycke': None, 'fynd': []}
    for e in mp['handelser']:
        rx = re.compile(r'''(["'`])%s\1''' % re.escape(e['namn']))
        var = sorted({str(f.relative_to(root)) for f, t in texter.items() if rx.search(t)})
        ut['handelser'].append({'namn': e['namn'], 'texttraff': bool(var), 'handelse_verifierad': False, 'filer': var[:5], 'status': 'ordträff (kan vara kommentar eller död kod; ej händelsebevis)' if var else 'ingen ordträff (inte bevis på frånvaro i körning)'})
        if not var:
            ut['fynd'].append('händelsen %s finns inte i bygget' % e['namn'])
    for nyckel, namn in SPARARE.items():
        if nyckel in allt:
            ut['sparare'].append(namn)
    ut['sparare'] = sorted(set(ut['sparare']))
    har_samtycke = bool(SAMTYCKE.search(allt))
    ut['samtycke'] = {'kravs': mp['samtycke_kravs'], 'texttraff': har_samtycke, 'beteende_verifierat': False}
    if ut['sparare'] and not har_samtycke:
        ut['fynd'].append('textträff för spårare (%s) utan samtyckestext; beteende måste prövas' % ', '.join(ut['sparare']))
    if mp['verktyg'] in ('ga4',) and 'gtag(' not in allt and 'googletagmanager.com' not in allt:
        ut['fynd'].append('verktyget ga4 är valt men inget gtag/GTM finns i bygget')
    if mp['verktyg'] == 'ingen' and ut['sparare']:
        ut['fynd'].append('mätplanen säger inget verktyg men textsökningen hittar spårarnamn: ' + ', '.join(ut['sparare']))
    ut['mottagning'] = {'verifierad': False, 'status': 'ej prövad; nätverksförsök är inte mottagarbekräftelse'}
    ut['kvarstaende_prov'] = ['faktisk utlösare och rätt händelse', 'nätverk före nekat/accepterat/återkallat samtycke', 'händelsens korrelation i rätt mätmottagare och egenskap']
    ut['not'] = 'en händelse i koden är inte en mätt händelse: verifiera i verktygets felsökningsläge eller med webbläsarverktygets nätverkslogg'
    return ut


def utm(url, kalla, medium, kampanj, innehall=None):
    p = urllib.parse.urlsplit(url)
    if p.scheme != 'https':
        raise Vagrad(['kampanjlänkar ska vara https'])
    q = dict(urllib.parse.parse_qsl(p.query))
    for k, val in (('utm_source', kalla), ('utm_medium', medium), ('utm_campaign', kampanj), ('utm_content', innehall)):
        if val:
            q[k] = re.sub(r'[^a-z0-9_-]+', '-', val.lower()).strip('-')
    return urllib.parse.urlunsplit((p.scheme, p.netloc, p.path, urllib.parse.urlencode(q), p.fragment))


def las(export, mp):
    p = Path(export)
    if p.suffix == '.json':
        rows = json.loads(p.read_text(encoding='utf-8'))
    else:
        with p.open(encoding='utf-8-sig') as f: rows = list(csv.DictReader(f))
    konv = {e['namn'] for e in mp['handelser'] if e['konvertering']}
    summa = {'affarsnytta': {}, 'proxy': {}}
    for r in rows:
        namn = r.get('event') or r.get('eventName') or r.get('Händelse') or r.get('name') or ''
        antal = float(str(r.get('count') or r.get('eventCount') or r.get('Antal') or 0).replace(',', '.') or 0)
        (summa['affarsnytta'] if namn in konv else summa['proxy'])[namn] = summa['affarsnytta'].get(namn, 0) + antal if namn in konv else summa['proxy'].get(namn, 0) + antal
    return {'schema': 1, 'export': str(p), 'rader': len(rows), **summa, 'not': 'affärsnytta = planens konverteringshändelser; allt annat är proxy; jämför med kundens verkliga inflöde (mejl, bokningar) innan något kallas resultat'}


def main(argv=None):
    p = argparse.ArgumentParser(prog='uppfoljning', description=__doc__.split('\n\n')[0])
    p.add_argument('kommando', choices=('plan', 'kontrollera', 'utm', 'las'))
    p.add_argument('--matplan'); p.add_argument('--bygge'); p.add_argument('--export'); p.add_argument('--ut')
    p.add_argument('--url'); p.add_argument('--kalla'); p.add_argument('--medium'); p.add_argument('--kampanj'); p.add_argument('--innehall')
    a = p.parse_args(argv)
    try:
        if a.kommando == 'utm':
            if not (a.url and a.kalla and a.medium and a.kampanj):
                raise Vagrad(['utm kräver --url --kalla --medium --kampanj'])
            print(utm(a.url, a.kalla, a.medium, a.kampanj, a.innehall)); return 0
        if not (a.matplan and a.ut):
            raise Vagrad([a.kommando + ' kräver --matplan och --ut'])
        mp = json.loads(Path(a.matplan).read_text(encoding='utf-8'))
        validera(mp)
        if a.kommando == 'plan':
            Path(a.ut).write_text(handelseplan_md(mp), encoding='utf-8'); print(json.dumps({'handelser': len(mp['handelser']), 'ut': a.ut}))
        elif a.kommando == 'kontrollera':
            if not a.bygge or not Path(a.bygge).is_dir():
                raise Vagrad(['kontrollera kräver --bygge KATALOG'])
            k = kontrollera(mp, a.bygge)
            Path(a.ut).write_text(json.dumps(k, ensure_ascii=False, indent=1) + '\n', encoding='utf-8'); print(json.dumps({'fynd': len(k['fynd']), 'sparare': k['sparare'], 'ut': a.ut}, ensure_ascii=False))
        else:
            if not a.export:
                raise Vagrad(['las kräver --export'])
            l = las(a.export, mp)
            Path(a.ut).write_text(json.dumps(l, ensure_ascii=False, indent=1) + '\n', encoding='utf-8'); print(json.dumps({'rader': l['rader'], 'ut': a.ut}))
    except Vagrad as e:
        print(json.dumps({'vagrad': e.args[0]}, ensure_ascii=False)); return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
