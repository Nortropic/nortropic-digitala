"""Samlar ett falls körningar till kvalitetsbilden: tekniskt prövat · professionellt bedömt · ej observerat.

    python3 -B verktyg/kvalitetsbild.py --fall FALL --ut FIL.md [--ej-observerat TEXT ...] [--json]

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


def samla(fall):
    fall = Path(fall)
    rows = []
    for path in sorted(fall.glob('KORNING-*.json')):
        post = las_json(path)
        if not isinstance(post, dict):
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
        rows.append(entry)
    return rows


def rendera(rows, ej_observerat):
    out = ['# Kvalitetsbild', '', 'Skapad %s ur fallets körningar. Tre kolumner som aldrig blandas (KVALITET.md).' % time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime()), '']
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
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    if not Path(args.fall).is_dir():
        print(json.dumps({'utfall': 'vagrad', 'skal': 'fallmappen finns inte'}))
        return 2
    rows = samla(args.fall)
    text = rendera(rows, args.ej_observerat)
    with Path(args.ut).open('x', encoding='utf-8') as stream:
        stream.write(text)
    if args.json:
        print(json.dumps({'korningar': len(rows), 'ut': args.ut, 'rader': [{k: r.get(k) for k in ('profil', 'etikett', 'utfall', 'run')} for r in rows]}, ensure_ascii=False, indent=1))
    else:
        print(json.dumps({'korningar': len(rows), 'ut': args.ut}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
