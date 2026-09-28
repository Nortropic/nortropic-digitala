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
import kritikbevis

ROT = Path(__file__).resolve().parents[1]
STEG_FIL = 'steg/steg.json'
PINNAR_FIL = 'steg/PINNAR.sha256'
KLASSER = ('profession', 'kund')
MANDAT = ('staende', 'bestallning')
BESTALLNING = re.compile(r'\A[A-Z0-9][A-Z0-9-]{2,79}\Z')
STEGNAMN = re.compile(r'\A[a-z][a-z0-9-]{1,39}\Z')
FIL = re.compile(r'\A[A-Za-z0-9][A-Za-z0-9._-]*(/[A-Za-z0-9][A-Za-z0-9._-]*)*\Z')
SKAPARFIL = 'SKAPARUNDERLAG.json'


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


def skaparplan(kund, rot, pinnar):
    """Validera ett litet kundvalt skaparpaket. Hash är bindning, aldrig bevis på användning."""
    path = utan_lankar(kund / SKAPARFIL, kund)
    try:
        d = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as e:
        raise Vagrad('skaparpaket kan inte läsas: ' + str(e)) from e
    if (not isinstance(d, dict) or set(d) != {'schema', 'uppdrag', 'bilagor', 'referenser', 'resurser'}
            or d['schema'] != 'digitala-skaparunderlag/1'
            or any(not isinstance(d[k], list) for k in ('bilagor', 'referenser', 'resurser'))):
        raise Vagrad('skaparpaket har fel form')

    def text(value):
        return isinstance(value, str) and bool(value.strip())

    def filrad(item, role, extra):
        if (not isinstance(item, dict) or set(item) != {'fil', 'sha256'} | extra
                or not isinstance(item['fil'], str) or not FIL.fullmatch(item['fil'])
                or item['fil'] in (SKAPARFIL, 'SKAPARPAKET.md')
                or not isinstance(item['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', item['sha256'])):
            raise Vagrad('ogiltig filbindning i skaparpaket')
        source = utan_lankar(kund / item['fil'], kund)
        if not inuti(source, kund) or not source.is_file() or sha256_file(source) != item['sha256']:
            raise Vagrad('skaparpaketets fil saknas eller har ändrats: ' + item['fil'])
        if role == 'referensbild':
            raw = source.read_bytes()
            if not (raw.startswith(b'\x89PNG\r\n\x1a\n') or raw.startswith(b'\xff\xd8\xff')
                    or (raw.startswith(b'RIFF') and raw[8:12] == b'WEBP')):
                raise Vagrad('referensbild är inte PNG/JPEG/WebP: ' + item['fil'])
        return {'fil': item['fil'], 'klass': 'kund', 'obligatorisk': True,
                'delar': role + ': ' + item.get('varfor', 'fokuserat skapandeuppdrag, läs först'),
                'kalla': str(source), 'sha256': item['sha256'], 'pinnad_sha256': None,
                'byte': source.stat().st_size, 'status': 'laddad', 'plats': 'underlag/kund/' + item['fil']}

    rows = [filrad(d['uppdrag'], 'skapandeuppdrag', set())]
    roles = {}
    seen = {d['uppdrag']['fil']}
    for item in d['bilagor']:
        if (not isinstance(item, dict) or item.get('roll') not in ('fakta', 'referensbild', 'beteende', 'tillgang')
                or not text(item.get('varfor'))):
            raise Vagrad('skaparpaketets bilaga saknar roll eller skäl')
        row = filrad(item, item['roll'], {'roll', 'varfor'})
        if item['fil'] in seen:
            raise Vagrad('dubbel fil i skaparpaket: ' + item['fil'])
        seen.add(item['fil']); roles[item['fil']] = item['roll']; rows.append(row)
    ids = set()
    for ref in d['referenser']:
        if (not isinstance(ref, dict) or set(ref) != {'id', 'kalla', 'roller', 'urvalsskal', 'observation', 'bevis', 'paverkar', 'begransning'}
                or any(not text(ref[k]) for k in ('id', 'kalla', 'urvalsskal', 'paverkar', 'begransning'))
                or not isinstance(ref['roller'], list) or not ref['roller']
                or any(r not in ('bransch', 'hantverk', 'ux') for r in ref['roller'])
                or ref['observation'] not in ('live', 'galleri', 'text', 'delvis', 'otillganglig')
                or not isinstance(ref['bevis'], list)
                or any(not isinstance(p, str) or p not in roles for p in ref['bevis'])):
            raise Vagrad('ogiltig referensroll eller bevispekare i skaparpaket')
        if ref['id'] in ids:
            raise Vagrad('dubbelt referens-id: ' + ref['id'])
        ids.add(ref['id'])
        if ref['observation'] in ('live', 'galleri') and not any(roles[p] == 'referensbild' for p in ref['bevis']):
            raise Vagrad('visuell referens saknar hashbunden bild: ' + ref['id'])
        if ref['observation'] != 'otillganglig' and not ref['bevis']:
            raise Vagrad('observerad referens saknar underlag: ' + ref['id'])
    resources = {}
    for item in d['resurser']:
        if (not isinstance(item, dict) or set(item) != {'fil', 'form', 'delar', 'skal', 'historik'}
                or any(not text(item[k]) for k in item)
                or not FIL.fullmatch(item['fil']) or not item['fil'].startswith('kunskap/externa/')
                or item['form'] not in ('lasunderlag', 'metod', 'skill', 'plugin', 'verktyg', 'anpassning', 'utdrag')):
            raise Vagrad('ogiltigt resursval i skaparpaket')
        if item['fil'] in resources:
            raise Vagrad('dubbelt resursval: ' + item['fil'])
        source = utan_lankar(rot / item['fil'], rot)
        if not inuti(source, rot) or not source.is_file() or pinnar.get(item['fil']) != sha256_file(source):
            raise Vagrad('resursen är inte en tillgänglig pinnad professionsfil: ' + item['fil'])
        resources[item['fil']] = item
    return d, rows, resources


def skaparpaket_md(d):
    lines = ['# Fokuserat skaparpaket', '',
             'Läs skapandeuppdraget först, öppna valda bilder och använd källorna vid konkreta val.',
             'Behov och mandat gäller framför designhypotesen. Paketet är underlag, inte kvalitetsgodkännande.',
             'Kopierad skilltext betyder inte installerad eller anropad skill. Kontrollera faktisk tillgång innan bruk.', '',
             '## Uppdrag', '', '`underlag/kund/' + d['uppdrag']['fil'] + '`', '', '## Valda bilagor', '']
    for item in d['bilagor']:
        lines.append('- `%s` — %s: %s' % ('underlag/kund/' + item['fil'], item['roll'], item['varfor']))
    lines += ['', '## Referenser och avsedd påverkan', '']
    for ref in d['referenser']:
        lines.append('- %s (%s; %s): %s. Urval: %s. Påverkar: %s. Gräns: %s. Bevis: %s.' %
                     (ref['id'], ', '.join(ref['roller']), ref['observation'], ref['kalla'], ref['urvalsskal'],
                      ref['paverkar'], ref['begransning'], ', '.join('`underlag/kund/'+p+'`' for p in ref['bevis'])))
    lines += ['', '## Valda resurser', '']
    for item in d['resurser']:
        lines.append('- `%s` — önskad form %s, delar: %s. Skäl: %s. Läst historik: %s.' %
                     ('underlag/profession/'+item['fil'], item['form'], item['delar'], item['skal'], item['historik']))
    lines += ['', '## Obligatoriska gränser och fördjupning', '',
              'UNDERLAG.md redovisar samtliga versionsbundna filer, inklusive kriterier, brief och kundkällor.',
              'Kriterier och relevanta säkerhets-/integrationskrav får inte utelämnas för att paketet är litet.',
              'Skriv faktisk användning och konsekvens i ANVANDNINGSNOTER.md; tomt utfall förblir okänt.', '']
    return '\n'.join(lines)


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
    skapar, bilagor, resurser = None, [], {}
    if kund_dir and any(i['fil'] == SKAPARFIL for i in step['underlag']) and (kund_dir / SKAPARFIL).exists():
        skapar, bilagor, resurser = skaparplan(kund_dir, rot, pinnar)
    items = [dict(i) for i in step['underlag']]
    existing = {i['fil'] for i in items if i['klass'] == 'profession'}
    for name, item in resurser.items():
        if name not in existing:
            items.append({'fil': name, 'klass': 'profession', 'obligatorisk': False, 'delar': item['delar']})
    rows, saknade = [], []
    for item in items:
        row = {'fil': item['fil'], 'klass': item['klass'], 'obligatorisk': item['obligatorisk'], 'delar': item['delar']}
        if item['klass'] == 'profession' and item['fil'].startswith('kunskap/externa/') and not item['obligatorisk']:
            if item['fil'] not in resurser:
                row.update(status='inte vald (valfri resurs)', plats=None)
                rows.append(row)
                continue
            row['delar'] = resurser[item['fil']]['delar']
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
    task = next((r for r in rows if r['fil'] == 'KUNDSTART-ARBETSUPPGIFT.json' and r['status'] == 'laddad'), None)
    if task and steg_namn == 'research':
        try:
            task_data = json.loads(Path(task['kalla']).read_text(encoding='utf-8'))
            if not isinstance(task_data, dict) or task_data.get('schema') != 'digitala-intagsarbete/1':
                raise ValueError('fel taskschema')
            materials = task_data.get('material', [])  # en tidig avvikelserapport kan sakna material; inte komplett.
            if not isinstance(materials, list):
                raise ValueError('material är inte en lista')
            for item in materials:
                if not isinstance(item, dict):
                    raise ValueError('materialrad är inte ett objekt')
                if 'utdrag' not in item:
                    continue  # historiskt format; ingen läsning hittas på.
                excerpt = item['utdrag']
                if (not isinstance(excerpt, dict) or set(excerpt) != {'fil', 'sha256', 'kalla_sha256'}
                        or not isinstance(excerpt['fil'], str) or not FIL.fullmatch(excerpt['fil'])
                        or not excerpt['fil'].startswith('KUNDSTART/')
                        or item.get('sha256') != excerpt['kalla_sha256']
                        or any(not isinstance(excerpt[k], str) or not re.fullmatch('[0-9a-f]{64}', excerpt[k])
                               for k in ('sha256', 'kalla_sha256'))):
                    raise ValueError('ogiltig materialutdragsbindning')
                source = utan_lankar(kund_dir / excerpt['fil'], kund_dir)
                if not inuti(source, kund_dir) or not source.is_file() or sha256_file(source) != excerpt['sha256']:
                    raise ValueError('materialutdrag saknas eller har ändrats: ' + excerpt['fil'])
                old = next((r for r in rows if r['klass'] == 'kund' and r['fil'] == excerpt['fil']), None)
                if old:
                    if old.get('sha256') != excerpt['sha256']:
                        raise ValueError('motsägande materialutdrag: ' + excerpt['fil'])
                    continue
                rows.append({'fil': excerpt['fil'], 'klass': 'kund', 'obligatorisk': True,
                             'delar': 'obetrott kundmaterialutdrag; laddat, inte redan läst; originalsha256 ' + excerpt['kalla_sha256'],
                             'kalla': str(source), 'sha256': excerpt['sha256'], 'pinnad_sha256': None,
                             'byte': source.stat().st_size, 'status': 'laddad', 'plats': 'underlag/kund/' + excerpt['fil']})
        except (OSError, ValueError) as e:
            raise Vagrad('Kundstarts materialunderlag kan inte laddas: ' + str(e)) from e
    if skapar and steg_namn in ('koncept', 'bygge'):
        # Samma fil kan redan vara ett obligatoriskt kundunderlag. Behåll en enda kopia med samma hash.
        for row in bilagor:
            existing_row = next((r for r in rows if r['klass'] == 'kund' and r['fil'] == row['fil']), None)
            if existing_row:
                if existing_row.get('sha256') != row['sha256']:
                    raise Vagrad('skaparpaket och steg har olika filbindning: ' + row['fil'])
            else:
                rows.append(row)
        raw = skaparpaket_md(skapar).encode('utf-8')
        rows.append({'fil': 'SKAPARPAKET.md', 'klass': 'kund', 'obligatorisk': True, 'delar': 'genererad läsordning; läs först',
                     'data': raw, 'sha256': hashlib.sha256(raw).hexdigest(), 'pinnad_sha256': None,
                     'byte': len(raw), 'status': 'laddad', 'plats': 'SKAPARPAKET.md'})
    bildrad = next((r for r in rows if r['fil'] == kritikbevis.BILDFIL and r['status'] == 'laddad'), None)
    if bildrad:
        try:
            d = kritikbevis.manifest(json.loads(Path(bildrad['kalla']).read_text()), kund_dir)
        except (kritikbevis.Vagrad, ValueError) as e:
            raise Vagrad(str(e)) from e
        required=utan_lankar(kund_dir/d['kravfil'],kund_dir)
        rows.append({'fil':d['kravfil'],'klass':'kund','obligatorisk':True,'delar':'fördefinierade bildkrav och tillämplighet','kalla':str(required),'sha256':d['krav_sha256'],'pinnad_sha256':None,'byte':required.stat().st_size,'status':'laddad','plats':'underlag/kund/'+d['kravfil']})
        for b in d['bilder']:
            resolved = utan_lankar(kund_dir / b['fil'], kund_dir)
            rows.append({'fil': b['fil'], 'klass': 'kund', 'obligatorisk': True, 'delar': 'öppna bilden: ' + b['drag'],
                         'kalla': str(resolved), 'sha256': b['sha256'], 'pinnad_sha256': None, 'byte': resolved.stat().st_size,
                         'status': 'laddad', 'plats': 'underlag/kund/' + b['fil']})
    return step, rows, kund_dir


def underlag_md(steg_namn, step, rows, bestallning):
    lines = ['# Underlag för steget %s' % steg_namn, '',
             'Fullständig lista; du kan inte lista kataloger. Läs bara de delar som anges. Styrkta kundbehov och ägarens',
             'mandat står över råd och internt skrivna designhypoteser i briefen. Kundfiler (`underlag/kund/`) och professionsfiler (`underlag/profession/`)',
             'hålls isär; en kundpreferens blir aldrig praxis: erfarenhet klassas som observation, kundpreferens, hypotes eller',
             'dokumenterad felorsak (kunskap/LARDOMAR.md), och ingen mängd tillämpningar gör något till praxis.',
             '', '**Skapandeingång:** ' + ('läs `SKAPARPAKET.md` först; fullständig fördjupning nedan.' if any(r['fil'] == 'SKAPARPAKET.md' for r in rows)
                                         else 'inget fokuserat skaparpaket laddat; detta kvitto bevisar inte att skapandeunderlaget är färdigt.'),
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
             'Ingen rapport per fil för sakens skull; inga konstruerade bidrag. Noterna sammanfattas i fallets kontorspost.',
             'Skilj vald/laddad, faktiskt läst eller anropad, konkret påverkan och observerat resultat. Ange bevispekare.',
             'Åtgång: bokför tillgängliga input/output/cache-token, kostnad, väntetid, omtag och ägararbete separat.',
             'Okända värden är okända; byt inte modellkvot eller debitering mot uppskattade token. Jämförelse kräver samma uppgift/räckvidd.', '',
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
        data = r['data'] if 'data' in r else Path(r['kalla']).read_bytes()
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
               'valfria_saknade': [r['fil'] for r in receipt['underlag'] if r['status'].startswith('saknas')],
               'valfria_inte_valda': [r['fil'] for r in receipt['underlag'] if r['status'] == 'inte vald (valfri resurs)'],
               'sha256_over_underlag': receipt['sha256_over_underlag']}
    print(json.dumps(receipt if args.json else summary, ensure_ascii=False, indent=1 if args.json else None))
    return 0


if __name__ == '__main__':
    sys.exit(main())
