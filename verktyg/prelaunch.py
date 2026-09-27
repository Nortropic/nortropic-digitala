#!/usr/bin/env python3
"""Prelaunch: åtta grindar som rapport före lansering — 0 byggintegritet, 1 viktiga handlingar från början till slut,
2 prestanda, 3 responsivitet, 4 tillgänglighet, 5 SEO-beredskap, 6 juridik (rapporteras, avgörs av människa),
7 säkerhet. Varje grind får PASS, FAIL, EJ_MATT eller MANNISKA med belägg; helheten är "redo" bara när grind 0–5 och 7
är PASS, JURIDIK.json är lämnad och grind 6 saknar ohanterade flaggor. Verktyget godkänner aldrig juridik och gissar aldrig: det som inte
mätts står som EJ_MATT. Mätvärden kommer ur Runtimes mätkvitto (--matning), handlingsprov ur provarkörningar
(--handlingar), säkerhetsrubriker ur en sparad svarshuvudfil eller ett live-HEAD-anrop (--adress).

    python3 -B verktyg/prelaunch.py --bygge DIR --lage forhandsvisning|lansering [--repo DIR] [--verksamhet V.json]
        [--matning KORNING.json] [--inspektion INSPEKTION.json] [--handlingar HANDLINGAR.json] [--juridik JURIDIK.json] [--huvuden FIL] [--adress https://…]
        [--audit npm-audit.json] [--krav KRAV.json] --ut PRELAUNCH.json [--md PRELAUNCH.md]
"""
import argparse
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seo_kontroll as sk  # noqa: E402
import copy_kontroll as ck  # noqa: E402
import stegbevis  # noqa: E402

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


def bygg_hash(bygge):
    root = Path(bygge).resolve()
    rows = [(str(p.relative_to(root)), hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(root.rglob('*')) if p.is_file() and not set(p.relative_to(root).parts) & {'node_modules', '.git'}]
    return hashlib.sha256(json.dumps(rows, separators=(',', ':')).encode()).hexdigest()


def g1_handlingar(handlingar, bygge=None):
    if not handlingar:
        return grind('1 viktiga handlingar', 'EJ_MATT', 'ingen HANDLINGAR.json med kandidatbundet stegbevis')
    try:
        data = stegbevis.las(handlingar)
        if not bygge or data.get('bygge_sha256') != bygg_hash(bygge):
            return grind('1 viktiga handlingar', 'EJ_MATT', 'handlingsprovet saknar aktuell bygginnehållshash; ingen kandidat antas')
        if not data.get('handlingar'):
            return grind('1 viktiga handlingar', 'EJ_MATT', 'HANDLINGAR.json utan handlingar')
        rows = []
        for h in data['handlingar']:
            if not all(data.get(k) for k in ('fall', 'kund')) or not h.get('bevis') or not h.get('kontroll_id'):
                return grind('1 viktiga handlingar', 'EJ_MATT', 'handling saknar fall/kund/bevis/kontroll_id; äldre fri status är inte verifierat resultat')
            b = stegbevis.las(h['bevis'])
            g = stegbevis.kontrollera(h['bevis'], data['fall'], data['kund'], b.get('steg'))
            kr = g['stegkrav']['kontroller']
            if h['kontroll_id'] not in kr or not any(r['id'] == h['kontroll_id'] and r['utfall'] == 'godkant' for r in b['kontroller']):
                raise stegbevis.Vagrad('handlingen saknar obligatoriskt godkänt prov: ' + h['kontroll_id'])
            control = next(r for r in b['kontroller'] if r['id'] == h['kontroll_id'])
            actual_build = stegbevis.pekare(stegbevis.las(control['fil']), control.get('byggpekare'))
            if actual_build != data['bygge_sha256']:
                raise stegbevis.Vagrad('råresultatet gäller annat bygginnehåll; en ny hash i HANDLINGAR.json räcker inte')
            rows.append('%s (%s): godkänt kandidatbundet prov %s, nivå %s' % (h.get('namn'), h.get('typ'), h['kontroll_id'], b['niva']))
        return grind('1 viktiga handlingar', 'PASS', '; '.join(rows))
    except (stegbevis.Vagrad, KeyError, TypeError) as e:
        return grind('1 viktiga handlingar', 'FAIL', str(e), 'rätta bevisbindningen och prova faktisk kandidat; återanvänd inte fri status')


def las_matning(matning):
    """Läser mätkvittot. Ett KORNING-kvitto från verktyg/kor_profil.py pekar på Runtimes körkatalog (resultat.run); då läses
    körningens SAMMANFATTNING.json (Lighthouse, axe, h1, handling, detektor per vy) och KVITTO.json (vyer) in under
    kvittot, så att grindarna får sina mätvärden ur körningen — inte ur startposten (fynd ur slutprovet HELHET-20260927)."""
    if not matning or not Path(matning).is_file():
        return None
    try:
        m = json.loads(Path(matning).read_text(encoding='utf-8'))
    except ValueError:
        return None
    run = (m.get('resultat') or {}).get('run') if isinstance(m, dict) else None
    if run and Path(run).is_dir():
        # körningens sammanfattning läggs FÖRST så att djupsökningen hittar mätvärdena, inte startpostens verktygsversioner
        m2 = {'korning_katalog': run}
        for namn, nyckel in (('SAMMANFATTNING.json', 'sammanfattning'), ('KVITTO.json', 'kvitto')):
            f = Path(run) / namn
            if f.is_file():
                try:
                    m2[nyckel] = json.loads(f.read_text(encoding='utf-8'))
                except ValueError:
                    m2[nyckel] = None
        vyer = (m2.get('kvitto') or {}).get('viewports') or (m2.get('sammanfattning') or {}).get('views')
        if isinstance(vyer, dict):
            m2['vyer'] = list(vyer.keys())
        if m.get('resultat', {}).get('outcome') not in (None, 'klar'):
            m2['ofullstandig'] = m['resultat'].get('outcome')
        m2['korning'] = m
        return m2
    return m


def las_inspektion(inspektion):
    """INSPEKTION.json från verktyg/webblasare/inspektera.mjs: horisontellt spill per vy (spill.spill), layoutbredd = fönster."""
    if not inspektion or not Path(inspektion).is_file():
        return None
    try:
        j = json.loads(Path(inspektion).read_text(encoding='utf-8'))
    except ValueError:
        return None
    ut = {}
    for vy, v in (j.get('vyer') or {}).items():
        sp = v.get('spill') if isinstance(v, dict) else None
        if isinstance(sp, dict):
            ut[vy] = {'spill': bool(sp.get('spill')), 'scrollWidth': sp.get('scrollWidth'), 'clientWidth': sp.get('clientWidth')}
    return ut or None


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


def g2_prestanda(m, krav, lage='lansering'):
    """Lighthouse per vy (mobil och desktop) ur körningens sammanfattning; sämsta vyn gäller. I förhandsvisning är sidan
    noindex och robots stänger, så Lighthouse-SEO är per definition låg: den redovisas men avgör inte (SEO-beredskapen
    prövas av grind 5 mot avsett läge)."""
    if not m:
        return grind('2 prestanda', 'EJ_MATT', 'inget mätkvitto (--matning ur verktyg/kor_profil.py matning)')
    if isinstance(m, dict) and m.get('ofullstandig'):
        return grind('2 prestanda', 'EJ_MATT', 'mätningen är inte klar (outcome %s): inga poäng räknas' % m['ofullstandig'])
    lh = hitta(m, 'lighthouse', 'lighthouse_scores', 'poang')
    if not isinstance(lh, dict):
        return grind('2 prestanda', 'EJ_MATT', 'mätkvittot saknar Lighthouse-poäng')
    # per vy ({mobil: {scores, lcp_ms, cls}, desktop: {...}}) eller platt
    vyer = {k: v for k, v in lh.items() if isinstance(v, dict) and ('scores' in v or 'performance' in v)} or {'': lh}
    def sc(d, k):
        src = d.get('scores') if isinstance(d.get('scores'), dict) else d
        v = src.get(k) if k in src else src.get(k.replace('_', '-'))
        return v * 100 if isinstance(v, (int, float)) and v <= 1 else v
    poang = {}; lcp = None; cls = None; brister = []
    for vy, d in vyer.items():
        for k in ('performance', 'accessibility', 'best_practices', 'seo'):
            v = sc(d, k)
            if v is not None:
                poang[(vy + ' ' if vy else '') + k] = v
                if v < krav[k] and not (k == 'seo' and lage == 'forhandsvisning'):
                    brister.append((vy + ' ' if vy else '') + k)
        l = d.get('lcp_ms') if 'lcp_ms' in d else hitta(d, 'lcp_ms', 'largest-contentful-paint', 'lcp'); c = d.get('cls') if 'cls' in d else hitta(d, 'cls', 'cumulative-layout-shift')
        if isinstance(l, (int, float)):
            lcp = max(lcp or 0, l)
            if l > krav['lcp_ms']:
                brister.append((vy + ' ' if vy else '') + 'lcp')
        if isinstance(c, (int, float)):
            cls = max(cls or 0, c)
            if c > krav['cls']:
                brister.append((vy + ' ' if vy else '') + 'cls')
    belagg = 'Lighthouse %s; LCP (sämsta vy) %s ms; CLS (sämsta vy) %s; INP: mäts inte av navigations-Lighthouse (EJ_MATT, fältdata krävs)%s' % (poang, lcp, cls, '; SEO-poängen avgör inte i förhandsvisning (noindex)' if lage == 'forhandsvisning' else '')
    if not poang:
        return grind('2 prestanda', 'EJ_MATT', belagg)
    return grind('2 prestanda', 'FAIL' if brister else 'PASS', belagg, ('under kravnivå: ' + ', '.join(brister)) if brister else None)


def g3_responsivitet(m, inspektion=None):
    """Vyerna ur mätkvittot; spill ur webbläsarverktygets INSPEKTION.json (--inspektion) eller ur ett kvitto som bär det."""
    if not m and not inspektion:
        return grind('3 responsivitet', 'EJ_MATT', 'inget mätkvitto och ingen inspektion')
    if isinstance(m, dict) and m.get('ofullstandig') and not inspektion:
        return grind('3 responsivitet', 'EJ_MATT', 'mätningen är inte klar (outcome %s) och ingen inspektion' % m['ofullstandig'])
    vyer = hitta(m, 'vyer', 'viewports') if m else None
    spill = hitta(m, 'horisontell_spill', 'horizontal_overflow', 'overflow') if m else None
    if inspektion:
        spill = {vy: v['spill'] for vy, v in inspektion.items()}
        vyer = vyer or list(inspektion.keys())
    if vyer is None:
        return grind('3 responsivitet', 'EJ_MATT', 'mätkvittot saknar vyer')
    belagg = 'vyer: %s; horisontell spill: %s' % (list(vyer) if isinstance(vyer, (list, dict)) else vyer, spill)
    if spill is None:
        return grind('3 responsivitet', 'EJ_MATT', belagg + '; spill inte rapporterat — ge --inspektion INSPEKTION.json (verktyg/webblasare/inspektera.mjs, vyer 390/768/1440)')
    dalig = any(spill.values()) if isinstance(spill, dict) else (spill if isinstance(spill, bool) else bool(spill))
    return grind('3 responsivitet', 'FAIL' if dalig else 'PASS', belagg + ('; layoutvyns bredd = fönstret i varje vy (inspektionen)' if inspektion else ''))


def g4_tillganglighet(m):
    if not m:
        return grind('4 tillgänglighet', 'EJ_MATT', 'inget mätkvitto (axe)')
    if isinstance(m, dict) and m.get('ofullstandig'):
        return grind('4 tillgänglighet', 'EJ_MATT', 'mätningen är inte klar (outcome %s): axe räknas inte' % m['ofullstandig'])
    views = (m.get('sammanfattning') or {}).get('views') if isinstance(m, dict) else None
    if isinstance(views, dict) and views:
        # per vy ur Runtimes sammanfattning: summan av violations avgör; incomplete redovisas (lista eller antal)
        def antal_av(x):
            return len(x) if isinstance(x, list) else (x if isinstance(x, int) else 0)
        per = {vy: antal_av(((v.get('axe') or {}).get('violations'))) for vy, v in views.items()}
        inc = sorted({str(x) for v in views.values() for x in (((v.get('axe') or {}).get('incomplete')) if isinstance((v.get('axe') or {}).get('incomplete'), list) else [])})
        antal = sum(per.values())
        belagg = 'axe violations per vy: %s; incomplete (manuell kontroll): %s; manuellt återstår alltid: tangentbord, fokus, kontrast, alt-texter, formulärfel, rörelse' % (per, inc or 'inga')
        return grind('4 tillgänglighet', 'PASS' if antal == 0 else 'FAIL', belagg, None if antal == 0 else 'rätta violations och mät om')
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
    grindar = [g0_bygg(a.bygge, a.repo), g1_handlingar(a.handlingar, a.bygge), g2_prestanda(m, krav, a.lage), g3_responsivitet(m, las_inspektion(a.inspektion)), g4_tillganglighet(m), g5_seo(a.bygge, a.lage, a.verksamhet), g6_juridik(a.juridik), g7_sakerhet(a.huvuden, a.adress, a.audit, a.bygge)]
    tekniska = [g for g in grindar if not g['grind'].startswith('6')]
    juridik_lamnad = bool(a.juridik and Path(a.juridik).is_file())
    ohanterade = (grindar[6]['atgard'] or '').startswith('människa avgör varje flagga; ohanterade:')
    redo = all(g['status'] == 'PASS' for g in tekniska) and juridik_lamnad and not ohanterade
    return {'schema': 1, 'bygge': a.bygge, 'lage': a.lage, 'krav': krav, 'grindar': grindar, 'redo_for_lansering': bool(redo),
            'juridik_lamnad': juridik_lamnad,
            'not': 'redo = grind 0–5 och 7 PASS, JURIDIK.json lämnad (människans genomgång av basen och flaggorna) och inga ohanterade flaggor; juridik avgörs av människa; EJ_MATT är inte PASS; gröna verktygsprov bevisar inte mänsklig användbarhet'}


def markdown(r):
    lines = ['# Prelaunch — %s (läge %s) — %s' % (r['bygge'], r['lage'], 'REDO för lansering enligt grindarna' if r['redo_for_lansering'] else 'INTE redo'), '', '| Grind | Status | Belägg | Åtgärd |', '|---|---|---|---|']
    for g in r['grindar']:
        lines.append('| %s | %s | %s | %s |' % (g['grind'], g['status'], str(g['belagg']).replace('|', '/'), str(g['atgard'] or '').replace('|', '/')))
    return '\n'.join(lines) + '\n\n' + r['not'] + '\n'


def main(argv=None):
    p = argparse.ArgumentParser(prog='prelaunch', description=__doc__.split('\n\n')[0])
    p.add_argument('--bygge', required=True); p.add_argument('--lage', required=True, choices=('forhandsvisning', 'lansering')); p.add_argument('--repo'); p.add_argument('--verksamhet')
    p.add_argument('--matning'); p.add_argument('--inspektion', help='INSPEKTION.json från verktyg/webblasare/inspektera.mjs (spill per vy)'); p.add_argument('--handlingar'); p.add_argument('--juridik'); p.add_argument('--huvuden'); p.add_argument('--adress'); p.add_argument('--audit'); p.add_argument('--krav')
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
