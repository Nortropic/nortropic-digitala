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
lika med kodens standardvärden, annars vägras körningen. Kritikens fråga och schema kommer ur den laddade
arbetsytans kopior av kritik/-mallarna; varje {{PLATSHÅLLARE}} fylls med --parameter (avskärmade mallar tillåter inga
parametrar), och en fråga med kvarvarande platshållare vägras. Laddningskvittots hash och
steg binds till körningen (kritik: i frågan; provare: som --bindning; mätning: i KORNING-posten). Varje körning
lämnar FALL/KORNING-<tid>-<profil>-<etikett>.json med argv, körkatalog, utfall och bindning (steg, mandat, beställning,
utförare, kundmapp, repots revision, verktygens hashar, --bindning K=V). Mätprofil, kritikfråga och schema läses ur den
LADDADE arbetsytan (kvittots rader), aldrig ur repots levande filer, och varje laddad fil måste fortfarande ha kvittots
sha256; ett kvitto för fel steg vägras. Kritikens kontextpolicy (KONTEXT) avgör vilka underlag som får följa med: ett
femsekunderstest är avskärmat och får varken kundunderlag eller professionstexter. --torr visar bara kommandot. I bokförd argv, också i --torr, ersätts undantagsfilens sökväg med <undantag-fil>;
själva kommandot körs med den riktiga sökvägen.
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
ETIKETT = re.compile(r'\A[a-z0-9][a-z0-9-]{0,39}\Z')
PLATSHALLARE = re.compile(r'\{\{[A-ZÅÄÖ0-9_]+\}\}')
KRITIKMALLAR = ('designkritik-komp', 'renderingslasning', 'femsekunderstest')
# Kontextpolicy per kritikmall (beviskedjans fynd B): vilka laddade underlag som får följa med i manifestet.
# 'kund' = kundklassens filer (briefen), 'profession' = professionstexter utöver frågan och schemat, 'avskarmad' = en
# förstagångsbedömning som inte får brief, kod, facit eller tidigare kritik; --filer får då bara bära bilder.
KONTEXT = {'designkritik-komp': {'kund': True, 'profession': True, 'avskarmad': False},
           'renderingslasning': {'kund': True, 'profession': True, 'avskarmad': False},
           'femsekunderstest': {'kund': False, 'profession': False, 'avskarmad': True}}
AVSKARMAD_FORBJUDET = re.compile(r'(?i)(?<![a-zåäö])(brief|facit|kritik|svar|riktning|research)(en|et|er|erna|ens|ets|s)?(?![a-zåäö])|\.html?$|\.css$|\.jsx?$|\.tsx?$|\.md$|\.json$|\.txt$')
STEG_FOR_PROFIL = {'matning': 'matning', 'kritik': 'kritik', 'provare': 'provare'}


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


def bind_laddning(receipt, profil):
    """Beviskedjans fynd A: rätt steg, och varje laddad fil har fortfarande kvittots sha256 (annars vägras körningen)."""
    if receipt['steg'] != STEG_FOR_PROFIL[profil]:
        raise Vagrad('laddningskvittot gäller steget %r, profilen %s kräver steget %r' % (receipt['steg'], profil, STEG_FOR_PROFIL[profil]))
    arbetsyta = Path(receipt.get('arbetsyta') or '')
    if not arbetsyta.is_dir():
        raise Vagrad('kvittots arbetsyta finns inte: ' + str(arbetsyta))
    for r in receipt.get('underlag', []):
        if r.get('status') != 'laddad':
            continue
        path = arbetsyta / r['plats']
        if not path.is_file():
            raise Vagrad('laddat underlag saknas i arbetsytan: ' + r['plats'])
        if not r.get('sha256'):
            raise Vagrad('kvittoraden saknar sha256: ' + r['plats'])
        if hashlib.sha256(path.read_bytes()).hexdigest() != r['sha256']:
            raise Vagrad('laddat underlag ändrat sedan kvittot: ' + r['plats'])
    return arbetsyta


def laddad_fil(receipt, fil):
    """En professionsfil ur den laddade arbetsytan, aldrig ur repots levande filer."""
    for r in receipt.get('underlag', []):
        if r.get('fil') == fil and r.get('status') == 'laddad':
            return (Path(receipt['arbetsyta']) / r['plats']).read_text(encoding='utf-8')
    raise Vagrad('underlaget %s är inte laddat i kvittot (steg %s)' % (fil, receipt.get('steg')))


def verktygshashar():
    return {name: hashlib.sha256((ROT / 'verktyg' / name).read_bytes()).hexdigest() for name in kritikbevis.DOMKOD if (ROT / 'verktyg' / name).is_file()}


def bindning_ur(args, receipt, release):
    extra = {}
    for b in (getattr(args, 'bindning', None) or []):
        if '=' not in b:
            raise Vagrad('--bindning är NYCKEL=VÄRDE: ' + b)
        key, value = b.split('=', 1)
        extra[key] = value
    return {'steg': receipt['steg'], 'mandat': receipt.get('mandat'), 'bestallning': receipt.get('bestallning'), 'utforare': getattr(args, 'utforare', None) or receipt.get('utforare'),
            'kundmapp': receipt.get('kundmapp'), 'rot_git_head': receipt.get('rot_git_head'), 'aktiv_release_config': release['config_sha256'], 'verktyg': verktygshashar(), **extra}


def profil(receipt):
    return json.loads(laddad_fil(receipt, 'matning/PROFIL.json'))


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


def bygg_matning(args, release, root, receipt):
    valda = profil(receipt)
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
    fraga = laddad_fil(receipt, 'kritik/FRAGA-%s.md' % args.mall)
    schema = laddad_fil(receipt, 'kritik/SCHEMA-%s.json' % args.mall)
    policy = KONTEXT[args.mall]
    if policy['avskarmad'] and args.parameter:
        raise Vagrad('avskärmad bedömning (%s): inga --parameter tillåts; bedömaren får bara bilderna av det renderade resultatet' % args.mall)
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
    if not isinstance(files, list) or (not files and policy['avskarmad']):
        raise Vagrad('--filer är en JSON-lista av {"kalla","plats","vad"}')
    if policy['avskarmad']:
        for f in files:
            if AVSKARMAD_FORBJUDET.search(str(f.get('plats', ''))) or AVSKARMAD_FORBJUDET.search(str(f.get('kalla', ''))):
                raise Vagrad('avskärmad bedömning (%s): --filer får bara bära bilder av det renderade resultatet, inte %s' % (args.mall, f.get('plats')))
    arbetsyta = Path(receipt['arbetsyta'])
    bilddata = None; bildmap = {}; expected = None
    if not policy['avskarmad']:
        bildtext = laddad_fil(receipt, kritikbevis.BILDFIL)
        bilddata = json.loads(bildtext)
        try:
            kritikbevis.manifest(bilddata, arbetsyta / 'underlag/kund')
        except kritikbevis.Vagrad as e:
            raise Vagrad(str(e)) from e
        kontrakt = laddad_fil(receipt, kritikbevis.KONTRAKT)
        if bilddata['kriterier_sha256'] != hashlib.sha256(kontrakt.encode()).hexdigest():
            raise Vagrad('bildmanifestet gäller annan kriteriefrysning än laddat BEDOMNING-v2')
        bildmap = {b['fil']: b for b in bilddata['bilder']}
        expected = kritikbevis.bindning(bilddata, hashlib.sha256(bildtext.encode()).hexdigest())
        # Inputs cannot silently substitute unbound images for the required set.
        if any(Path(f.get('plats', '')).suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp') for f in files):
            raise Vagrad('kvalificerad kritik laddar bilder ur BEDOMNINGSUNDERLAG; --filer är kompletterande text/mätbevis')
    for r in receipt['underlag']:
        if r['status'] != 'laddad' or r['fil'] in ('kritik/FRAGA-%s.md' % args.mall, 'kritik/SCHEMA-%s.json' % args.mall) or (r['fil'].startswith('kritik/') and r['fil'] != 'kritik/BEDOMNING-v2.md'):
            continue
        if r['klass'] == 'profession' and policy['profession']:
            files.append({'kalla': str(arbetsyta / r['plats']), 'plats': 'UNDERLAG/' + Path(r['plats']).name,
                          'vad': 'professionsunderlag (%s): %s' % (r['fil'], r['delar'][:200])})
        elif r['klass'] == 'kund' and policy['kund'] and r['fil'] in bildmap:
            files.append({'kalla': str(arbetsyta / r['plats']), 'plats': bildmap[r['fil']]['plats'], 'vad': bildmap[r['fil']]['drag']})
        elif r['klass'] == 'kund' and policy['kund']:
            files.append({'kalla': str(arbetsyta / r['plats']), 'plats': 'KUND/' + Path(r['plats']).name,
                          'vad': 'kundunderlag (%s): %s' % (r['fil'], r['delar'][:200])})
    if expected:
        bind_path = Path(args.fall) / ('kritik-' + args.etikett + '-bindning.json')
        if not args.torr:
            if bind_path.exists():raise Vagrad('kritiketiketten har redan en bindning; använd ny etikett för omprov')
            with bind_path.open('x', encoding='utf-8') as out:
                json.dump(expected, out, ensure_ascii=False, indent=1)
        files.append({'kalla': str(bind_path), 'plats': 'UNDERLAG/BEDOMNINGSBINDNING.json', 'vad': 'exakt bedömningsbindning, kopieras till svaret'})
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
    return argv, {'mall': args.mall, 'parametrar': parametrar, 'antal_filer': len(files), 'kontext_policy': policy,
                  'manifest_platser': [f['plats'] for f in files], 'bedomningsbindning': expected, 'bildbedomningsunderlag': bilddata}


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
    common.add_argument('--bindning', action='append', help='NYCKEL=VÄRDE som bokförs i KORNING-posten (t.ex. revision=, driftsattning=)')
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
    args = parser.parse_args(argv)
    if not ETIKETT.match(args.etikett):
        raise Vagrad('--etikett är [a-z0-9-], högst 40 tecken')
    return args


def utan_hemlig_vag(cmd):
    """Bokförd argv: undantagsfilens sökväg ersätts med en platshållare, så att evidensen inte pekar ut hemlighetsfilen."""
    return [('<undantag-fil>' if i > 0 and cmd[i - 1] == '--undantag-fil' else a) for i, a in enumerate(cmd)]


def run(argv=None):
    args = parse(sys.argv[1:] if argv is None else argv)
    fall = Path(args.fall)
    if not fall.is_dir():
        raise Vagrad('fallmappen finns inte: ' + str(fall))
    receipt, laddning_sha = laddning(args.laddning)
    bind_laddning(receipt, args.profil)
    root = runtime_root()
    release = aktiv_release(root)
    if args.profil == 'matning':
        cmd, extra = bygg_matning(args, release, root, receipt)
    elif args.profil == 'kritik':
        cmd, extra = bygg_kritik(args, release, root, receipt, laddning_sha)
    else:
        cmd, extra = bygg_provare(args, release, root, receipt, laddning_sha)
    post = {'schema': 1, 'profil': args.profil, 'etikett': args.etikett, 'laddning': {'fil': str(Path(args.laddning).resolve()),
            'sha256': laddning_sha, 'steg': receipt['steg'], 'sha256_over_underlag': receipt['sha256_over_underlag'],
            'rot_git_head': receipt.get('rot_git_head')}, 'aktiv_release': release, 'argv': utan_hemlig_vag(cmd), 'cwd': release['kod'], 'bindning': bindning_ur(args, receipt, release), **extra}
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
    run_path = Path(post['resultat'].get('run') or '.')
    digest_path=run_path/'KVITTO.sha256'; receipt_path=run_path/'KVITTO.json'
    if digest_path.is_file() and receipt_path.is_file():
        digest=digest_path.read_text().split()[0]
        if digest==hashlib.sha256(receipt_path.read_bytes()).hexdigest():post['runtime_kvitto_sha256']=digest
    if args.profil == 'kritik' and extra.get('bedomningsbindning'):
        run_path = Path(post['resultat'].get('run') or '.')
        try:
            answer = json.loads((run_path / 'svar.json').read_text())
            runtime_receipt = json.loads((run_path / 'KVITTO.json').read_text())
            if not post.get('runtime_kvitto_sha256'):raise ValueError('Runtime-kvittots hash saknas/avviker')
            post['bildbelagg']=kritikbevis.bildbelagg(runtime_receipt)
            post['kvalitetsstatus'] = kritikbevis.dom(answer, extra['bedomningsbindning'], extra['bildbedomningsunderlag'], runtime_receipt)
        except (OSError, ValueError):
            post['kvalitetsstatus'] = 'ej bedömbart: saknat faktiskt svar eller Runtime-kvitto'
    post['stderr_sista'] = done.stderr.strip()[-500:]
    name = 'KORNING-%s-%s-%s.json' % (time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()), args.profil, args.etikett)
    with (fall / name).open('x', encoding='utf-8') as stream:
        json.dump(post, stream, indent=1, ensure_ascii=False)
        stream.write('\n')
    print(json.dumps({'korning': str(fall / name), 'exit': done.returncode, 'resultat': post['resultat'], 'kvalitetsstatus': post.get('kvalitetsstatus')}, ensure_ascii=False))
    return 0 if done.returncode == 0 and post.get('kvalitetsstatus', 'ok') == 'ok' else 1


if __name__ == '__main__':
    try:
        sys.exit(run())
    except Vagrad as error:
        print(json.dumps({'utfall': 'vagrad', 'skal': str(error)}, ensure_ascii=False))
        sys.exit(2)
