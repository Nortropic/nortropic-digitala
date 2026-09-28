#!/usr/bin/env python3
"""Lämnar ett förseglat uppgifts-id till Runtimes privata publiceringshållare.

    python3 -I -B /absolut/primar/nortropic-digitala/verktyg/publicera.py --task ID

Kör den integrerade primäringången, aldrig kandidatens kopia. Kandidaten provas
credential-isolerat och granskas före värdens försegling. Den betrodda hållaren
verifierar uppgift, kandidat, acceptans, helprov, pinnar och separat granskning;
den utfärdar Appbundna kontroller och använder den skyddade PR-/mergevägen.

Detta kommando kör inga kandidatprov, pinnverktyg eller GitHub-anrop, läser inga
nycklar och skapar inga godkännandekvitton. Bara --task får lämnas vidare. Saknad
hållare är en vägran, inte en reservväg genom git/gh. Gammal publiceringssyntax
med gren/granskningskatalog har ersatts och godtas inte.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import stat
import subprocess
import sys


class Vagrad(Exception):
    pass


def systemhem():
    """Värdens fasta ingång följer OS-kontot, inte anroparens HOME/NR_HOST_ROOT."""
    return Path(pwd.getpwuid(os.getuid()).pw_dir)


def privatfil(path):
    """Läs bara ägarens vanliga privata fil; aldrig ett länkat auktoritetsobjekt."""
    try:
        with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise Vagrad('hållarens launcher och adoptionspost måste vara ägarprivata vanliga filer')
            return stream.read()
    except OSError as error:
        raise Vagrad('hållarens privata launcher eller adoptionspost kan inte läsas säkert') from error


def publicera(task):
    if not isinstance(task, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}', task):
        raise Vagrad('task ska vara ett förseglat uppgifts-id: 1–80 små bokstäver, siffror eller bindestreck')
    hem = systemhem()
    repos = hem / 'nortropic-repos'
    primar = repos / 'nortropic-digitala'
    ingang = primar / 'verktyg/publicera.py'
    if (repos.is_symlink() or primar.is_symlink() or (primar / 'verktyg').is_symlink()
            or ingang.is_symlink() or Path(__file__).resolve() != ingang):
        raise Vagrad('kör publicera.py från den integrerade primäringången, inte från kandidatens kopia')
    host = repos / 'Nortropic Runtime'
    private = host / '.runtime/ap11/check-issuer'
    launcher = private / 'launch.py'
    python = host / '.runtime/temporal-venv/bin/python'
    if (any(p.is_symlink() for p in (host, host / '.runtime', host / '.runtime/ap11', private, launcher))
            or not launcher.is_file() or not python.is_file()):
        raise Vagrad('den fasta privata publiceringshållaren saknas eller har en otillåten länk; värden måste bereda den')
    info = private.stat()
    if info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise Vagrad('publiceringshållarens katalog måste vara ägarprivat')
    launcher_bytes = privatfil(launcher)
    try:
        adoption = json.loads(privatfil(private / 'launcher-adoption.json'))
    except (ValueError, UnicodeError) as error:
        raise Vagrad('hållarens launcher-adoptionspost är inte ett giltigt JSON-objekt') from error
    if (not isinstance(adoption, dict) or adoption.get('schema') != 'nortropic-launcher-adoption/1'
            or adoption.get('verdict') != 'approved' or adoption.get('blocking_findings') != []
            or not isinstance(adoption.get('reviewer_run'), str) or not adoption['reviewer_run'].strip()
            or not isinstance(adoption.get('implementation_run'), str) or not adoption['implementation_run'].strip()
            or adoption['reviewer_run'] == adoption['implementation_run']
            or adoption.get('launcher_sha256') != hashlib.sha256(launcher_bytes).hexdigest()):
        raise Vagrad('launchern saknar separat godkänd adoption för exakt dessa bytes')
    # No candidate-selected path, executable, auth or Python/Git override reaches
    # the holder. Its own sealed authority determines all publication inputs.
    environment = {'PATH': '/opt/homebrew/bin:/usr/bin:/bin', 'HOME': str(hem),
                   'LANG': 'C', 'LC_ALL': 'C', 'GIT_CONFIG_NOSYSTEM': '1',
                   'PYTHONDONTWRITEBYTECODE': '1'}
    result = subprocess.run([str(python), '-I', '-B', str(launcher), 'digitala', '--task', task],
                            cwd=host, env=environment, stdin=subprocess.DEVNULL, close_fds=True)
    return result.returncode if result.returncode >= 0 else 128 - result.returncode


def main(argv=None):
    parser = argparse.ArgumentParser(prog='publicera', description=__doc__.split('\n\n')[0], allow_abbrev=False)
    parser.add_argument('--task', required=True, help='id för värdens förseglade publiceringsuppgift')
    args = parser.parse_args(argv)
    try:
        return publicera(args.task)
    except (Vagrad, OSError) as error:
        print(json.dumps({'vagrad': str(error)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    sys.exit(main())
