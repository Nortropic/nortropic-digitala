"""Samlar ett falls körningar till kvalitetsbilden: tekniskt prövat · professionellt bedömt · ej observerat.

    python3 -B verktyg/kvalitetsbild.py --fall FALL --ut FIL.md [--leverans NYCKEL=VÄRDE ...] [--ej-observerat TEXT ...] [--json]

Beviskedjans fynd C: varje KORNING-post får en bevisstatus och visas — korrupt (oläsbar), saknas (körkatalog eller
kvitto borta), kvittohash (KVITTO.sha256 stämmer inte), inaktuell (laddningskvittot har ändrats sedan körningen),
underkänd (utfallet är inte klar/svar_giltigt), oavgjord (en provarkörning utan kontrollantens bedömning) eller utanför
leveransen (bindningen skiljer sig från --leverans).
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
import kritikbevis
import hashlib

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
    values=line.read_text().split()
    if len(values)!=2 or values[1]!='KVITTO.json':return False
    expected = values[0]
    return hashlib.sha256((Path(run) / 'KVITTO.json').read_bytes()).hexdigest() == expected


def bevisstatus(post, entry, leverans):
    """En status per körning; den första bristen vinner. ok betyder: läsbar, kvitto funnet och hashat, laddning oförändrad,
    utfall klar/svar_giltigt, och bindningen lika med --leverans."""
    run = entry.get('run')
    if not run or not Path(run).is_dir():
        return 'saknas: körkatalogen finns inte'
    if entry.get('kvitto') is None:
        return 'saknas: KVITTO.json saknas eller är oläsbart'
    if kvittohash_ok(run) is None:
        return 'saknas: KVITTO.sha256 integritetsrad krävs för aktuellt bevis'
    if kvittohash_ok(run) is False:
        return 'kvittohash: KVITTO.sha256 stämmer inte med KVITTO.json'
    if post.get('runtime_kvitto_sha256') != hashlib.sha256((Path(run)/'KVITTO.json').read_bytes()).hexdigest():
        return 'oavgjord: Runtime-kvittots hash saknas/avviker i körningens bindning'
    if not post.get('profil') or post['profil'] != entry['kvitto'].get('profile'):
        return 'ogiltig bindning: profil skiljer från Runtime-kvittots profile'
    ladd = (post.get('laddning') or {})
    fil = ladd.get('fil')
    if fil and Path(fil).is_file():
        if hashlib.sha256(Path(fil).read_bytes()).hexdigest() != ladd.get('sha256'):
            return 'inaktuell: laddningskvittot har ändrats sedan körningen'
    elif fil:
        return 'inaktuell: laddningskvittot finns inte längre'
    if entry.get('utfall') not in ('klar', 'svar_giltigt'):
        return 'underkänd: utfall %s' % entry.get('utfall')
    if post.get('profil')=='kritik' and post.get('mall')=='femsekunderstest':
        return 'begriplighetsprov: avskärmat femsekunderstest, ingen kvalitetsdom'
    if post.get('profil') == 'kritik':
        if not post.get('bedomningsbindning') or not post.get('bildbedomningsunderlag'):
            return 'oavgjord: historisk kritik saknar kandidat- och bildbindning enligt v2'
        try:
            expected,underlag=kritikbevis.ur_laddning(fil)
            if expected!=post['bedomningsbindning'] or underlag!=post['bildbedomningsunderlag']:
                return 'ogiltig bindning: körningens kopior skiljer från faktiskt laddat manifest'
            runtime_rows={r['place']:r for r in entry['kvitto'].get('underlag',[])}
            for b in underlag['bilder']:
                row=runtime_rows.get(b['plats'],{})
                if row.get('copy_sha256')!=b['sha256'] or row.get('source_sha256')!=b['sha256']:
                    return 'ogiltig bindning: Runtime-bildens hash skiljer från laddningen'
            for output in ('svar.json','strom.jsonl','start.json'):
                actual=Path(run)/output
                if not actual.is_file() or entry['kvitto'].get('outputs',{}).get(output,{}).get('sha256')!=kritikbevis.stegbevis.sha(actual):
                    return 'kvittohash: '+output+' saknas/skiljer från Runtime-kvittot'
            result = kritikbevis.dom(entry.get('svar'), expected, underlag, entry['kvitto'])
            entry['bildbelagg']=kritikbevis.bildbelagg(entry['kvitto'])
        except (kritikbevis.Vagrad,kritikbevis.stegbevis.Vagrad,OSError,KeyError,TypeError,ValueError) as e:
            return 'inaktuell/ogiltig beviskedja: '+str(e)
        if result != 'ok':
            return result
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
        entry = {'fil': path.name, 'mall':post.get('mall'), 'profil': post.get('profil'), 'etikett': post.get('etikett'), 'run': run,
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
    # Playwright-vägens besökarprov (verktyg/webblasare/besok.mjs): FALL/BESOK-*/BESOK.json med efterkontroll av
    # nätverksloggen; kontrollantens bedömning i FALL/KONTROLL-<namn>.json/.md (fynd ur slutprovet HELHET-20260927:
    # ett verkligt besök syntes inte i kvalitetsbilden eftersom det inte är en KORNING-post)
    for d in sorted(fall.glob('BESOK-*')):
        post = las_json(d / 'BESOK.json')
        if not isinstance(post, dict):
            continue
        kontroller = []
        for k in sorted(fall.glob('KONTROLL-*.json')):
            kj = las_json(k)
            if isinstance(kj, dict) and isinstance(kj.get('korning'), str) and str(d) in kj['korning']:
                kontroller.append(k)
        kontroll = las_json(kontroller[0]) if kontroller else None
        kontroll_fil = kontroller[0].name if kontroller else None
        if post.get('torr') or post.get('lage') == 'qa':
            status = 'utanför leveransen: torrläge eller QA-konfiguration, inget besök'
        elif leverans:
            status = 'oavgjord: besöket bär ingen leveransbindning (adress %s); bind besöket till revisionen i kontrollantens kvitto innan det räknas som leveransbevis' % post.get('adress')
        elif post.get('utforare_status') not in (0, None) or post.get('inom_gransen') is not True:
            status = 'underkänd: utföraren slutade med status %s eller ursprung utanför gränsen' % post.get('utforare_status')
        elif not kontroll:
            status = 'oavgjord: KONTROLL SAKNAS — kontrollantens bedömning finns inte; provarens rapport räknas inte'
        else:
            status = 'ok' if str(kontroll.get('utfall', '')).lower().startswith(('godk', 'lyck')) else 'underkänd: kontrollanten bedömde %s' % kontroll.get('utfall')
        rows.append({'fil': d.name + '/BESOK.json', 'profil': 'provare', 'vag': 'playwright', 'etikett': d.name, 'run': str(d), 'laddning': None, 'steg': 'provare',
                     'exit': post.get('utforare_status'), 'kvitto': None, 'utfall': (post.get('besok') or {}).get('utfall') or 'okänt', 'kontroll': kontroll, 'kontroll_fil': kontroll_fil,
                     'efterkontroll': post.get('efterkontroll'), 'utforare': '%s/%s' % (post.get('utforare'), post.get('modell')), 'bindning': {'adress': post.get('adress')}, 'status': status})
    return rows


def rendera(rows, ej_observerat, leverans=None):
    alla_rader=rows
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
    out += ['', 'Aktuella leveransbevis: %d. Historik eller utanför kvalitetsgrinden: %d.' % (len(aktuella), len(brister)), '']
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
        if r.get('vag') == 'playwright':
            e = r.get('efterkontroll') or {}
            out.append('- Playwright-vägen (besok.mjs, %s): besökarens utfall "%s"; efterkontroll: %s förfrågningar, %s blockerade, inom gränsen %s' % (r.get('utforare'), r.get('utfall'), e.get('antal_forfragningar'), e.get('blockerade'), e.get('inom_gransen')))
        if r['profil'] == 'provare':
            out.append('- kontrollantens bedömning: ' + ('finns (%s)' % (r.get('kontroll_fil') or 'KONTROLL-%s.md' % r['etikett']) if r.get('kontroll') else 'KONTROLL SAKNAS — utfallet är inte avgjort; provarens rapport räknas inte'))
        out.append('')
    out += ['## 2. Professionellt bedömt (modellbedömning, märkt som sådan)', '']
    bedomt = [r for r in alla_rader if r['profil'] == 'kritik']
    if not bedomt:
        out.append('Ingen kritik- eller läsarsession i fallet: ej bedömt.')
    for r in bedomt:
        out.append('### kritik — %s (%s)' % (r['etikett'], r.get('utfall') or 'okänt'))
        out.append('Bevisstatus: '+r['status']+'. Bildbelägg: '+str(r.get('bildbelagg') or 'ej verifierat')+'.')
        if r.get('mall')=='femsekunderstest':out.append('Avskärmat begriplighetsprov; ingen professionell kvalitetsdom och ingen täckning av kvalitetsgrinden.')
        elif r.get('status')=='ok':out.append('Godkänd leveransbedömning inom den angivna räckvidden.')
        out.append('Körkatalog: `%s`; laddning %s (steg %s); bilder kompletta: %s.' % (
            r['run'] or 'ingen', (r['laddning'] or '')[:16], r['steg'], ((r.get('kvitto') or {}).get('images') or {}).get('complete', 'okänt')))
        svar = r.get('svar')
        if isinstance(svar, dict):
            for key in ('verdict', 'omdome_en_mening', 'summary', 'specificitet', 'vad', 'hur'):
                if key in svar:
                    out.append('- %s: %s' % (key, json.dumps(svar[key], ensure_ascii=False)[:400]))
            if isinstance(svar.get('blocking_findings'), list):
                out.append('- blockerande fynd: %d' % len(svar['blocking_findings']))
                for finding in svar['blocking_findings']:out.append('  - '+json.dumps(finding,ensure_ascii=False))
            for missing in svar.get('could_not_review',[]):out.append('- ej bedömbart: '+str(missing))
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
