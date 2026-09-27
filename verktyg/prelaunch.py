#!/usr/bin/env python3
"""Prelaunch: åtta grindar som rapport före lansering — 0 byggintegritet, 1 viktiga handlingar från början till slut,
2 prestanda, 3 responsivitet, 4 tillgänglighet, 5 SEO-beredskap, 6 juridik (rapporteras, avgörs av människa),
7 säkerhet. Varje grind får PASS, FAIL, EJ_MATT eller MANNISKA med belägg; helheten är "redo" bara när grind 0–5 och 7
är PASS och grind 6 saknar ohanterade flaggor. Verktyget godkänner aldrig juridik och gissar aldrig: det som inte
mätts står som EJ_MATT. Mätvärden kommer ur Runtimes mätkvitto (--matning), handlingsprov ur provarkörningar
(--handlingar), säkerhetsrubriker ur en sparad svarshuvudfil eller ett live-HEAD-anrop (--adress).

    python3 -B verktyg/prelaunch.py --bygge DIR --lage forhandsvisning|lansering [--repo DIR] [--verksamhet V.json]
        [--matning KORNING.json] [--handlingar HANDLINGAR.json] [--juridik JURIDIK.json] [--huvuden FIL] [--adress https://…]
        [--audit npm-audit.json] [--krav KRAV.json] --ut PRELAUNCH.json [--md PRELAUNCH.md]
"""
import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seo_kontroll as sk  # noqa: E402
import copy_kontroll as ck  # noqa: E402

STANDARDKRAV = {'performance': 90, 'accessibility': 95, 'best_practices': 95, 'seo': 95, 'lcp_ms': 2500, 'cls': 0.1, 'inp_ms': 200, 'sidvikt_kb': 1000}
HEMLIGHETER = re.compile(r'(re_[A-Za-z0-9]{20,}|sk_live_[A-Za-z0-9]{10,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{30,}|xox[baprs]-[A-Za-z0-9-]{10,}|-----BEGIN (RSA |EC )?PRIVATE KEY-----)')
RUBRIKER = {'content-security-policy': 'Content-Security-Policy', 'strict-transport-security': 'Strict-Transport-Security', 'x-content-type-options': 'X-Content-Type-Options', 'referrer-policy': 'Referrer-Policy'}


def grind(namn, status, belagg, atgard=None):
    return {'grind': namn, 'status': status, 'belagg': belagg, 'atgard': atgard}


def g0_bygg(bygge, repo):
    root = Path(bygge)
    html = list(sk.sidor(root))
    if not html:
        return grind('0 byggintegritet', 'FAIL', 'inga HTML-sidor i ' + str(root))
    platsh = []
    for f in html:
        raw = f.read_text(encoding='utf-8', errors='replace').lower()
        for ph in ('lorem ipsum', 'todo-fact', 'todo-copy', '[osäker]'):
            if ph in raw:
                platsh.append('%s: %s' % (sk.url_for(root, f), ph))
    hemligt = []
    for f in root.rglob('*'):
        if f.is_file() and f.suffix in ('.html', '.js', '.mjs', '.css', '.json', '.txt', '.map') and not (set(f.parts) & {'node_modules', '.git'}):
            if HEMLIGHETER.search(f.read_text(encoding='utf-8', errors='replace')):
                hemligt.append(str(f.relative_to(root)))
    env_ex = None
    if repo:
        env_ex = any((Path(repo) / n).is_file() for n in ('.env.example', '.env.local.example'))
    belagg = '%d sidor; platshållare: %d; hemligheter i bygget: %d; .env.example: %s' % (len(html), len(platsh), len(hemligt), 'finns' if env_ex else ('saknas' if env_ex is False else 'inte kontrollerat'))
    status = 'PASS' if not platsh and not hemligt and env_ex is not False else 'FAIL'
    return grind('0 byggintegritet', status, belagg, (platsh + hemligt) or None)


def g1_handlingar(handlingar):
    if not handlingar:
        return grind('1 viktiga handlingar', 'EJ_MATT', 'ingen HANDLINGAR.json: handlingarna ur briefens §4 med provkvitto per handling', 'skriv HANDLINGAR.json [{namn, typ, prov: provare|manuell, kvitto, utfall}]')
    data = json.loads(Path(handlingar).read_text(encoding='utf-8'))
    rader = []; ok = True
    for h in data.get('handlingar', []):
        kvitto = h.get('kvitto'); utfall = None
        if kvitto and Path(kvitto).is_file():
            try:
                k = json.loads(Path(kvitto).read_text(encoding='utf-8'))
                utfall = k.get('utfall') or k.get('bedomning') or k.get('status')
            except ValueError:
                utfall = 'kvitto oläsbart'
        elif h.get('prov') == 'manuell' and h.get('utfall'):
            utfall = 'manuell: ' + h['utfall']
        rader.append('%s (%s): %s' % (h.get('namn'), h.get('typ'), utfall or 'inte prövad'))
        if not utfall or not str(utfall).lower().startswith(('klar', 'godk', 'manuell: godk', 'pass')):
            ok = False
    if not rader:
        return grind('1 viktiga handlingar', 'EJ_MATT', 'HANDLINGAR.json utan handlingar')
    return grind('1 viktiga handlingar', 'PASS' if ok else 'FAIL', '; '.join(rader), None if ok else 'varje viktig handling ska ha ett provkvitto med utfall klar/godkänd (leveransen är provet, inte svarskoden)')


def las_matning(matning):
    if not matning or not Path(matning).is_file():
        return None
    try:
        return json.loads(Path(matning).read_text(encoding='utf-8'))
    except ValueError:
        return None


def hitta(d, *nycklar):
    """Djupsök första förekomsten av en nyckel i ett kvitto (Runtimes mätkvitto varierar i form)."""
    if isinstance(d, dict):
        for k in nycklar:
            if k in d:
                return d[k]
        for v in d.values():
            r = hitta(v, *nycklar)
            if r is not None:
                return r
    elif isinstance(d, list):
        for v in d:
            r = hitta(v, *nycklar)
            if r is not None:
                return r
    return None


def g2_prestanda(m, krav):
    if not m:
        return grind('2 prestanda', 'EJ_MATT', 'inget mätkvitto (--matning ur verktyg/kor_profil.py matning)')
    lh = hitta(m, 'lighthouse', 'lighthouse_scores', 'poang')
    if not isinstance(lh, dict):
        return grind('2 prestanda', 'EJ_MATT', 'mätkvittot saknar Lighthouse-poäng')
    def sc(k):
        v = lh.get(k) if k in lh else hitta(lh, k)
        return v * 100 if isinstance(v, (int, float)) and v <= 1 else v
    poang = {k: sc(k) for k in ('performance', 'accessibility', 'best_practices', 'seo')}
    poang = {k: v for k, v in poang.items() if v is not None}
    brister = [k for k, v in poang.items() if v < krav[k]]
    lcp = hitta(m, 'lcp_ms', 'largest-contentful-paint', 'lcp'); cls = hitta(m, 'cls', 'cumulative-layout-shift')
    if isinstance(lcp, (int, float)) and lcp > krav['lcp_ms']:
        brister.append('lcp')
    if isinstance(cls, (int, float)) and cls > krav['cls']:
        brister.append('cls')
    belagg = 'Lighthouse %s; LCP %s ms; CLS %s; INP: mäts inte av navigations-Lighthouse (EJ_MATT, fältdata krävs)' % (poang, lcp, cls)
    if not poang:
        return grind('2 prestanda', 'EJ_MATT', belagg)
    return grind('2 prestanda', 'FAIL' if brister else 'PASS', belagg, ('under kravnivå: ' + ', '.join(brister)) if brister else None)


def g3_responsivitet(m):
    if not m:
        return grind('3 responsivitet', 'EJ_MATT', 'inget mätkvitto')
    vyer = hitta(m, 'vyer', 'viewports')
    spill = hitta(m, 'horisontell_spill', 'horizontal_overflow', 'overflow')
    if vyer is None:
        return grind('3 responsivitet', 'EJ_MATT', 'mätkvittot saknar vyer')
    belagg = 'vyer: %s; horisontell spill: %s' % (list(vyer) if isinstance(vyer, (list, dict)) else vyer, spill)
    if spill is None:
        return grind('3 responsivitet', 'EJ_MATT', belagg + '; spill inte rapporterat — bedöm skärmbilderna (webbläsarverktyget)')
    dalig = spill if isinstance(spill, bool) else bool(spill)
    return grind('3 responsivitet', 'FAIL' if dalig else 'PASS', belagg)


def g4_tillganglighet(m):
    if not m:
        return grind('4 tillgänglighet', 'EJ_MATT', 'inget mätkvitto (axe)')
    axe = hitta(m, 'axe', 'axe_violations', 'violations')
    if axe is None:
        return grind('4 tillgänglighet', 'EJ_MATT', 'mätkvittot saknar axe-resultat')
    antal = len(axe) if isinstance(axe, list) else (axe if isinstance(axe, int) else hitta(axe, 'violations', 'antal_violations'))
    if isinstance(antal, list):
        antal = len(antal)
    belagg = 'axe violations: %s; manuellt återstår alltid: tangentbord, fokus, kontrast, alt-texter, formulärfel, rörelse (axe täcker en del av kriterierna)' % antal
    return grind('4 tillgänglighet', 'PASS' if antal == 0 else ('FAIL' if isinstance(antal, int) else 'EJ_MATT'), belagg)


def g5_seo(bygge, lage, verksamhet):
    r = sk.rapport(bygge, lage, verksamhet)
    return grind('5 SEO-beredskap', 'PASS' if r['fynd_totalt'] == 0 else 'FAIL', '%d sidor, %d fynd (seo_kontroll, läge %s)' % (r['sidor'], r['fynd_totalt'], lage), None if r['fynd_totalt'] == 0 else 'se SEO-rapporten; inga rankningslöften')


def g6_juridik(juridik):
    bas = ['integritetspolicy med ansvarig, ändamål, rättslig grund, lagring, rättigheter', 'samtyckesläge stämmer med det som laddas', 'företagsuppgifter (namn, organisationsnummer, adress eller ort, kontakt)', 'verifierbara påståenden (betyg med källa, certifieringar mot register)', 'priser inklusive moms mot konsumenter; ROT/RUT korrekt']
    if not juridik:
        return grind('6 juridik', 'MANNISKA', 'ingen JURIDIK.json; basen gäller alltid: ' + '; '.join(bas), 'människa avgör; verktyget godkänner aldrig juridik')
    data = json.loads(Path(juridik).read_text(encoding='utf-8'))
    flaggor = data.get('flaggor', [])
    ohant = [f for f in flaggor if f.get('status') not in ('hanterad', 'utanför uppdraget')]
    return grind('6 juridik', 'MANNISKA', 'flaggor: %s; ohanterade: %d; basen: %s' % ([f.get('flagga') for f in flaggor], len(ohant), '; '.join(bas)),
                 'människa avgör varje flagga; ohanterade: ' + ', '.join(f.get('flagga', '?') for f in ohant) if ohant else 'inga ohanterade flaggor; basen bekräftas av människa')


def las_huvuden(huvuden, adress):
    if huvuden and Path(huvuden).is_file():
        text = Path(huvuden).read_text(encoding='utf-8', errors='replace')
        return {l.split(':', 1)[0].strip().lower(): l.split(':', 1)[1].strip() for l in text.splitlines() if ':' in l and not l.lower().startswith('http/')}, 'sparad huvudfil'
    if adress:
        req = urllib.request.Request(adress, method='HEAD', headers={'User-Agent': 'nortropic-digitala prelaunch'})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return {k.lower(): v for k, v in r.headers.items()}, 'live HEAD ' + adress
        except Exception as e:  # noqa: BLE001
            return None, 'HEAD misslyckades: %s' % e.__class__.__name__
    return None, 'inga svarshuvuden (--huvuden eller --adress)'


def g7_sakerhet(huvuden, adress, audit, bygge):
    h, kalla = las_huvuden(huvuden, adress)
    brister = []; belagg = [kalla]
    if h is None:
        status_h = 'EJ_MATT'
    else:
        saknas = [namn for k, namn in RUBRIKER.items() if k not in h]
        frame = ('frame-ancestors' in h.get('content-security-policy', '').lower()) or ('x-frame-options' in h)
        if not frame:
            saknas.append('frame-ancestors/X-Frame-Options')
        if h.get('x-content-type-options', '').lower() != 'nosniff' and 'x-content-type-options' in h:
            saknas.append('X-Content-Type-Options ≠ nosniff')
        belagg.append('saknade rubriker: ' + (', '.join(saknas) or 'inga'))
        status_h = 'PASS' if not saknas else 'FAIL'
        brister += saknas
    if audit and Path(audit).is_file():
        try:
            a = json.loads(Path(audit).read_text(encoding='utf-8'))
            v = (a.get('metadata') or {}).get('vulnerabilities') or {}
            hc = int(v.get('high', 0)) + int(v.get('critical', 0))
            belagg.append('npm audit: high+critical = %d' % hc)
            if hc:
                brister.append('beroenden med high/critical')
        except ValueError:
            belagg.append('npm audit: oläsbar fil'); status_h = 'EJ_MATT' if status_h == 'PASS' else status_h
    else:
        belagg.append('npm audit: inte lämnat (--audit npm-audit.json)')
    status = 'FAIL' if brister else status_h
    return grind('7 säkerhet', status, '; '.join(belagg), ('åtgärda: ' + ', '.join(brister)) if brister else None)


def rapport(a):
    krav = dict(STANDARDKRAV)
    if a.krav:
        krav.update(json.loads(Path(a.krav).read_text(encoding='utf-8')))
    m = las_matning(a.matning)
    grindar = [g0_bygg(a.bygge, a.repo), g1_handlingar(a.handlingar), g2_prestanda(m, krav), g3_responsivitet(m), g4_tillganglighet(m), g5_seo(a.bygge, a.lage, a.verksamhet), g6_juridik(a.juridik), g7_sakerhet(a.huvuden, a.adress, a.audit, a.bygge)]
    tekniska = [g for g in grindar if not g['grind'].startswith('6')]
    redo = all(g['status'] == 'PASS' for g in tekniska) and 'ohanterade: ' not in (grindar[6]['atgard'] or '') or False
    if 'ohanterade:' in (grindar[6]['atgard'] or '') and not (grindar[6]['atgard'] or '').startswith('inga'):
        redo = False
    return {'schema': 1, 'bygge': a.bygge, 'lage': a.lage, 'krav': krav, 'grindar': grindar, 'redo_for_lansering': bool(redo),
            'not': 'redo = grind 0–5 och 7 PASS och inga ohanterade juridikflaggor; juridik avgörs av människa; EJ_MATT är inte PASS; gröna verktygsprov bevisar inte mänsklig användbarhet'}


def markdown(r):
    lines = ['# Prelaunch — %s (läge %s) — %s' % (r['bygge'], r['lage'], 'REDO för lansering enligt grindarna' if r['redo_for_lansering'] else 'INTE redo'), '', '| Grind | Status | Belägg | Åtgärd |', '|---|---|---|---|']
    for g in r['grindar']:
        lines.append('| %s | %s | %s | %s |' % (g['grind'], g['status'], str(g['belagg']).replace('|', '/'), str(g['atgard'] or '').replace('|', '/')))
    return '\n'.join(lines) + '\n\n' + r['not'] + '\n'


def main(argv=None):
    p = argparse.ArgumentParser(prog='prelaunch', description=__doc__.split('\n\n')[0])
    p.add_argument('--bygge', required=True); p.add_argument('--lage', required=True, choices=('forhandsvisning', 'lansering')); p.add_argument('--repo'); p.add_argument('--verksamhet')
    p.add_argument('--matning'); p.add_argument('--handlingar'); p.add_argument('--juridik'); p.add_argument('--huvuden'); p.add_argument('--adress'); p.add_argument('--audit'); p.add_argument('--krav')
    p.add_argument('--ut', required=True); p.add_argument('--md')
    a = p.parse_args(argv)
    if not Path(a.bygge).is_dir():
        print(json.dumps({'fel': 'bygget är ingen katalog'})); return 2
    r = rapport(a)
    Path(a.ut).write_text(json.dumps(r, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    if a.md:
        Path(a.md).write_text(markdown(r), encoding='utf-8')
    print(json.dumps({'redo': r['redo_for_lansering'], 'grindar': {g['grind']: g['status'] for g in r['grindar']}, 'ut': a.ut}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
