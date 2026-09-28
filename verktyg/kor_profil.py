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
import contextlib
import tempfile
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


def bind_bildschema(schema_text, bilddata):
    """Begränsa den laddade mallen till det verifierade manifestet, före Runtime-start.

    Runtime stöder enum men inte villkorliga scheman. Proveniensvärden begränsas
    därför per roll; kritikbevis.dom kontrollerar fortsatt att de hör till SAMMA bild.
    Inga modellsvar eller kvalitetskriterier ändras här.
    """
    schema = json.loads(schema_text)

    def bind_enum(node, values):
        values = sorted(set(values))
        if (node.get('type') != 'string' or not values
                or any(not isinstance(v, str) or len(v) > node.get('maxLength', len(v)) for v in values)
                or ('enum' in node and not set(values) <= set(node['enum']))):
            raise Vagrad('bildmanifestet ryms inte i den laddade schemamallen')
        node['enum'] = values

    try:
        candidates = [b['plats'] for b in bilddata['bilder'] if b['roll'] == 'kandidat']
        for field, role, image_key in (('referensjamforelser', 'referens', 'referensbild'),
                                        ('dagensjamforelser', 'dagens', 'dagensbild')):
            array = schema['properties'][field]
            if array.get('type') != 'array' or array['items'].get('type') != 'object':
                raise Vagrad('den laddade schemamallen saknar jämförelseobjekt')
            props = array['items']['properties']
            bind_enum(props['kandidatbild'], candidates)
            images = [b for b in bilddata['bilder'] if b['roll'] == role]
            if not images:
                # Inga DAGENS-bilder: tom lista, aldrig en påhittad bild eller tom enum.
                if role != 'dagens' or array.get('minItems', 0) > 0:
                    raise Vagrad('den laddade schemamallen kräver saknade jämförelsebilder')
                array['maxItems'] = 0
                continue
            bind_enum(props[image_key], [b['plats'] for b in images])
            for key in ('kalla', 'tid', 'vy'):
                bind_enum(props[key], [b[key] for b in images])
    except (KeyError, TypeError) as e:
        raise Vagrad('den laddade schemamallen saknar bild-/proveniensfält') from e
    return json.dumps(schema, ensure_ascii=False, indent=2) + '\n'


def bind_sedda_filer(schema_text, files):
    """Exakta paketplatser, inte bevis på läsning. Körs efter hela underlagsbygget.

    Runtime web_critique.build_workspace tillför FILES.md och AGENTS.md;
    load_manifest reserverar samma namn. Inga andra automatiska filer antas.
    """
    schema = json.loads(schema_text)
    try:
        node = schema['properties']['seen_files']['items']
        places = sorted({f['plats'] for f in files} | {'FILES.md', 'AGENTS.md'})
        if (not isinstance(node, dict) or node.get('type') != 'string'
                or any(not isinstance(p, str) or len(p) > node.get('maxLength', len(p)) for p in places)
                or ('enum' in node and not set(places) <= set(node['enum']))):
            raise Vagrad('paketplatserna ryms inte i den laddade seen_files-mallen')
        node['enum'] = places
    except (KeyError, TypeError) as e:
        raise Vagrad('den laddade schemamallen saknar seen_files-items') from e
    return json.dumps(schema, ensure_ascii=False, indent=2) + '\n'


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
        schema = bind_bildschema(schema, bilddata)
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
        schema = bind_sedda_filer(schema, files)
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
                  'schema_sha256': hashlib.sha256(schema.encode()).hexdigest(),
                  'manifest_platser': [f['plats'] for f in files], 'bedomningsbindning': expected, 'bildbedomningsunderlag': bilddata}


@contextlib.contextmanager
def historisk_domkod(post):
    """No historical Python is imported. Current semantic code must be byte-identical.

    Older wrapper/loading bytes are only hashed in an isolated evidence directory,
    so adding this orchestration cannot silently replace the original bound verdict code.
    """
    revision = (post.get('bindning') or {}).get('rot_git_head', '')
    hashes = (post.get('bindning') or {}).get('verktyg') or {}
    expected = (post.get('bedomningsbindning') or {}).get('domkod_sha256')
    if not re.fullmatch(r'[0-9a-f]{40}', revision) or set(hashes) != set(kritikbevis.DOMKOD):
        raise Vagrad('historisk domkod kräver exakt commit och samtliga ursprungliga kodhashar')
    # These are the only modules that execute for the historical semantic check.
    for name in ('kritikbevis.py', 'stegbevis.py'):
        if hashlib.sha256((ROT / 'verktyg' / name).read_bytes()).hexdigest() != hashes.get(name):
            raise Vagrad('semantisk domkod har ändrats; historisk formåterhämtning kräver ny sakprövning')
    with tempfile.TemporaryDirectory(prefix='digitala-domhash-') as temporary:
        snapshot = Path(temporary)
        for relative in ['steg/DOMKOD.sha256'] + ['verktyg/' + n for n in kritikbevis.DOMKOD]:
            done = subprocess.run(['git', '-C', str(ROT), 'show', revision + ':' + relative], capture_output=True)
            if done.returncode:
                raise Vagrad('ursprunglig domkod saknas i lokal Git-historik')
            digest = hashlib.sha256(done.stdout).hexdigest()
            if digest != (expected if relative == 'steg/DOMKOD.sha256' else hashes[Path(relative).name]):
                raise Vagrad('historisk domkod avviker från ursprunglig bindning')
            target = snapshot / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(done.stdout)
        original_root = kritikbevis.ROT
        try:
            kritikbevis.ROT = snapshot
            if kritikbevis.domkod() != expected:
                raise Vagrad('historisk domkodspin stämmer inte')
            yield
        finally:
            kritikbevis.ROT = original_root


def aterhamtningskalla(post):
    meta = post.get('formaterhamtning') or {}
    path = Path(meta.get('korning') or '')
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != meta.get('sha256'):
        raise Vagrad('ursprunglig KORNING saknas eller har ändrats')
    original = json.loads(path.read_text())
    if original.get('formaterhamtning') or original.get('profil') != 'kritik' or original.get('mall') != 'renderingslasning':
        raise Vagrad('formåterhämtning kräver ursprunglig renderingsläsning, inte en återhämtningskedja')
    for key in ('laddning', 'bedomningsbindning', 'bildbedomningsunderlag'):
        if post.get(key) != original.get(key):
            raise Vagrad('återhämtningens ' + key + ' skiljer från originalet')
    return original


def kontrollera_aterhamtningsbevis(post, run, kvitto, svar):
    """The new answer preserves every protected value and its exact original source."""
    if not post.get('formaterhamtning'):
        return
    original_post = aterhamtningskalla(post)
    provenance = kvitto.get('format_recovery') or {}
    oldrun = Path(original_post['resultat']['run'])
    if (provenance.get('source_receipt_sha256') != original_post.get('runtime_kvitto_sha256')
            or Path(provenance.get('source_run') or '').resolve() != oldrun.resolve()
            or provenance.get('changed_fields') != ['summary'] or provenance.get('images_reopened') != 0
            or provenance.get('error') is not None):
        raise Vagrad('formåterhämtning saknar samma källkvitto eller avgränsning')
    if hashlib.sha256((oldrun / 'KVITTO.json').read_bytes()).hexdigest() != original_post['runtime_kvitto_sha256']:
        raise Vagrad('ursprungligt Runtime-kvitto har ändrats')
    required = ['original-svar.json', 'FORMATERHAMTNING.json']
    for directory in ('formrattning', 'innebordskontroll'):
        required += [directory + '/' + name for name in ('svar.json', 'SESSION.json', 'strom.jsonl', 'start.json', 'fraga.txt', 'schema.json')]
    for name in required:
        path = Path(run) / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != kvitto.get('outputs', {}).get(name, {}).get('sha256'):
            raise Vagrad('formåterhämtningens bundna bevis saknas/ändrat: ' + name)
    original = json.loads((Path(run) / 'original-svar.json').read_text())
    if not isinstance(svar, dict) or set(original) != set(svar) or any(svar[k] != v for k, v in original.items() if k != 'summary'):
        raise Vagrad('formåterhämtning har ändrat dom, fynd, risk eller bevisfält')
    attempts = []
    for line in (oldrun / 'strom.jsonl').read_text().splitlines():
        row = json.loads(line); message = row.get('message')
        if isinstance(message, dict):
            attempts += [b.get('input') for b in message.get('content', []) if isinstance(b, dict) and b.get('name') == 'StructuredOutput']
    if attempts != [original]:
        raise Vagrad('bevarat råobjekt skiljer från ursprungligt komplett svarsförsök')
    patch = json.loads((Path(run) / 'formrattning/svar.json').read_text())
    audit = json.loads((Path(run) / 'innebordskontroll/svar.json').read_text())
    if patch != {'summary': svar['summary']} or audit.get('preserved') is not True or audit.get('lost_or_changed') != []:
        raise Vagrad('formrättning eller separat innebördskontroll stämmer inte')
    sessions = provenance.get('sessions') or []
    if len(sessions) != 2 or any(s.get('valid_terminal') is not True or s.get('images') != 0 for s in sessions):
        raise Vagrad('båda nya textsessionernas kvalificerade terminaler krävs')


@contextlib.contextmanager
def domkontext(post):
    if post.get('formaterhamtning'):
        with historisk_domkod(aterhamtningskalla(post)):
            yield
    else:
        yield


def bygg_aterhamtning(args, release, root, receipt, laddning_sha):
    original_path = Path(args.aterhamta).resolve()
    original = json.loads(original_path.read_text())
    extra = {key: original.get(key) for key in ('mall', 'parametrar', 'antal_filer', 'kontext_policy',
             'schema_sha256', 'manifest_platser', 'bedomningsbindning', 'bildbedomningsunderlag')}
    extra['formaterhamtning'] = {'korning': str(original_path), 'sha256': hashlib.sha256(original_path.read_bytes()).hexdigest(),
                               'falt': ['summary'], 'inga_nya_bildlasningar': True}
    proposal = {**extra, 'laddning': original.get('laddning')}
    aterhamtningskalla(proposal)
    if ((original.get('laddning') or {}).get('sha256') != laddning_sha
            or Path(original['laddning']['fil']).resolve() != Path(args.laddning).resolve()):
        raise Vagrad('formåterhämtning kräver exakt ursprungligt laddningskvitto')
    argv = original.get('argv') or []
    def argument(flag):
        if argv.count(flag) != 1 or argv.index(flag) + 1 >= len(argv):
            raise Vagrad('ursprunglig körning saknar entydig parameter ' + flag)
        return argv[argv.index(flag) + 1]
    if argv.count('runtime.web_critique') != 1:
        raise Vagrad('ursprunglig körning är inte Runtimes kritikprofil')
    args.utforare = argument('--utforare'); args.modell = argument('--modell'); args.mall = original['mall']
    paths = {flag: argument(flag) for flag in ('--underlag', '--fraga', '--schema')}
    run = Path((original.get('resultat') or {}).get('run') or '')
    runtime_receipt = run / 'KVITTO.json'
    if not runtime_receipt.is_file() or hashlib.sha256(runtime_receipt.read_bytes()).hexdigest() != original.get('runtime_kvitto_sha256'):
        raise Vagrad('ursprungligt Runtime-kvitto avviker från KORNING')
    with historisk_domkod(original):
        expected, underlag = kritikbevis.ur_laddning(args.laddning)
        if expected != original.get('bedomningsbindning') or underlag != original.get('bildbedomningsunderlag'):
            raise Vagrad('ursprunglig kandidat, kriterier, domkod eller bildbindning har ändrats')
    cmd = [release['python'], '-B', '-m', 'runtime.web_critique']
    for flag, value in paths.items(): cmd += [flag, value]
    cmd += ['--utforare', args.utforare, '--modell', args.modell, '--etikett', args.etikett,
            '--aterhamta', str(run), '--formfalt', 'summary', '--formtid', str(args.formtid)]
    # Run the exact Runtime eligibility check without auth/model startup. This
    # also refuses an active release that lacks the implementation.
    probe = ('import sys; from runtime.web_critique import parse; '
             'from runtime.critique_format import verified_source; '
             'a=parse(sys.argv[1:]); verified_source(a.aterhamta,a); print("form-preflight-ok")')
    done = subprocess.run([release['python'], '-B', '-c', probe, *cmd[4:]], cwd=release['kod'], env=miljo(root),
                          capture_output=True, text=True)
    if done.returncode or done.stdout.strip() != 'form-preflight-ok':
        raise Vagrad('Runtime vägrar formåterhämtning före modellstart: ' + done.stderr.strip()[-600:])
    return cmd, extra


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
    k.add_argument('--mall')
    k.add_argument('--filer')
    k.add_argument('--utforare', choices=('claude', 'codex'))
    k.add_argument('--modell')
    k.add_argument('--aterhamta', help='Ursprunglig KORNING.json; endast summary-form, samma laddning och domkod')
    k.add_argument('--formtid', type=int, default=180)
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
    if args.profil == 'kritik':
        if args.aterhamta:
            if args.mall or args.filer or args.utforare or args.modell or args.parameter or args.bindning or args.tid:
                raise Vagrad('formåterhämtning hämtar mall, underlag, modell och bindning oförändrade ur KORNING')
        elif not all((args.mall, args.filer, args.utforare, args.modell)):
            raise Vagrad('kritik kräver --mall, --filer, --utforare och --modell')
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
        cmd, extra = (bygg_aterhamtning if args.aterhamta else bygg_kritik)(args, release, root, receipt, laddning_sha)
    else:
        cmd, extra = bygg_provare(args, release, root, receipt, laddning_sha)
    post = {'schema': 1, 'profil': args.profil, 'etikett': args.etikett, 'laddning': {'fil': str(Path(args.laddning).resolve()),
            'sha256': laddning_sha, 'steg': receipt['steg'], 'sha256_over_underlag': receipt['sha256_over_underlag'],
            'rot_git_head': receipt.get('rot_git_head')}, 'aktiv_release': release, 'argv': utan_hemlig_vag(cmd), 'cwd': release['kod'], 'bindning': bindning_ur(args, receipt, release), **extra}
    if extra.get('formaterhamtning'):
        original = json.loads(Path(args.aterhamta).read_text())
        post['laddning'] = original['laddning']
        post['bindning'] = original['bindning']
        post['formaterhamtning']['konsument_head'] = subprocess.check_output(['git', '-C', str(ROT), 'rev-parse', 'HEAD'], text=True).strip()
        post['formaterhamtning']['konsument_hashar'] = verktygshashar()
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
            kontrollera_aterhamtningsbevis(post, run_path, runtime_receipt, answer)
            post['bildbelagg']=kritikbevis.bildbelagg(runtime_receipt)
            with domkontext(post):
                post['kvalitetsstatus'] = kritikbevis.dom(answer, extra['bedomningsbindning'], extra['bildbedomningsunderlag'], runtime_receipt)
        except (OSError, ValueError, Vagrad, kritikbevis.Vagrad):
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
