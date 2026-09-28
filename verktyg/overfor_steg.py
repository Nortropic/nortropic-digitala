"""Bytebunden lokal överföring av research/brief från ordinarie laddad arbetsyta.

Ingen sakbedömning eller stegaccept. Modellens original bevaras; bara null-hashar
beräknas. Ett återupptaget, delvis skrivet paket får samma journal och bytes.
"""
import hashlib
import json
import os
from pathlib import Path
import tempfile

import ladda_steg as ls


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def safe(root, name):
    if not isinstance(name, str) or not ls.FIL.fullmatch(name):
        raise ls.Vagrad('ogiltig överföringssökväg')
    path = ls.utan_lankar(root / name, root)
    if not ls.inuti(path, root):
        raise ls.Vagrad('överföringssökväg lämnar sin katalog')
    return path


def write(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, tmp = tempfile.mkstemp(prefix='.overfor-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def transfer(s, steg, rot):
    if steg not in ('research', 'brief'):
        raise ls.Vagrad('överföring stöder research eller brief')
    st = s['steg'][steg]
    receipt_path = Path(st['laddning'])
    work = receipt_path.parent.resolve()
    customer = Path(s['kund']).resolve()
    raw_receipt = receipt_path.read_bytes()
    receipt = json.loads(raw_receipt)
    if (receipt.get('steg') != steg or Path(receipt.get('kundmapp', '')).resolve() != customer
            or Path(receipt.get('arbetsyta', '')).resolve() != work):
        raise ls.Vagrad('överföringens laddning gäller annan arbetsyta, kund eller steg')
    loaded = {}
    current_sources = {}
    for row in receipt['underlag']:
        if row['status'] != 'laddad':
            continue
        path = safe(work, row['plats'])
        raw = path.read_bytes()
        if sha(raw) != row['sha256']:
            raise ls.Vagrad('laddat underlag ändrat: ' + row['plats'])
        if row['klass'] == 'kund':
            loaded[row['plats']] = raw
            loaded[row['fil']] = raw
            current_sources[row['fil']] = raw
    files = {}
    originals = {}
    if steg == 'research':
        files['research.md'] = safe(work, 'research.md').read_bytes()
    else:
        original = safe(work, ls.SKAPARFIL).read_bytes()
        originals[ls.SKAPARFIL] = original
        d = json.loads(original)
        if (not isinstance(d, dict) or not isinstance(d.get('uppdrag'), dict)
                or not isinstance(d.get('bilagor'), list)):
            raise ls.Vagrad('skaparpaket har fel form')
        files['PROJECT-BRIEF.md'] = safe(work, 'PROJECT-BRIEF.md').read_bytes()
        protected = {'BESTALLNING.json', 'VERKSAMHET.json', 'INTERVJU.json', 'KUNDSTART.json',
                     'KUNDSTART-ARBETSUPPGIFT.json', 'KANALBEHOV.json', 'BEVISKRAV.json',
                     'LAGE.json', 'LADDNING.json', ls.SKAPARFIL, 'SKAPARPAKET.md',
                     'research-intervju.md', 'research.md', 'INTEGRATIONSVAL.json'}
        for row in [d['uppdrag']] + d['bilagor']:
            if not isinstance(row, dict):
                raise ls.Vagrad('skaparpaketets filrad har fel form')
            name = row.get('fil')
            source = safe(work, name)
            if name in loaded and not source.is_file():
                raw = loaded[name]
            elif name in loaded and name.startswith('underlag/kund/'):
                raw = loaded[name]
            elif name in protected or name.split('/')[0] in ('underlag', 'KUNDSTART'):
                raise ls.Vagrad('filen är varken valt laddat underlag eller tillåtet arbetsresultat: ' + name)
            else:
                raw = source.read_bytes()
            digest = sha(raw)
            if row.get('sha256') not in (None, digest):
                raise ls.Vagrad('modellens filhash stämmer inte: ' + name)
            row['sha256'] = digest
            if name in files and files[name] != raw:
                raise ls.Vagrad('motsägande överföringsfil: ' + name)
            files[name] = raw
        files[ls.SKAPARFIL] = (json.dumps(d, ensure_ascii=False, indent=2) + '\n').encode()
        # Same validator as the next ordinary consumer, before customer writes.
        with tempfile.TemporaryDirectory(prefix='paketkontroll-', dir=s['fall']) as tmp:
            stage = Path(tmp)
            for name, raw in files.items():
                write(safe(stage, name), raw)
            ls.skaparplan(stage, Path(rot).resolve(), ls.las_pinnar(Path(rot)))
    for name, raw in current_sources.items():
        actual = safe(customer, name).read_bytes()
        own_output = name == ('research.md' if steg == 'research' else 'PROJECT-BRIEF.md')
        if actual != raw and not (own_output and actual == files.get(name)):
            raise ls.Vagrad('kundkälla ändrad efter laddning: ' + name)
    if any(not raw.strip() for raw in files.values()):
        raise ls.Vagrad('tomt arbetsresultat får inte överföras')
    binding = {'steg': steg, 'laddning_sha256': sha(raw_receipt),
               'original': {n: sha(b) for n, b in originals.items()},
               'filer': {n: sha(b) for n, b in sorted(files.items())}}
    ident = sha(json.dumps(binding, sort_keys=True).encode())
    history = Path(s['fall']) / ('overforing-' + ident)
    journal = history / 'KVITTO.json'
    # Resolve and read every destination before any writes. Never write through links.
    targets = {n: safe(customer, n) for n in files}
    before = {n: p.read_bytes() if p.exists() else None for n, p in targets.items()}
    if journal.exists():
        record = json.loads(journal.read_bytes())
        if record.get('bindning') != binding:
            raise ls.Vagrad('överföringsjournalens bindning har ändrats')
        if (history / 'LADDNING.json').read_bytes() != raw_receipt or any((history / 'original' / n).read_bytes() != b for n, b in originals.items()):
            raise ls.Vagrad('överföringens bevarade original har ändrats')
        for name, raw in before.items():
            digest = sha(raw) if raw is not None else None
            if digest not in (record['fore'][name], binding['filer'][name]):
                raise ls.Vagrad('målet har ändrats efter påbörjad överföring: ' + name)
            old = history / 'fore' / name
            if record['fore'][name] is not None and (not old.is_file() or sha(old.read_bytes()) != record['fore'][name]):
                raise ls.Vagrad('överföringens historik har ändrats: ' + name)
    else:
        record = {'schema': 'digitala-stegoverforing/1', 'bindning': binding,
                  'fore': {n: sha(b) if b is not None else None for n, b in before.items()},
                  'lage': 'förberedd', 'sakgodkannande': False}
        for name, raw in before.items():
            if raw is not None:
                write(history / 'fore' / name, raw)
        for name, raw in originals.items():
            write(history / 'original' / name, raw)
        write(history / 'LADDNING.json', raw_receipt)
        write(journal, (json.dumps(record, ensure_ascii=False, indent=2) + '\n').encode())
    for name, raw in files.items():
        if before[name] != raw:
            write(targets[name], raw)
    record['lage'] = 'överförd'
    write(journal, (json.dumps(record, ensure_ascii=False, indent=2) + '\n').encode())
    return {'steg': steg, 'lage': record['lage'], 'kvitto': str(journal),
            'filer': binding['filer'], 'sakgodkannande': False}
