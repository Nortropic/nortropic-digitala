"""Kör Runtimes webbprofiler som den aktiva releasens egen kopia, med Digitalas val, bundet till laddningskvittot.

    python3 -B verktyg/kor_profil.py matning --laddning LADDNING.json --fall FALL --etikett NAMN (--mal URL | --fil PATH)
        [--sektioner N] [--handling-text TEXT] [--handling-selektor CSS] [--undantag-fil FIL] [--torr]
    python3 -B verktyg/kor_profil.py kritik --laddning LADDNING.json --fall FALL --etikett NAMN --mall NAMN
        --filer FILER.json --utforare claude|codex --modell NAMN [--parameter NYCKEL=VÄRDE ...] [--tid SEK] [--torr]
    python3 -B verktyg/kor_profil.py provare --laddning LADDNING.json --fall FALL --etikett NAMN --start URL
        --tillatna ORIGIN[,ORIGIN] --uppgift FIL --vy mobil|desktop --utforare claude|codex --modell NAMN
        [--max-handlingar N] [--tid SEK] [--undantag-fil FIL] [--bindning K=V ...] [--torr]

Runtime hittas genom NR_HOST_ROOT eller systerkatalogen "Nortropic Runtime"; den aktiva releasen läses ur
.runtime/ap10/active.json, och profilen körs ur releasens egen kod. Mätningens vyer och axe-taggar kommer ur
matning/PROFIL.json: tar den aktiva koden dem som parametrar (--vyer, --axe-taggar) skickas de, annars måste de vara
lika med kodens standardvärden, annars vägras körningen. Kritikens fråga och schema kommer ur kritik/; varje
{{PLATSHÅLLARE}} fylls med --parameter, och en fråga med kvarvarande platshållare vägras. Laddningskvittots hash och
steg binds till körningen (kritik: i frågan; provare: som --bindning; mätning: i KORNING-posten). Varje körning
lämnar FALL/KORNING-<tid>-<profil>-<etikett>.json med argv, körkatalog och utfall. --torr visar bara kommandot.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROT = Path(__file__).resolve().parents[1]
ETIKETT = re.compile(r'\A[a-z0-9][a-z0-9-]{0,39}\Z')
PLATSHALLARE = re.compile(r'\{\{[A-ZÅÄÖ0-9_]+\}\}')
KRITIKMALLAR = ('designkritik-komp', 'renderingslasning', 'femsekunderstest')


class Vagrad(Exception):
    pass


def runtime_root():
    root = Path(os.environ.get('NR_HOST_ROOT') or (ROT.parent / 'Nortropic Runtime')).resolve()
    if not (root / '.runtime/ap10/active.json').is_file():
        raise Vagrad('Runtime hittas inte (sätt NR_HOST_ROOT): ' + str(root))
    return root


def aktiv_release(root):
    active = json.loads((root / '.runtime/ap10/active.json').read_text())
    config = Path(active['config'])
    if hashlib.sha256(config.read_bytes()).hexdigest() != active['sha256']:
        raise Vagrad('active.json pekar på en konfiguration med annan sha256')
    code = config.parent / 'runtime'
    if not (code / 'runtime/web_measure.py').is_file():
        raise Vagrad('den aktiva releasen saknar webbprofilerna: ' + str(code))
    return {'config': str(config), 'config_sha256': active['sha256'], 'kod': str(code),
            'python': str(root / '.runtime/temporal-venv/bin/python')}


def miljo(root):
    env = {k: v for k, v in os.environ.items() if k in ('PATH', 'HOME', 'USER', 'LOGNAME', 'TMPDIR')}
    env.update(NR_HOST_ROOT=str(root), LC_ALL='C', LANG='C', PYTHONDONTWRITEBYTECODE='1')
    return env


def laddning(path):
    receipt = json.loads(Path(path).read_text(encoding='utf-8'))
    if receipt.get('schema') != 1 or not receipt.get('steg') or not receipt.get('sha256_over_underlag'):
        raise Vagrad('laddningskvittot har fel form')
    return receipt, hashlib.sha256(Path(path).read_bytes()).hexdigest()


def profil():
    return json.loads((ROT / 'matning/PROFIL.json').read_text(encoding='utf-8'))


def kodens_matvarden(release, root):
    """Vad den aktiva koden faktiskt fryser, läst genom att importera den — inte gissat ur en fil."""
    probe = ('import json, runtime.web_measure as m; print(json.dumps({"viewports": m.VIEWPORTS, "axe_tags": m.AXE_TAGS,'
             ' "parametrar": bool(getattr(m, "PARAMETRAR", ()))}))')
    done = subprocess.run([release['python'], '-B', '-c', probe], cwd=release['kod'], env=miljo(root),
                          capture_output=True, text=True, timeout=60)
    if done.returncode != 0:
        raise Vagrad('kunde inte läsa den aktiva mätprofilens värden: ' + done.stderr.strip()[-300:])
    return json.loads(done.stdout.strip().splitlines()[-1])


def vyer_argument(vyer):
    parts = []
    for name, spec in vyer.items():
        parts.append('%s=%dx%d@%d%s' % (name, spec['width'], spec['height'], spec['deviceScaleFactor'], 'm' if spec.get('isMobile') else 'd'))
    return ','.join(parts)


def bygg_matning(args, release, root):
    valda = profil()
    kod = kodens_matvarden(release, root)
    argv = [release['python'], '-B', '-m', 'runtime.web_measure', '--etikett', args.etikett,
            '--sektioner', str(args.sektioner if args.sektioner is not None else valda['sektioner']),
            '--delar', ','.join(valda['delar'])]
    argv += ['--mal', args.mal] if args.mal else ['--fil', args.fil]
    if args.handling_text:
        argv += ['--handling-text', args.handling_text]
    if args.handling_selektor:
        argv += ['--handling-selektor', args.handling_selektor]
    if args.undantag_fil:
        argv += ['--undantag-fil', args.undantag_fil]
    lika = kod['viewports'] == valda['vyer'] and kod['axe_tags'] == valda['axe_taggar']
    if kod['parametrar']:
        argv += ['--vyer', vyer_argument(valda['vyer']), '--axe-taggar', ','.join(valda['axe_taggar'])]
        hur = 'Digitalas vyer och axe-taggar skickade som parametrar'
    elif lika:
        hur = 'den aktiva koden tar inga parametrar; Digitalas val är lika med kodens standardvärden'
    else:
        raise Vagrad('Digitalas vyer eller axe-taggar skiljer sig från den aktiva mätprofilens frysta värden och koden tar '
                     'inga parametrar (kräver Runtime D037 aktiv); körningen vägras')
    return argv, {'profil_val': valda, 'kodens_varden': kod, 'hur': hur}


def bygg_kritik(args, release, root, receipt, laddning_sha):
    if args.mall not in KRITIKMALLAR:
        raise Vagrad('okänd mall; kända: ' + ', '.join(KRITIKMALLAR))
    fraga = (ROT / ('kritik/FRAGA-%s.md' % args.mall)).read_text(encoding='utf-8')
    schema = (ROT / ('kritik/SCHEMA-%s.json' % args.mall)).read_text(encoding='utf-8')
    parametrar = {}
    for item in args.parameter or []:
        if '=' not in item:
            raise Vagrad('--parameter är NYCKEL=VÄRDE: ' + item)
        key, value = item.split('=', 1)
        parametrar[key] = value
    for key, value in parametrar.items():
        fraga = fraga.replace('{{%s}}' % key, value)
    rest = sorted(set(PLATSHALLARE.findall(fraga)))
    if rest:
        raise Vagrad('frågan har ofyllda platshållare: ' + ', '.join(rest))
    files = json.loads(Path(args.filer).read_text(encoding='utf-8'))
    if not isinstance(files, list) or not files:
        raise Vagrad('--filer är en JSON-lista av {"kalla","plats","vad"}')
    arbetsyta = Path(receipt['arbetsyta'])
    for r in receipt['underlag']:
        if r['status'] == 'laddad' and r['klass'] == 'profession':
            files.append({'kalla': str(arbetsyta / r['plats']), 'plats': 'UNDERLAG/' + Path(r['plats']).name,
                          'vad': 'professionsunderlag (%s): %s' % (r['fil'], r['delar'][:200])})
        elif r['status'] == 'laddad':
            files.append({'kalla': str(arbetsyta / r['plats']), 'plats': 'KUND/' + Path(r['plats']).name,
                          'vad': 'kundunderlag (%s): %s' % (r['fil'], r['delar'][:200])})
    fraga += '\n\nBindning: laddningskvitto %s (steg %s), sha256 %s.\n' % (laddning_sha[:16], receipt['steg'], receipt['sha256_over_underlag'][:16])
    fall = Path(args.fall)
    stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    fraga_path = fall / ('kritik-%s-%s-fraga.md' % (args.etikett, stamp))
    schema_path = fall / ('kritik-%s-%s-schema.json' % (args.etikett, stamp))
    manifest_path = fall / ('kritik-%s-%s-underlag.json' % (args.etikett, stamp))
    if not args.torr:
        fraga_path.write_text(fraga, encoding='utf-8')
        schema_path.write_text(schema, encoding='utf-8')
        manifest_path.write_text(json.dumps({'filer': files}, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    argv = [release['python'], '-B', '-m', 'runtime.web_critique', '--underlag', str(manifest_path), '--fraga', str(fraga_path),
            '--schema', str(schema_path), '--utforare', args.utforare, '--modell', args.modell, '--etikett', args.etikett]
    if args.tid:
        argv += ['--tid', str(args.tid)]
    return argv, {'mall': args.mall, 'parametrar': parametrar, 'antal_filer': len(files)}


def bygg_provare(args, release, root, receipt, laddning_sha):
    uppgift = Path(args.uppgift).read_text(encoding='utf-8')
    rest = sorted(set(PLATSHALLARE.findall(uppgift)))
    if rest:
        raise Vagrad('uppgiften har ofyllda platshållare: ' + ', '.join(rest))
    if 'Startadress:' not in uppgift or 'handlingskommando' not in uppgift:
        raise Vagrad('uppgiften saknar Startadress eller handlingskommando (L18)')
    argv = [release['python'], '-B', '-m', 'runtime.web_visitor', '--start', args.start, '--tillatna', args.tillatna,
            '--uppgift', str(Path(args.uppgift).resolve()), '--vy', args.vy, '--utforare', args.utforare, '--modell', args.modell,
            '--etikett', args.etikett]
    if args.max_handlingar:
        argv += ['--max-handlingar', str(args.max_handlingar)]
    if args.tid:
        argv += ['--tid', str(args.tid)]
    if args.undantag_fil:
        argv += ['--undantag-fil', args.undantag_fil]
    for b in (args.bindning or []):
        argv += ['--bindning', b]
    argv += ['--bindning', 'laddning=' + laddning_sha[:16], '--bindning', 'steg=' + receipt['steg']]
    return argv, {}


def parse(argv):
    parser = argparse.ArgumentParser(prog='kor_profil', description=__doc__.split('\n\n')[0])
    sub = parser.add_subparsers(dest='profil', required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--laddning', required=True)
    common.add_argument('--fall', required=True)
    common.add_argument('--etikett', required=True)
    common.add_argument('--torr', action='store_true')
    m = sub.add_parser('matning', parents=[common])
    where = m.add_mutually_exclusive_group(required=True)
    where.add_argument('--mal')
    where.add_argument('--fil')
    m.add_argument('--sektioner', type=int)
    m.add_argument('--handling-text')
    m.add_argument('--handling-selektor')
    m.add_argument('--undantag-fil')
    k = sub.add_parser('kritik', parents=[common])
    k.add_argument('--mall', required=True)
    k.add_argument('--filer', required=True)
    k.add_argument('--utforare', choices=('claude', 'codex'), required=True)
    k.add_argument('--modell', required=True)
    k.add_argument('--parameter', action='append')
    k.add_argument('--tid', type=int)
    p = sub.add_parser('provare', parents=[common])
    p.add_argument('--start', required=True)
    p.add_argument('--tillatna', required=True)
    p.add_argument('--uppgift', required=True)
    p.add_argument('--vy', choices=('mobil', 'desktop'), required=True)
    p.add_argument('--utforare', choices=('claude', 'codex'), required=True)
    p.add_argument('--modell', required=True)
    p.add_argument('--max-handlingar', type=int)
    p.add_argument('--tid', type=int)
    p.add_argument('--undantag-fil')
    p.add_argument('--bindning', action='append')
    args = parser.parse_args(argv)
    if not ETIKETT.match(args.etikett):
        raise Vagrad('--etikett är [a-z0-9-], högst 40 tecken')
    return args


def run(argv=None):
    args = parse(sys.argv[1:] if argv is None else argv)
    fall = Path(args.fall)
    if not fall.is_dir():
        raise Vagrad('fallmappen finns inte: ' + str(fall))
    if not shutil.which('git'):
        pass
    receipt, laddning_sha = laddning(args.laddning)
    root = runtime_root()
    release = aktiv_release(root)
    if args.profil == 'matning':
        cmd, extra = bygg_matning(args, release, root)
    elif args.profil == 'kritik':
        cmd, extra = bygg_kritik(args, release, root, receipt, laddning_sha)
    else:
        cmd, extra = bygg_provare(args, release, root, receipt, laddning_sha)
    post = {'schema': 1, 'profil': args.profil, 'etikett': args.etikett, 'laddning': {'fil': str(Path(args.laddning).resolve()),
            'sha256': laddning_sha, 'steg': receipt['steg'], 'sha256_over_underlag': receipt['sha256_over_underlag'],
            'rot_git_head': receipt.get('rot_git_head')}, 'aktiv_release': release, 'argv': cmd, 'cwd': release['kod'], **extra}
    if args.torr:
        print(json.dumps({**post, 'torr': True}, ensure_ascii=False, indent=1))
        return 0
    post['startad_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    began = time.monotonic()
    done = subprocess.run(cmd, cwd=release['kod'], env=miljo(root), capture_output=True, text=True)
    post['sekunder'] = round(time.monotonic() - began, 1)
    post['exit'] = done.returncode
    last = (done.stdout.strip().splitlines() or [''])[-1]
    try:
        post['resultat'] = json.loads(last)
    except ValueError:
        post['resultat'] = {'ra': last[:500]}
    post['stderr_sista'] = done.stderr.strip()[-500:]
    name = 'KORNING-%s-%s-%s.json' % (time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()), args.profil, args.etikett)
    with (fall / name).open('x', encoding='utf-8') as stream:
        json.dump(post, stream, indent=1, ensure_ascii=False)
        stream.write('\n')
    print(json.dumps({'korning': str(fall / name), 'exit': done.returncode, 'resultat': post['resultat']}, ensure_ascii=False))
    return 0 if done.returncode == 0 else 1


if __name__ == '__main__':
    try:
        sys.exit(run())
    except Vagrad as error:
        print(json.dumps({'utfall': 'vagrad', 'skal': str(error)}, ensure_ascii=False))
        sys.exit(2)
