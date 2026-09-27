"""Samlar ett falls körningar till kvalitetsbilden: tekniskt prövat · professionellt bedömt · ej observerat.

    python3 -B verktyg/kvalitetsbild.py --fall FALL --ut FIL.md [--leverans NYCKEL=VÄRDE ...] [--ej-observerat TEXT ...] [--json]

Beviskedjans fynd C: varje KORNING-post får en bevisstatus och visas — korrupt (oläsbar), saknas (körkatalog eller
kvitto borta), kvittohash (KVITTO.sha256 stämmer inte), inaktuell (laddningskvittot har ändrats sedan körningen),
underkänd (utfallet är inte klar/svar_giltigt) eller utanför leveransen (bindningen skiljer sig från --leverans).
Bara körningar med status ok och inom leveransen räknas som aktuella leveransbevis; övriga listas som historik eller
brist och döljs aldrig. --leverans binder rapporten till leveransens revision, driftsättning och konfiguration:
varje aktuell körning måste bära samma värden i sin bindning (kor_profil --bindning). Täckningen redovisas per profil.

Läser FALL/KORNING-*.json (skrivna av kor_profil.py), följer varje körkatalog till KVITTO.json och, för mätning,
SAMMANFATTNING.json; för kritik svar.json; för provare FALL/KONTROLL-<etikett>.md om den finns. Det som saknas står
som "ej prövat" eller "kontroll saknas" och fylls aldrig i. Verktyget bedömer ingenting.
"""
import argparse
import json
from pathlib import Path
import sys
import time

STANDARD_EJ_OBSERVERAT = ('verkliga besökares beteende och konvertering', 'kundens eller mottagarens omdöme',
                          'läsbarhet utomhus i verkligheten', 'mänskliga användarprov', 'fältdata över tid')


def las_json(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def kvittohash_ok(run):
    """KVITTO.sha256 (skriven av Runtime) stämmer med KVITTO.json; None om filen saknas."""
    line = Path(run) / 'KVITTO.sha256'
    if not line.is_file() or not (Path(run) / 'KVITTO.json').is_file():
        return None
    import hashlib
    expected = line.read_text().split()[0]
    return hashlib.sha256((Path(run) / 'KVITTO.json').read_bytes()).hexdigest() == expected


def bevisstatus(post, entry, leverans):
    """En status per körning; den första bristen vinner. ok betyder: läsbar, kvitto funnet och hashat, laddning oförändrad,
    utfall klar/svar_giltigt, och bindningen lika med --leverans."""
    run = entry.get('run')
    if not run or not Path(run).is_dir():
        return 'saknas: körkatalogen finns inte'
    if entry.get('kvitto') is None:
        return 'saknas: KVITTO.json saknas eller är oläsbart'
    if kvittohash_ok(run) is False:
        return 'kvittohash: KVITTO.sha256 stämmer inte med KVITTO.json'
    ladd = (post.get('laddning') or {})
    fil = ladd.get('fil')
    if fil and Path(fil).is_file():
        import hashlib
        if hashlib.sha256(Path(fil).read_bytes()).hexdigest() != ladd.get('sha256'):
            return 'inaktuell: laddningskvittot har ändrats sedan körningen'
    elif fil:
        return 'inaktuell: laddningskvittot finns inte längre'
    if entry.get('utfall') not in ('klar', 'svar_giltigt'):
        return 'underkänd: utfall %s' % entry.get('utfall')
    if post.get('profil') == 'provare' and not entry.get('kontroll'):
        return 'oavgjord: KONTROLL SAKNAS — kontrollantens bedömning finns inte; provarens rapport räknas inte'
    if leverans:
        bind = post.get('bindning') or {}
        for key, value in leverans.items():
            if str(bind.get(key)) != value:
                return 'utanför leveransen: %s=%s (leveransen %s)' % (key, bind.get(key), value)
    return 'ok'


def samla(fall, leverans=None):
    fall = Path(fall)
    rows = []
    for path in sorted(fall.glob('KORNING-*.json')):
        post = las_json(path)
        if not isinstance(post, dict):
            rows.append({'fil': path.name, 'profil': None, 'etikett': None, 'run': None, 'laddning': None, 'steg': None, 'exit': None, 'kvitto': None,
                         'utfall': 'oläsbar', 'status': 'korrupt: posten går inte att läsa som JSON'})
            continue
        run = (post.get('resultat') or {}).get('run')
        entry = {'fil': path.name, 'profil': post.get('profil'), 'etikett': post.get('etikett'), 'run': run,
                 'laddning': (post.get('laddning') or {}).get('sha256'), 'steg': (post.get('laddning') or {}).get('steg'),
                 'exit': post.get('exit'), 'kvitto': None}
        if run:
            kvitto = las_json(Path(run) / 'KVITTO.json')
            entry['kvitto'] = kvitto
            entry['utfall'] = (kvitto or {}).get('outcome') or (post.get('resultat') or {}).get('outcome')
            if post.get('profil') == 'matning':
                entry['sammanfattning'] = las_json(Path(run) / 'SAMMANFATTNING.json')
            if post.get('profil') == 'kritik':
                entry['svar'] = las_json(Path(run) / 'svar.json')
        else:
            entry['utfall'] = (post.get('resultat') or {}).get('outcome') or 'okänt'
        if post.get('profil') == 'provare':
            kontroll = fall / ('KONTROLL-%s.md' % post.get('etikett'))
            entry['kontroll'] = kontroll.read_text(encoding='utf-8') if kontroll.is_file() else None
        entry['bindning'] = post.get('bindning')
        entry['status'] = bevisstatus(post, entry, leverans)
        rows.append(entry)
    return rows


def rendera(rows, ej_observerat, leverans=None):
    out = ['# Kvalitetsbild', '', 'Skapad %s ur fallets körningar. Tre kolumner som aldrig blandas (KVALITET.md).' % time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime()), '']
    if leverans:
        out += ['Bunden till leveransen: ' + ', '.join('%s=%s' % kv for kv in sorted(leverans.items())) + '.', '']
    else:
        out += ['INTE bunden till någon leverans (ingen --leverans): bilden är en ögonblicksbild av fallets körningar, inte ett leveransbevis.', '']
    out += ['## 0. Bevisstatus (varje körning visas; ingen döljs)', '']
    for r in rows:
        out.append('- `%s` — %s %s: %s' % (r['fil'], r.get('profil') or '?', r.get('etikett') or '?', r['status']))
    aktuella = [r for r in rows if r['status'] == 'ok']
    brister = [r for r in rows if r['status'] != 'ok']
    out += ['', 'Aktuella leveransbevis: %d. Historik eller brist: %d.' % (len(aktuella), len(brister)), '']
    out += ['## Täckning (aktuella körningar per profil)', '']
    for profil in ('matning', 'kritik', 'provare'):
        n = sum(1 for r in aktuella if r['profil'] == profil)
        out.append('- %s: %s' % (profil, ('%d körning(ar)' % n) if n else 'INGEN aktuell körning — ej prövat'))
    out.append('')
    rows = aktuella
    out += ['## 1. Tekniskt prövat (uppmätt)', '']
    tekniskt = [r for r in rows if r['profil'] in ('matning', 'provare')]
    if not tekniskt:
        out.append('Ingen mätning eller scenariokörning i fallet: ej prövat.')
    for r in tekniskt:
        out.append('### %s — %s (%s)' % (r['profil'], r['etikett'], r.get('utfall') or 'okänt'))
        out.append('Körkatalog: `%s`; laddning %s (steg %s).' % (r['run'] or 'ingen', (r['laddning'] or '')[:16], r['steg']))
        s = r.get('sammanfattning')
        if r['profil'] == 'matning' and isinstance(s, dict):
            for name, view in (s.get('views') or {}).items():
                axe = view.get('axe') or {}
                det = view.get('detector') or {}
                h1 = view.get('h1') or []
                out.append('- %s: status %s; axe violations %s, incomplete %s; h1-rader %s; handling i vyn %s; detektor %s (%s)' % (
                    name, view.get('status'), len(axe.get('violations', [])) if axe else 'ej mätt',
                    len(axe.get('incomplete', [])) if axe else 'ej mätt', [h.get('lines') for h in h1] or 'ej mätt',
                    (view.get('action') or {}).get('fully_in_first_view', 'ej mätt'), det.get('findings', 'ej mätt'), det.get('meaning', '')))
            lh = s.get('lighthouse') or {}
            for form, value in lh.items():
                scores = value.get('scores') if isinstance(value, dict) else None
                out.append('- Lighthouse %s: %s' % (form, json.dumps(scores or value, ensure_ascii=False)[:300]))
        elif r['profil'] == 'matning':
            out.append('- sammanfattning saknas: ej prövat')
        if r['profil'] == 'provare':
            out.append('- kontrollantens bedömning: ' + ('finns (KONTROLL-%s.md)' % r['etikett'] if r.get('kontroll') else 'KONTROLL SAKNAS — utfallet är inte avgjort; provarens rapport räknas inte'))
        out.append('')
    out += ['## 2. Professionellt bedömt (modellbedömning, märkt som sådan)', '']
    bedomt = [r for r in rows if r['profil'] == 'kritik']
    if not bedomt:
        out.append('Ingen kritik- eller läsarsession i fallet: ej bedömt.')
    for r in bedomt:
        out.append('### kritik — %s (%s)' % (r['etikett'], r.get('utfall') or 'okänt'))
        out.append('Körkatalog: `%s`; laddning %s (steg %s); bilder kompletta: %s.' % (
            r['run'] or 'ingen', (r['laddning'] or '')[:16], r['steg'], ((r.get('kvitto') or {}).get('images') or {}).get('complete', 'okänt')))
        svar = r.get('svar')
        if isinstance(svar, dict):
            for key in ('verdict', 'omdome_en_mening', 'summary', 'specificitet', 'vad', 'hur'):
                if key in svar:
                    out.append('- %s: %s' % (key, json.dumps(svar[key], ensure_ascii=False)[:400]))
            if isinstance(svar.get('blocking_findings'), list):
                out.append('- blockerande fynd: %d' % len(svar['blocking_findings']))
        else:
            out.append('- inget giltigt svar: ej bedömt')
        out.append('')
    out += ['## 3. Ej observerat hos verkliga användare', '']
    for item in list(STANDARD_EJ_OBSERVERAT) + list(ej_observerat or []):
        out.append('- ' + item)
    out += ['', 'Regel: gröna prov ersätter inte visuell bedömning; en modellbedömning är inte ett mänskligt prov; granskare av samma modellfamilj som byggaren ger en separat läsning, inte ett oberoende omdöme.', '']
    return '\n'.join(out)


def main(argv=None):
    parser = argparse.ArgumentParser(prog='kvalitetsbild', description=__doc__.split('\n\n')[0])
    parser.add_argument('--fall', required=True)
    parser.add_argument('--ut', required=True)
    parser.add_argument('--ej-observerat', action='append')
    parser.add_argument('--leverans', action='append', help='NYCKEL=VÄRDE som varje aktuell körning måste bära i sin bindning (t.ex. revision=abc123 driftsattning=dpl)')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    if not Path(args.fall).is_dir():
        print(json.dumps({'utfall': 'vagrad', 'skal': 'fallmappen finns inte'}))
        return 2
    leverans = {}
    for item in args.leverans or []:
        if '=' not in item:
            print(json.dumps({'utfall': 'vagrad', 'skal': '--leverans är NYCKEL=VÄRDE: ' + item}))
            return 2
        key, value = item.split('=', 1)
        leverans[key] = value
    rows = samla(args.fall, leverans)
    text = rendera(rows, args.ej_observerat, leverans)
    with Path(args.ut).open('x', encoding='utf-8') as stream:
        stream.write(text)
    if args.json:
        print(json.dumps({'korningar': len(rows), 'aktuella': sum(1 for r in rows if r['status'] == 'ok'), 'ut': args.ut, 'rader': [{k: r.get(k) for k in ('fil', 'profil', 'etikett', 'utfall', 'status', 'run')} for r in rows]}, ensure_ascii=False, indent=1))
    else:
        print(json.dumps({'korningar': len(rows), 'aktuella': sum(1 for r in rows if r['status'] == 'ok'), 'ut': args.ut}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
