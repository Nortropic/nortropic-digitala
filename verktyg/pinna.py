"""Räknar versionspinnar (sha256) för varje professionsfil som steg/steg.json namnger.

    python3 -B verktyg/pinna.py            visar skillnaden mot steg/PINNAR.sha256
    python3 -B verktyg/pinna.py --skriv    skriver steg/PINNAR.sha256 (ett nytt beslut; committas)
"""
import json
from pathlib import Path
import sys

ROT = Path(__file__).resolve().parents[1]


def pinnar(rot=ROT):
    data = json.loads((rot / 'steg/steg.json').read_text(encoding='utf-8'))
    files = sorted({item['fil'] for step in data['steg'].values() for item in step['underlag'] if item['klass'] == 'profession'})
    result = {}
    for rel in files:
        path = rot / rel
        if not path.is_file():
            raise SystemExit('saknad professionsfil: ' + rel)
        import hashlib
        result[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def main(argv):
    new = pinnar()
    target = ROT / 'steg/PINNAR.sha256'
    old = {}
    if target.is_file():
        for line in target.read_text(encoding='utf-8').splitlines():
            if line.strip() and not line.startswith('#'):
                digest, rel = line.split('  ', 1)
                old[rel] = digest
    changed = sorted(rel for rel in set(old) | set(new) if old.get(rel) != new.get(rel))
    for rel in changed:
        print('%s: %s -> %s' % (rel, (old.get(rel) or 'saknas')[:12], (new.get(rel) or 'borttagen')[:12]))
    if '--skriv' in argv:
        target.write_text('# sha256  fil — versionspinnar för professionsunderlag; ändras bara som nytt beslut (verktyg/pinna.py --skriv)\n'
                          + ''.join('%s  %s\n' % (new[rel], rel) for rel in sorted(new)), encoding='utf-8')
        print('skrev', len(new), 'pinnar')
    elif not changed:
        print('inga skillnader; %d pinnar' % len(new))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
