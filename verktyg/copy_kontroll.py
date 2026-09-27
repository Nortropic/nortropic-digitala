#!/usr/bin/env python3
"""Copykontroll: en rapport över fraser, strukturer, platshållare, metalängder och saknade obligatoriska element i
levererad text. Ingen poäng, ingen stil: fynden är att läsa, rätta eller motivera i det redaktionella passet
(kunskap/copy-kontroll.md). Bransch- och kundspecifika fraser kommer från briefen (--fraser), obligatoriska element
från verksamhetsuppgifterna (--krav ur verktyg/verksamhetsuppgifter.py krav), inte från en inbyggd branschmall.

    python3 -B verktyg/copy_kontroll.py --kalla KATALOG|FIL [...] [--fraser FIL] [--krav KRAV.json] --ut RAPPORT.json [--md RAPPORT.md]

Exit 0 när rapporten är skriven; fynd ändrar aldrig exitkoden (rapporten är ingen grind). Läser .html/.htm/.md/.mdx/.txt/.tsx/.jsx/.ts/.js/.astro/.vue/.svelte.
"""
import argparse
import html
import json
import re
import sys
from pathlib import Path

SUFFIX = {'.html', '.htm', '.md', '.mdx', '.txt', '.tsx', '.jsx', '.ts', '.js', '.astro', '.vue', '.svelte'}
HOPPA = {'node_modules', '.next', '.git', 'dist', 'build', '.vercel', 'out', '.scratch'}
FRASER_SV = [
    ('vi förstår att', 'empatiteater; säg vad som görs i stället'),
    ('i dagens digitala värld', 'utfyllnad; stryk meningen'),
    ('i dagens digitala samhälle', 'utfyllnad; stryk meningen'),
    ('oavsett om du', 'gardering; namnge tjänsterna var för sig'),
    ('vi finns här för dig', 'säger inget; skriv när och hur man når er'),
    ('skräddarsydda lösningar', 'byråspråk; namnge vad som faktiskt anpassas'),
    ('helhetslösningar', 'vagt; lista vad som ingår'),
    ('till nästa nivå', 'utfyllnad; stryk'),
    ('vi brinner för', 'kliché; visa det med år, utbildning, bilder'),
    ('kvalitet i fokus', 'tomt påstående; ersätt med garanti eller certifikat'),
    ('kunden i centrum', 'tomt påstående; ersätt med något konkret'),
    ('marknadsledande', 'obevisbart superlativ; verkliga belägg eller stryk'),
    ('bäst i branschen', 'obevisbart superlativ; verkliga belägg eller stryk'),
    ('snabbt, smidigt och säkert', 'tretalsutfyllnad; ett konkret löfte'),
    ('kontakta oss redan idag', 'påstridig mallavslutning; konkret väg och tid'),
    ('din trygghet är vår prioritet', 'empatiutfyllnad; konkret garanti eller försäkring'),
]
FRASER_EN = ['unlock', 'elevate', 'seamless', 'empower', 'effortless', 'state-of-the-art', 'cutting-edge', 'world-class',
             'look no further', "we've got you covered", 'one-stop shop']
PLATSHALLARE = ['lorem ipsum', 'todo-fact', 'todo-copy', '[osäker]', 'platshållare', 'placeholder']
TAGG = re.compile(r'<[^>]+>')
JSX = re.compile(r'\{[^{}]*\}')
SCRIPT = re.compile(r'<(script|style)\b.*?</\1>', re.S | re.I)
TITLE = re.compile(r'<title[^>]*>(.*?)</title>', re.S | re.I)
META_DESC = re.compile(r'<meta\s+[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']', re.I)
META_DESC2 = re.compile(r'<meta\s+[^>]*content=["\']([^"\']*)["\'][^>]*name=["\']description["\']', re.I)


def synlig_text(path, raw):
    """Textrader med radnummer. HTML/JSX: taggar, script/style och JSX-uttryck bort; Markdown/text: som de är."""
    if path.suffix in ('.html', '.htm'):
        raw = SCRIPT.sub(lambda m: '\n' * m.group(0).count('\n'), raw)
    rows = []
    for i, line in enumerate(raw.split('\n'), 1):
        segs = [line]
        if path.suffix in ('.html', '.htm', '.tsx', '.jsx', '.astro', '.vue', '.svelte'):
            t = TAGG.sub('\n', line)
            if path.suffix in ('.tsx', '.jsx', '.astro', '.vue', '.svelte'):
                t = JSX.sub('\n', t)
            segs = t.split('\n')  # varje element blir ett eget stycke, med radens nummer
        elif path.suffix in ('.ts', '.js'):
            segs = [s[1] for s in re.findall(r'''(["'`])((?:(?!\1)[^\\]|\\.){4,})\1''', line)]
        for seg in segs:
            t = html.unescape(seg).strip()
            if t:
                rows.append((i, t))
    return rows


def samla_filer(kallor):
    for k in kallor:
        p = Path(k)
        if p.is_file():
            yield p
        elif p.is_dir():
            for f in sorted(p.rglob('*')):
                if f.is_file() and f.suffix.lower() in SUFFIX and not (set(f.parts) & HOPPA):
                    yield f


def kontrollera_fil(path, raw, extra_fraser):
    fynd = []
    rows = synlig_text(path, raw)
    lower_rows = [(i, t.lower()) for i, t in rows]
    for i, t in lower_rows:
        for fras, riktning in FRASER_SV + [(f, 'kund-/branschfras ur briefen') for f in extra_fraser]:
            if fras.lower() in t:
                fynd.append({'typ': 'fras', 'rad': i, 'text': fras, 'riktning': riktning})
        for w in FRASER_EN:
            if re.search(r'(?<![a-z])' + re.escape(w) + r'(?![a-z])', t):
                fynd.append({'typ': 'engelskt läckage', 'rad': i, 'text': w, 'riktning': 'svensk sajt; skriv på svenska utan lånad marknadsföringsjargong'})
        for ph in PLATSHALLARE:
            if ph in t:
                fynd.append({'typ': 'platshållare', 'rad': i, 'text': ph, 'riktning': 'levererad text får inte bära platshållare eller osäkra fakta'})
        if t.startswith('välkommen till'):
            fynd.append({'typ': 'hälsningsrubrik', 'rad': i, 'text': t[:60], 'riktning': 'första vyn säger vad som erbjuds och för vem, inte en hälsning'})
    for i, t in rows:
        if t.count('—') >= 2 or t.count(' – ') >= 2:
            fynd.append({'typ': 'tankstreckskedja', 'rad': i, 'text': t[:80], 'riktning': 'högst ett tankstreck per stycke; variera konstruktionen'})
    utrop = sum(t.count('!') for _, t in rows)
    if utrop > 1:
        fynd.append({'typ': 'utropstecken', 'rad': 0, 'text': '%d utropstecken' % utrop, 'riktning': 'högst ett per sida, helst inget'})
    stycken = [(i, t) for i, t in rows if len(t) >= 40]
    run = 0
    for i, t in stycken:
        run = run + 1 if t.startswith('Vi ') else 0
        if run == 3:
            fynd.append({'typ': 'spegelöppningar', 'rad': i, 'text': 'tre stycken i rad börjar med "Vi"', 'riktning': 'variera subjektet; skriv om besökaren och uppgiften'})
    if path.suffix in ('.html', '.htm'):
        m = TITLE.search(raw)
        if m:
            title = html.unescape(TAGG.sub('', m.group(1))).strip()
            if len(title) > 60:
                fynd.append({'typ': 'metalängd', 'rad': raw[:m.start()].count('\n') + 1, 'text': 'title %d tecken' % len(title), 'riktning': 'title ≤ 60 tecken; sanningsenlig, utan superlativ'})
        m = META_DESC.search(raw) or META_DESC2.search(raw)
        if m and len(html.unescape(m.group(1))) > 155:
            fynd.append({'typ': 'metalängd', 'rad': raw[:m.start()].count('\n') + 1, 'text': 'description %d tecken' % len(m.group(1)), 'riktning': 'description ≤ 155 tecken'})
    return fynd, rows


def kontrollera_krav(krav, texter):
    """Obligatoriska element: 'varje sida' kräver träff i varje fil; 'nagon sida' minst en fil. Sidor = .html/.md/.tsx-filer."""
    fynd = []
    for k in krav or []:
        rx = re.compile(k['regex'], re.I)
        traff = {str(p): bool(rx.search(text)) for p, text in texter.items()}
        if k.get('var') == 'varje sida':
            for p, ok in traff.items():
                if not ok:
                    fynd.append({'fil': p, 'typ': 'saknat element', 'rad': 0, 'text': k['namn'], 'riktning': k.get('skal', '')})
        elif not any(traff.values()):
            fynd.append({'fil': '(alla)', 'typ': 'saknat element', 'rad': 0, 'text': k['namn'], 'riktning': k.get('skal', '')})
    return fynd


def rapport(kallor, fraser_fil=None, krav_fil=None):
    extra = [l.strip() for l in Path(fraser_fil).read_text(encoding='utf-8').splitlines() if l.strip() and not l.startswith('#')] if fraser_fil else []
    krav = json.loads(Path(krav_fil).read_text(encoding='utf-8')).get('krav') if krav_fil else []
    alla, texter, filer = [], {}, 0
    for f in samla_filer(kallor):
        raw = f.read_text(encoding='utf-8', errors='replace')
        filer += 1
        fynd, rows = kontrollera_fil(f, raw, extra)
        for x in fynd:
            alla.append({'fil': str(f), **x})
        if f.suffix in ('.html', '.htm', '.md', '.mdx', '.tsx', '.jsx', '.astro'):
            texter[f] = '\n'.join(t for _, t in rows)
    alla.extend(kontrollera_krav(krav, texter))
    summa = {}
    for x in alla:
        summa[x['typ']] = summa.get(x['typ'], 0) + 1
    return {'schema': 1, 'kalla': [str(k) for k in kallor], 'filer': filer, 'fynd': alla, 'sammanfattning': summa,
            'fraser_ur_brief': len(extra), 'krav': len(krav or []), 'poang': None,
            'not': 'rapport att läsa och rätta eller motivera; ingen poäng, inget godkännande'}


def markdown(r):
    lines = ['# Copykontroll — %d filer, %d fynd' % (r['filer'], len(r['fynd'])), '']
    for typ, n in sorted(r['sammanfattning'].items()):
        lines.append('- %s: %d' % (typ, n))
    lines += ['', '| Fil | Rad | Typ | Text | Riktning |', '|---|---|---|---|---|']
    for x in r['fynd']:
        lines.append('| %s | %s | %s | %s | %s |' % (x['fil'], x['rad'] or '', x['typ'], x['text'].replace('|', '/'), x['riktning'].replace('|', '/')))
    lines += ['', r['not']]
    return '\n'.join(lines) + '\n'


def main(argv=None):
    p = argparse.ArgumentParser(prog='copy_kontroll', description=__doc__.split('\n\n')[0])
    p.add_argument('--kalla', nargs='+', required=True)
    p.add_argument('--fraser')
    p.add_argument('--krav')
    p.add_argument('--ut', required=True)
    p.add_argument('--md')
    a = p.parse_args(argv)
    r = rapport(a.kalla, a.fraser, a.krav)
    Path(a.ut).write_text(json.dumps(r, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    if a.md:
        Path(a.md).write_text(markdown(r), encoding='utf-8')
    print(json.dumps({'filer': r['filer'], 'fynd': len(r['fynd']), 'sammanfattning': r['sammanfattning'], 'ut': a.ut}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
