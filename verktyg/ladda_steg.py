"""Laddar ett Digitala-stegs underlag till en arbetsyta med versionskontroll och kvitto.

    python3 -B verktyg/ladda_steg.py --steg NAMN --ut KATALOG [--kund KUNDMAPP] [--bestallning POST-ID]
        [--utforare claude|codex] [--rot REPOROT] [--json]

Allt kontrolleras innan något skrivs: okänt steg, steg utanför stående mandat utan beställnings-id, saknat obligatoriskt
underlag, opinnad eller ändrad professionsfil (fel version), kundmapp inne i repot, kundfil som lämnar kundmappen och
professionsfil som lämnar repot vägras med exit 2 och ingen katalog skapas. Utkatalogen får inte finnas i förväg.
Skriver KATALOG/underlag/profession/…, KATALOG/underlag/kund/…, UNDERLAG.md (fullständig lista med delar att läsa och
anvisning), LADDNING.json (kvittot) och ANVANDNINGSNOTER.md (skelett). Bara standardbiblioteket.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROT = Path(__file__).resolve().parents[1]
STEG_FIL = 'steg/steg.json'
PINNAR_FIL = 'steg/PINNAR.sha256'
KLASSER = ('profession', 'kund')
MANDAT = ('staende', 'bestallning')
BESTALLNING = re.compile(r'\A[A-Z0-9][A-Z0-9-]{2,79}\Z')
STEGNAMN = re.compile(r'\A[a-z][a-z0-9-]{1,39}\Z')
FIL = re.compile(r'\A[A-Za-z0-9][A-Za-z0-9._-]*(/[A-Za-z0-9][A-Za-z0-9._-]*)*\Z')


class Vagrad(Exception):
    """Ett vägrat kommando; ingenting har skrivits."""


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def upplost(path):
    """Den upplösta sökvägen (systemlänkar som /var -> /private/var får finnas ovanför det som kontrolleras)."""
    path = Path(path)
    if not path.is_absolute():
        path = Path.cwd() / path
    return Path(os.path.realpath(str(path)))


def utan_lankar(path, base):
    """Den upplösta sökvägen, efter kontroll att ingen komponent UNDER base är en symbolisk länk.

    Länkar ovanför base (systemets egna, som /var) är inte vår sak; länkar inne i repot eller inne i kundmappen är
    det, eftersom de är vägen att smuggla en fil från fel klass in i laddningen.
    """
    path = Path(path)
    if not path.is_absolute():
        path = Path.cwd() / path
    base = Path(base)
    for candidate in (path, *path.parents):
        if candidate == base:
            break
        if candidate.is_symlink():
            raise Vagrad('symbolisk länk på vägen: ' + str(candidate))
    return Path(os.path.realpath(str(path)))


def inuti(child, parent):
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def las_steg(rot):
    try:
        data = json.loads((rot / STEG_FIL).read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise Vagrad('steg/steg.json kan inte läsas: ' + str(error))
    if not isinstance(data, dict) or data.get('schema') != 1 or not isinstance(data.get('steg'), dict) or not data['steg']:
        raise Vagrad('steg/steg.json har fel form')
    for name, step in data['steg'].items():
        if not STEGNAMN.match(name) or not isinstance(step, dict) or set(step) != {'mandat', 'syfte', 'anvisning', 'underlag'}:
            raise Vagrad('steget %r har fel form' % name)
        if step['mandat'] not in MANDAT or not isinstance(step['underlag'], list) or not step['underlag']:
            raise Vagrad('steget %r har fel mandat eller inga underlag' % name)
        seen = set()
        for item in step['underlag']:
            if (not isinstance(item, dict) or set(item) != {'fil', 'klass', 'obligatorisk', 'delar'}
                    or not isinstance(item['fil'], str) or not FIL.match(item['fil']) or item['klass'] not in KLASSER
                    or not isinstance(item['obligatorisk'], bool) or not isinstance(item['delar'], str) or not item['delar'].strip()):
                raise Vagrad('underlaget %r i steget %r har fel form' % (item, name))
            key = (item['klass'], item['fil'])
            if key in seen:
                raise Vagrad('underlaget %s/%s förekommer två gånger i steget %r' % (key[0], key[1], name))
            seen.add(key)
    return data


def las_pinnar(rot):
    pinnar = {}
    try:
        lines = (rot / PINNAR_FIL).read_text(encoding='utf-8').splitlines()
    except OSError as error:
        raise Vagrad('steg/PINNAR.sha256 kan inte läsas: ' + str(error))
    for line in lines:
        if not line.strip() or line.startswith('#'):
            continue
        parts = line.split('  ', 1)
        if len(parts) != 2 or not re.fullmatch('[0-9a-f]{64}', parts[0]) or parts[1] in pinnar:
            raise Vagrad('steg/PINNAR.sha256 har en ogiltig eller dubbel rad: ' + line[:80])
        pinnar[parts[1]] = parts[0]
    return pinnar


def git_lage(rot):
    try:
        head = subprocess.run(['git', '-C', str(rot), 'rev-parse', 'HEAD'], capture_output=True, text=True, timeout=30)
        status = subprocess.run(['git', '-C', str(rot), 'status', '--porcelain'], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None, None
    if head.returncode != 0 or status.returncode != 0:
        return None, None
    return head.stdout.strip(), status.stdout.strip() == ''


def planera(rot, steg_namn, kund, bestallning):
    """Kontrollerar allt och returnerar kopieplanen; kastar Vagrad utan sidoeffekter."""
    data = las_steg(rot)
    if steg_namn not in data['steg']:
        raise Vagrad('okänt steg: %r (kända: %s)' % (steg_namn, ', '.join(sorted(data['steg']))))
    step = data['steg'][steg_namn]
    if bestallning is not None and not BESTALLNING.match(bestallning):
        raise Vagrad('beställnings-id ska vara beslutspostens namn, t.ex. DIGITALA-1-AGARBESLUT-20260926')
    if step['mandat'] == 'bestallning' and bestallning is None:
        raise Vagrad('steget %r ligger utanför det stående mandatet (MANDAT.md §2): ange --bestallning POST-ID' % steg_namn)
    pinnar = las_pinnar(rot)
    kund_dir = None
    if kund is not None:
        kund_dir = upplost(kund)
        if not kund_dir.is_dir():
            raise Vagrad('kundmappen finns inte: ' + str(kund_dir))
        if inuti(kund_dir, rot) or inuti(rot, kund_dir):
            raise Vagrad('sammanblandning: kundmappen får inte ligga i repot (och repot inte i kundmappen)')
    rows, saknade = [], []
    for item in step['underlag']:
        row = {'fil': item['fil'], 'klass': item['klass'], 'obligatorisk': item['obligatorisk'], 'delar': item['delar']}
        if item['klass'] == 'profession':
            source = rot / item['fil']
            if source.exists() or source.is_symlink():
                resolved = utan_lankar(source, rot)
                if not inuti(resolved, rot):
                    raise Vagrad('sammanblandning: professionsfilen lämnar repot: ' + item['fil'])
                if not resolved.is_file():
                    raise Vagrad('professionsfilen är ingen vanlig fil: ' + item['fil'])
                pin = pinnar.get(item['fil'])
                if pin is None:
                    raise Vagrad('opinnad professionsfil (kör verktyg/pinna.py som nytt beslut): ' + item['fil'])
                digest = sha256_file(resolved)
                if digest != pin:
                    raise Vagrad('fel version: %s har sha256 %s…, pinnad %s…' % (item['fil'], digest[:12], pin[:12]))
                row.update(kalla=str(resolved), sha256=digest, pinnad_sha256=pin, byte=resolved.stat().st_size,
                           status='laddad', plats='underlag/profession/' + item['fil'])
            else:
                row.update(status='saknas', plats=None)
        else:
            if kund_dir is None:
                row.update(status='saknas (ingen kundmapp)', plats=None)
            else:
                source = kund_dir / item['fil']
                if source.exists() or source.is_symlink():
                    resolved = utan_lankar(source, kund_dir)
                    if not inuti(resolved, kund_dir):
                        raise Vagrad('sammanblandning: kundfilen lämnar kundmappen: ' + item['fil'])
                    if inuti(resolved, rot):
                        raise Vagrad('sammanblandning: kundfilen ligger i repot: ' + item['fil'])
                    if not resolved.is_file():
                        raise Vagrad('kundfilen är ingen vanlig fil: ' + item['fil'])
                    row.update(kalla=str(resolved), sha256=sha256_file(resolved), pinnad_sha256=None,
                               byte=resolved.stat().st_size, status='laddad', plats='underlag/kund/' + item['fil'])
                else:
                    row.update(status='saknas', plats=None)
        if row['status'] != 'laddad':
            if item['obligatorisk']:
                saknade.append('%s/%s' % (item['klass'], item['fil']))
            row['status'] = row['status'].replace('saknas', 'saknas (valfri)') if not item['obligatorisk'] else row['status']
        rows.append(row)
    if saknade:
        raise Vagrad('saknat obligatoriskt underlag: ' + ', '.join(saknade))
    return step, rows, kund_dir


def underlag_md(steg_namn, step, rows, bestallning):
    lines = ['# Underlag för steget %s' % steg_namn, '',
             'Fullständig lista; du kan inte lista kataloger. Läs bara de delar som anges. Underlagen är råd: briefen, det',
             'accepterade uppdraget och mandatet vinner. Kundfiler (`underlag/kund/`) och professionsfiler (`underlag/profession/`)',
             'hålls isär; en kundpreferens blir aldrig praxis utan fältet "lokal preferens?" och två relevanta tillämpningar.',
             '', '**Syfte:** ' + step['syfte'], '', '**Anvisning:** ' + step['anvisning'], '',
             '**Mandat:** ' + ('stående (MANDAT.md §1)' if step['mandat'] == 'staende' else 'beställning ' + str(bestallning) + ' (MANDAT.md §2)'), '',
             '| plats | klass | obligatorisk | delar att läsa | sha256 | byte | status |', '|---|---|---|---|---|---|---|']
    for r in rows:
        lines.append('| `%s` | %s | %s | %s | `%s` | %s | %s |' % (
            r['plats'] or r['fil'], r['klass'], 'ja' if r['obligatorisk'] else 'nej', r['delar'].replace('|', '/'),
            (r.get('sha256') or '')[:16] + ('…' if r.get('sha256') else ''), r.get('byte', ''), r['status']))
    lines.append('')
    return '\n'.join(lines) + '\n'


def noter_md(steg_namn, rows):
    lines = ['# Användningsnoter — steget %s' % steg_namn, '',
             'Fyll en rad per underlag när steget är klart, med ett av fyra utfall: *påverkade ett konkret val, en ändring eller',
             'ett fynd (vilket)* · *användes som kontroll, ingen ändring behövdes* · *inte tillämpligt* · *nådde inte arbetet*.',
             'Ingen rapport per fil för sakens skull; inga konstruerade bidrag. Noterna sammanfattas i fallets kontorspost.', '',
             '| underlag | utfall | not |', '|---|---|---|']
    for r in rows:
        if r['status'] == 'laddad':
            lines.append('| `%s` | (fyll i) | |' % r['plats'])
    lines.append('')
    return '\n'.join(lines) + '\n'


def ladda(rot, steg_namn, ut, kund=None, bestallning=None, utforare=None):
    rot = upplost(rot)
    step, rows, kund_dir = planera(rot, steg_namn, kund, bestallning)
    ut = Path(ut)
    if not ut.is_absolute():
        ut = Path.cwd() / ut
    if ut.exists() or ut.is_symlink():
        raise Vagrad('utkatalogen finns redan: ' + str(ut))
    if not ut.parent.is_dir():
        raise Vagrad('utkatalogens förälder finns inte: ' + str(ut.parent))
    if inuti(upplost(ut.parent), rot):
        raise Vagrad('arbetsytan ska ligga utanför repot')
    head, ren = git_lage(rot)
    ut.mkdir(mode=0o700)
    for r in rows:
        if r['status'] != 'laddad':
            continue
        target = ut / r['plats']
        target.parent.mkdir(parents=True, exist_ok=True)
        data = Path(r['kalla']).read_bytes()
        if hashlib.sha256(data).hexdigest() != r['sha256']:
            raise Vagrad('filen ändrades under laddningen: ' + r['fil'])
        target.write_bytes(data)
    over = hashlib.sha256('\n'.join('%s %s' % (r['plats'], r['sha256']) for r in rows if r['status'] == 'laddad').encode()).hexdigest()
    receipt = {'schema': 1, 'steg': steg_namn, 'mandat': step['mandat'], 'bestallning': bestallning, 'utforare': utforare,
               'laddat_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'rot': str(rot), 'rot_git_head': head,
               'rot_git_ren': ren, 'kundmapp': str(kund_dir) if kund_dir else None, 'arbetsyta': str(ut),
               'underlag': [{k: r.get(k) for k in ('plats', 'fil', 'klass', 'obligatorisk', 'delar', 'status', 'sha256', 'pinnad_sha256', 'byte')} for r in rows],
               'sha256_over_underlag': over}
    (ut / 'UNDERLAG.md').write_text(underlag_md(steg_namn, step, rows, bestallning), encoding='utf-8')
    (ut / 'ANVANDNINGSNOTER.md').write_text(noter_md(steg_namn, rows), encoding='utf-8')
    with (ut / 'LADDNING.json').open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, indent=1, ensure_ascii=False)
        stream.write('\n')
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(prog='ladda_steg', description=__doc__.split('\n\n')[0])
    parser.add_argument('--steg', required=True)
    parser.add_argument('--ut', required=True)
    parser.add_argument('--kund')
    parser.add_argument('--bestallning')
    parser.add_argument('--utforare', choices=('claude', 'codex'))
    parser.add_argument('--rot', default=str(ROT))
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    try:
        receipt = ladda(args.rot, args.steg, args.ut, args.kund, args.bestallning, args.utforare)
    except Vagrad as error:
        print(json.dumps({'utfall': 'vagrad', 'skal': str(error)}, ensure_ascii=False))
        return 2
    summary = {'utfall': 'laddad', 'steg': receipt['steg'], 'arbetsyta': receipt['arbetsyta'],
               'laddade': sum(1 for r in receipt['underlag'] if r['status'] == 'laddad'),
               'valfria_saknade': [r['fil'] for r in receipt['underlag'] if r['status'] != 'laddad'],
               'sha256_over_underlag': receipt['sha256_over_underlag']}
    print(json.dumps(receipt if args.json else summary, ensure_ascii=False, indent=1 if args.json else None))
    return 0


if __name__ == '__main__':
    sys.exit(main())
