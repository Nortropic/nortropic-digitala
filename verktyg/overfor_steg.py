"""Bytebunden lokal överföring av research/brief från ordinarie laddad arbetsyta.

Ingen sakbedömning eller stegaccept. Modellens original bevaras; bara null-hashar
beräknas. Ett återupptaget, delvis skrivet paket får samma journal och bytes.
"""
import hashlib
import json
import re
import os
from pathlib import Path
import tempfile

import ladda_steg as ls


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


DISPOSITIONER = ('val', 'kanal', 'utreds', 'avstar')


def kundtillval_krav(customer):
    """Kundens aktuella tillval ur senaste Kundstart-intaget: {id: kundval}. Tom när intaget saknar tillval."""
    path = Path(customer) / 'KUNDSTART-ARBETSUPPGIFT.json'
    if not path.is_file():
        return {}
    try:
        task = json.loads(path.read_bytes())
    except (ValueError, UnicodeError):
        raise ls.Vagrad('KUNDSTART-ARBETSUPPGIFT.json kan inte läsas; importera intaget på nytt före brief')
    if not isinstance(task, dict) or not isinstance(task.get('tillval', []), list):
        raise ls.Vagrad('KUNDSTART-ARBETSUPPGIFT.json har fel form; importera intaget på nytt före brief')
    # Samma id-regel som importen: ett id som importen vägrat kan inte blockera briefen.
    return {t['id']: t.get('kundval') for t in task.get('tillval', [])
            if isinstance(t, dict) and isinstance(t.get('id'), str) and re.fullmatch(r'(?:[a-z][a-z_]{1,39}|annat_\d{1,3})', t['id'])
            and t.get('kundval') in (None, 'onskat', 'har_system', 'hjalp', 'inte_nu')}


def prova_kundtillval(customer, integrationsval):
    """Brief besvarar varje aktuellt kundtillval; ett borttaget eller avböjt tillval får inte stå kvar som val."""
    tillval = kundtillval_krav(customer)
    aktuella = sorted(t for t, v in tillval.items() if v in ('onskat', 'har_system', 'hjalp'))
    if not tillval:
        return
    if aktuella and integrationsval is None:
        raise ls.Vagrad('kunden har aktuella tillval från Kundstart (%s); skriv INTEGRATIONSVAL.json med kundtillval som besvarar vart och ett' % ', '.join(aktuella))
    if integrationsval is None:
        return
    rader = integrationsval.get('kundtillval', [])
    if not isinstance(rader, list) or not all(isinstance(r, dict) for r in rader):
        raise ls.Vagrad('INTEGRATIONSVAL.json: kundtillval ska vara en lista med rader')
    svar = {r.get('tillval'): r for r in rader}
    saknas = [t for t in aktuella if t not in svar or svar[t].get('disposition') not in DISPOSITIONER
              or not isinstance(svar[t].get('skal'), str) or not svar[t]['skal'].strip()]
    if saknas:
        raise ls.Vagrad('INTEGRATIONSVAL.json besvarar inte kundens tillval: %s (disposition val|kanal|utreds|avstar och skal krävs)' % ', '.join(saknas))
    kvar = [t for t, r in svar.items() if r.get('disposition') == 'val' and tillval.get(t) not in ('onskat', 'har_system', 'hjalp')]
    if kvar:
        raise ls.Vagrad('kunden har tagit bort eller avböjt tillvalet %s; ta bort valet ur INTEGRATIONSVAL.json eller motivera det som utreds' % ', '.join(sorted(map(str, kvar))))


def safe(root, name):
    if not isinstance(name, str) or not ls.FIL.fullmatch(name):
        raise ls.Vagrad('ogiltig överföringssökväg')
    path = ls.utan_lankar(root / name, root)
    if not ls.inuti(path, root):
        raise ls.Vagrad('överföringssökväg lämnar sin katalog')
    cursor = Path(root)
    for part in name.split('/'):
        if cursor.is_dir() and any(p.name.casefold() == part.casefold() and p.name != part for p in cursor.iterdir()):
            raise ls.Vagrad('sökvägens skiftläge skiljer från befintligt namn: ' + name)
        cursor /= part
    return path


def read_work(work, name):
    path = safe(work, name)
    if not path.is_file():
        raise ls.Vagrad('skriv filen i arbetsytan eller välj ett hashbundet laddat underlag: ' + name)
    return path.read_bytes()


def protected_inputs(rot, customer, receipt):
    from fortsatt import FAKTA, INTAG
    names = {r['fil'].casefold() for step in ls.las_steg(Path(rot))['steg'].values()
             for r in step['underlag'] if r['klass'] == 'kund'}
    names.update(n.casefold() for n in FAKTA + INTAG)
    names.update(r['fil'].casefold() for r in receipt['underlag'] if r['klass'] == 'kund'
                 and not r.get('delar', '').startswith(('historiskt val', 'historiskt skaparpaket')))
    names.update({'lage.json', 'laddning.json', 'bestallning.json', 'beviskrav.json', 'skaparunderlag.json', 'skaparpaket.md'})
    names.update(p.name.casefold() for p in customer.glob('research-r*.md'))
    return names


def previous_outputs(s, st, steg):
    previous = {}
    for name in st.get('kvitton', []):
        path = Path(name)
        if ls.inuti(path, Path(s['fall'])) and path.name == 'KVITTO.json':
            record = json.loads(safe(Path(s['fall']), str(path.relative_to(s['fall']))).read_bytes())
            if record.get('schema') == 'digitala-stegoverforing/1' and record['bindning']['steg'] == steg:
                ident = sha(json.dumps(record['bindning'], sort_keys=True).encode())
                if path.parent.name != 'overforing-' + ident or record.get('lage') not in ('förberedd', 'överförd'):
                    raise ls.Vagrad('tidigare överföringsjournal har ändrats eller har okänt läge')
                history = path.parent
                if sha(safe(history, 'LADDNING.json').read_bytes()) != record['bindning']['laddning_sha256']:
                    raise ls.Vagrad('tidigare överföringsjournal har ändrad laddning')
                for name, digest in record['bindning']['original'].items():
                    if sha(safe(history, 'original/' + name).read_bytes()) != digest:
                        raise ls.Vagrad('tidigare överföringsjournal har ändrat original')
                for name, digest in record['fore'].items():
                    if digest is not None and sha(safe(history, 'fore/' + name).read_bytes()) != digest:
                        raise ls.Vagrad('tidigare överföringsjournal har ändrad historik')
                previous.update(record['bindning']['filer'])
    return previous


def write(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, tmp = tempfile.mkstemp(prefix='.overfor-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            if path.is_file():
                os.fchmod(stream.fileno(), path.stat().st_mode & 0o777)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def transfer(s, steg, rot, checkpoint=None):
    if steg not in ('research', 'brief'):
        raise ls.Vagrad('överföring stöder research eller brief')
    st = s['steg'][steg]
    receipt_path = Path(st['laddning'])
    work = receipt_path.parent.resolve()
    customer = Path(s['kund']).resolve()
    if not receipt_path.is_file():
        raise ls.Vagrad('laddningen saknas: ' + str(receipt_path)
                        + '; markera steget underkand och kör fortsatt för ny arbetsyta')
    raw_receipt = receipt_path.read_bytes()
    receipt = json.loads(raw_receipt)
    if (receipt.get('steg') != steg or Path(receipt.get('kundmapp', '')).resolve() != customer
            or Path(receipt.get('arbetsyta', '')).resolve() != work):
        raise ls.Vagrad('överföringens laddning gäller annan arbetsyta, kund eller steg')
    loaded = {}
    current_sources = {}
    historical_current = {}
    for row in receipt['underlag']:
        if (row['klass'] == 'kund' and row.get('delar', '').startswith('historiskt skaparpaket')
                and row.get('aktuell_sha256')):
            historical_current[row['fil']] = row['aktuell_sha256']
        if row['status'] != 'laddad':
            continue
        path = safe(work, row['plats'])
        raw = path.read_bytes()
        if sha(raw) != row['sha256']:
            raise ls.Vagrad('laddat underlag ändrat: ' + row['plats'])
        if row['klass'] == 'kund':
            loaded[row['plats']] = (row['fil'], raw)
            loaded[row['fil']] = (row['fil'], raw)
            current_sources[row['fil']] = raw
    files = {}
    originals = {}
    referenced = {}
    package_present = False
    protected = protected_inputs(rot, customer, receipt)
    if steg == 'research':
        files['research.md'] = read_work(work, 'research.md')
    else:
        files['PROJECT-BRIEF.md'] = read_work(work, 'PROJECT-BRIEF.md')
    optional = 'VERKSAMHET.json' if steg == 'research' else 'INTEGRATIONSVAL.json'
    if safe(work, optional).exists():
        import integrationer
        import verksamhetsuppgifter as vu
        raw = read_work(work, optional)
        try:
            value = json.loads(raw)
            if steg == 'research':
                vu.validera(value)
                order_path = safe(customer, 'BESTALLNING.json')
                if order_path.is_file():
                    order = json.loads(order_path.read_bytes())
                    if value['namn'] != order['kund'] or bool(value['fiktiv']) != bool(order.get('testfall')):
                        raise ls.Vagrad('verksamhetsutdata ändrar beställningens kund eller fiktiv-status')
            else:
                integrationer.plan(value)
                prova_kundtillval(customer, value)
        except (ValueError, KeyError, TypeError, AttributeError, vu.Vagrad, integrationer.Fel) as e:
            raise ls.Vagrad('ogiltigt valfritt arbetsresultat ' + optional + ': ' + str(e)) from e
        files[optional] = raw
    elif steg == 'brief':
        prova_kundtillval(customer, None)
    if steg == 'brief' and safe(work, ls.SKAPARFIL).exists():
        package_present = True
        original = read_work(work, ls.SKAPARFIL)
        originals[ls.SKAPARFIL] = original
        d = json.loads(original)
        if (not isinstance(d, dict) or not isinstance(d.get('uppdrag'), dict)
                or not isinstance(d.get('bilagor'), list)):
            raise ls.Vagrad('skaparpaket har fel form')
        aliases = {name: canonical for name, (canonical, _) in loaded.items()}
        for row in [d['uppdrag']] + d['bilagor']:
            if not isinstance(row, dict):
                raise ls.Vagrad('skaparpaketets filrad har fel form')
            name = row.get('fil')
            source = safe(work, name)
            if name in loaded and (not source.is_file() or name.startswith('underlag/kund/')):
                canonical, raw = loaded[name]
                aliases[name] = canonical
                row['fil'] = canonical
                referenced[canonical] = raw
            elif (name.casefold() in protected and name not in files
                    or name.split('/')[0].casefold() in ('underlag', 'kundstart', 'intervju', 'evidence', 'overforing')):
                raise ls.Vagrad('filen är varken valt laddat underlag eller tillåtet arbetsresultat: ' + name)
            else:
                raw = read_work(work, name)
            digest = sha(raw)
            if row.get('sha256') not in (None, digest):
                raise ls.Vagrad('modellens filhash stämmer inte: ' + name)
            row['sha256'] = digest
            canonical = row['fil']
            if canonical in files and files[canonical] != raw:
                raise ls.Vagrad('motsägande överföringsfil: ' + name)
            if canonical not in referenced:
                files[canonical] = raw
        for ref in d.get('referenser', []):
            if isinstance(ref, dict) and isinstance(ref.get('bevis'), list):
                ref['bevis'] = [aliases.get(name, name) for name in ref['bevis']]
        files[ls.SKAPARFIL] = (json.dumps(d, ensure_ascii=False, indent=2) + '\n').encode()
        # Same validator as the next ordinary consumer, before customer writes.
        with tempfile.TemporaryDirectory(prefix='paketkontroll-', dir=s['fall']) as tmp:
            stage = Path(tmp)
            for name, raw in {**referenced, **files}.items():
                write(safe(stage, name), raw)
            ls.skaparplan(stage, Path(rot).resolve(), ls.las_pinnar(Path(rot)))
    previous = previous_outputs(s, st, steg)
    for name, raw in referenced.items():
        if safe(customer, name).read_bytes() != raw:
            raise ls.Vagrad('valt laddat underlag är inte längre kundens aktuella bytes; ladda om: ' + name)
    for name, raw in current_sources.items():
        actual = safe(customer, name).read_bytes()
        if actual != raw and actual != files.get(name) and sha(actual) != previous.get(name):
            raise ls.Vagrad('kundkälla ändrad efter laddning: ' + name)
    if any(not raw.strip() for raw in files.values()):
        raise ls.Vagrad('tomt arbetsresultat får inte överföras')
    if len({n.casefold() for n in files}) != len(files):
        raise ls.Vagrad('överföringsfiler krockar i skiftläge')
    binding = {'steg': steg, 'laddning_sha256': sha(raw_receipt),
               'original': {n: sha(b) for n, b in originals.items()},
               'filer': {n: sha(b) for n, b in sorted(files.items())},
               'refererat_laddat': {n: sha(b) for n, b in sorted(referenced.items())},
               'skaparpaket': package_present}
    ident = sha(json.dumps(binding, sort_keys=True).encode())
    history = safe(Path(s['fall']), 'overforing-' + ident)
    journal = safe(history, 'KVITTO.json')
    # Resolve and read every destination before any writes. Never write through links.
    targets = {n: safe(customer, n) for n in files}
    before = {n: p.read_bytes() if p.exists() else None for n, p in targets.items()}
    for name, raw in before.items():
        if (raw is not None and name not in current_sources and raw != files[name]
                and sha(raw) not in (previous.get(name), historical_current.get(name))):
            raise ls.Vagrad('målet har ändrats efter överföring eller fanns inte i laddningen: ' + name
                            + '; markera steget underkand och kör fortsatt för aktuell laddning')
    if journal.exists():
        record = json.loads(journal.read_bytes())
        if record.get('bindning') != binding:
            raise ls.Vagrad('överföringsjournalens bindning har ändrats')
        if safe(history, 'LADDNING.json').read_bytes() != raw_receipt or any(safe(history, 'original/' + n).read_bytes() != b for n, b in originals.items()):
            raise ls.Vagrad('överföringens bevarade original har ändrats')
        for name, raw in before.items():
            digest = sha(raw) if raw is not None else None
            if digest not in (record['fore'][name], binding['filer'][name]):
                raise ls.Vagrad('målet har ändrats efter påbörjad överföring: ' + name)
            old = safe(history, 'fore/' + name)
            if record['fore'][name] is not None and (not old.is_file() or sha(old.read_bytes()) != record['fore'][name]):
                raise ls.Vagrad('överföringens historik har ändrats: ' + name)
    else:
        record = {'schema': 'digitala-stegoverforing/1', 'bindning': binding,
                  'fore': {n: sha(b) if b is not None else None for n, b in before.items()},
                  'lage': 'förberedd', 'sakgodkannande': False}
        for name, raw in before.items():
            if raw is not None:
                write(safe(history, 'fore/' + name), raw)
        for name, raw in originals.items():
            write(safe(history, 'original/' + name), raw)
        write(safe(history, 'LADDNING.json'), raw_receipt)
        write(journal, (json.dumps(record, ensure_ascii=False, indent=2) + '\n').encode())
    # Persist the prepared journal before the first customer write, including
    # process termination. Only bytes bound by that journal count as our output.
    if str(journal) not in st['kvitton']:
        st['kvitton'].append(str(journal))
        if checkpoint is not None:
            checkpoint()
    for name, raw in files.items():
        if before[name] != raw:
            write(targets[name], raw)
    record['lage'] = 'överförd'
    write(journal, (json.dumps(record, ensure_ascii=False, indent=2) + '\n').encode())
    return {'steg': steg, 'lage': record['lage'], 'kvitto': str(journal),
            'filer': binding['filer'], 'sakgodkannande': False}
