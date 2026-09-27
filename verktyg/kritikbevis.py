"""Fallets bildmanifest och semantiska kvalitetsdom. Runtime kör själva modellen och bokför bildleveransen."""
import hashlib
import json
from pathlib import Path
import re
import stegbevis

VERSION = 'digitala-kvalitet/2'
BILDFIL = 'BEDOMNINGSUNDERLAG.json'
KONTRAKT = 'kritik/BEDOMNING-v2.md'
DOMKOD = ('kritikbevis.py', 'stegbevis.py', 'kor_profil.py', 'kvalitetsbild.py', 'ladda_steg.py')
ROT = Path(__file__).resolve().parents[1]
PRODUKTKATEGORIER = {'start','undersidor','sprak','handlingsresa','fel','tom','laddning','redaktor','mobil','dator'}


class Vagrad(Exception):
    pass


def kanon(d):
    return json.dumps(d, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def domkod():
    p=ROT/'steg/DOMKOD.sha256'
    try:
        pins=dict((rel,digest) for digest,rel in (line.split('  ',1) for line in p.read_text().splitlines() if line and not line.startswith('#')))
        if set(pins)!={'verktyg/'+n for n in DOMKOD} or any(stegbevis.sha(ROT/rel)!=digest for rel,digest in pins.items()):
            raise Vagrad('domkodens pinnar skiljer från körd kod; nytt beslut och pinning krävs')
        return stegbevis.sha(p)
    except OSError as e:raise Vagrad('domkodens hashlista saknas') from e


def krav(d,kund):
    rel=Path(d.get('kravfil',''));p=Path(kund)/rel
    if not d.get('kravfil') or rel.is_absolute() or '..' in rel.parts or Path(kund).resolve() not in p.resolve().parents or not p.is_file() or stegbevis.sha(p)!=d.get('krav_sha256'):
        raise Vagrad('separat fördefinierad BEVISKRAV saknas eller har ändrad hash')
    k=stegbevis.las(p);b=k.get('bildbedomning') or {}
    if k.get('schema')!='digitala-beviskrav/1' or not k.get('version') or b.get('typ') not in ('produkt','komp') or not b.get('faststalld_av') or not b.get('faststalld_tid'):
        raise Vagrad('bildkrav kräver version, uppdragstyp och fastställelse före bedömning')
    if not b.get('tackning') or b['tackning']!=d.get('tackning'):
        raise Vagrad('manifestets täckning/N/A skiljer från fördefinierade bildkrav')
    categories={c for r in b['tackning'] for c in r.get('kategorier',[])}
    if b['typ']=='produkt' and not PRODUKTKATEGORIER<=categories:
        raise Vagrad('produktkraven saknar täckningskategorier: '+', '.join(sorted(PRODUKTKATEGORIER-categories)))
    dagens=b.get('dagens')
    if not isinstance(dagens,dict) or set(dagens)!={'tackning','na_skal'} or not isinstance(dagens['tackning'],list) or not isinstance(dagens['na_skal'],str):
        raise Vagrad('fördefinierat DAGENS-beslut kräver tackning och na_skal')
    if bool(dagens['tackning']) == bool(dagens['na_skal'].strip()):
        raise Vagrad('DAGENS kräver antingen jämförelsevyer eller ett fastställt N/A-skäl')
    ids=[r.get('id') for r in dagens['tackning']]
    if any(not r.get('id') or not r.get('beskrivning') for r in dagens['tackning']) or len(ids)!=len(set(ids)):
        raise Vagrad('DAGENS-rader kräver unika id och beskrivningar')
    if d.get('dagens')!=dagens:
        raise Vagrad('manifestets DAGENS-beslut skiljer från fördefinierade bildkrav')
    return b


def manifest(d, kund):
    if d.get('schema') != 'digitala-bildbedomning/2' or d.get('kriterieversion') != VERSION:
        raise Vagrad('bildmanifestet kräver digitala-bildbedomning/2 och digitala-kvalitet/2')
    if not re.fullmatch(r'[a-f0-9]{64}', str(d.get('kriterier_sha256', ''))):
        raise Vagrad('bildmanifestet saknar fryst kriteriehash')
    if not d.get('rackvidd') or not isinstance(d.get('tackning'), list) or not d['tackning']:
        raise Vagrad('bildmanifestet kräver räckvidd och fördefinierad sid-/läges-/vytäckning')
    try:
        stegbevis.sammanhang(d.get('sammanhang') or {})
    except stegbevis.Vagrad as e:
        raise Vagrad(str(e)) from e
    krav(d,kund)
    bilder = d.get('bilder')
    if not isinstance(bilder, list) or not bilder or not {'kandidat', 'referens'} <= {b.get('roll') for b in bilder}:
        raise Vagrad('obligatoriska kandidat- och referensbilder saknas')
    seen = set(); coverage = set(); dagens_coverage = set()
    for b in bilder:
        for key in ('fil', 'sha256', 'plats', 'kalla', 'tid', 'vy', 'drag'):
            if not b.get(key):
                raise Vagrad('bilden saknar proveniensfält: ' + key)
        if not re.fullmatch(r'(VYER|REFERENSER|DAGENS)/[A-Za-z0-9][A-Za-z0-9._/-]*\.(png|jpg|jpeg|webp)', b['plats']) or '..' in Path(b['plats']).parts:
            raise Vagrad('bildens paketplats har fel form')
        if b['plats'] in seen or b['roll'] != {'VYER':'kandidat','REFERENSER':'referens','DAGENS':'dagens'}[b['plats'].split('/')[0]]:
            raise Vagrad('dubblerad bildplats eller fel bildroll')
        seen.add(b['plats'])
        rel = Path(b['fil']); path = Path(kund) / rel
        if rel.is_absolute() or '..' in rel.parts or Path(kund).resolve() not in path.resolve().parents:
            raise Vagrad('bilden måste ligga i kundmappen utan att lämna den')
        if not path.is_file() or stegbevis.sha(path) != b['sha256']:
            raise Vagrad('bild saknas eller har ändrad hash: ' + b['fil'])
        # A textual file renamed .png is not a rendered image.
        raw = path.read_bytes()[:16]
        if not (raw.startswith(b'\x89PNG\r\n\x1a\n') or raw.startswith(b'\xff\xd8\xff') or (raw.startswith(b'RIFF') and raw[8:12] == b'WEBP')):
            raise Vagrad('bildfilens byteformat stöds inte: ' + b['fil'])
        if b['roll'] == 'kandidat':
            coverage.update(b.get('tacker', []))
        elif b['roll'] == 'dagens':
            dagens_coverage.update(b.get('tacker', []))
    for row in d['tackning']:
        if not row.get('id') or not row.get('beskrivning'):
            raise Vagrad('täckningsrad saknar id/beskrivning')
        if not row.get('na_skal') and row['id'] not in coverage:
            raise Vagrad('obligatorisk sid-/läges-/vybild saknas: ' + row['id'])
    if not {r['id'] for r in d['dagens']['tackning']} <= dagens_coverage:
        raise Vagrad('obligatoriska DAGENS-bilder saknas för fastställd jämförelse')
    return d


def bindning(d, digest):
    return {'underlag_sha256': digest, 'kriterier_sha256': d['kriterier_sha256'], 'krav_sha256':d['krav_sha256'], 'domkod_sha256':domkod(),
            'kandidat': kanon(d['sammanhang']['kandidat']), 'miljo': kanon(d['sammanhang']['miljo']),
            'konfiguration': kanon(d['sammanhang']['konfiguration']), 'rackvidd': d['rackvidd']}


def ur_laddning(path):
    receipt=stegbevis.las(path);root=Path(receipt['arbetsyta']);rows={r['fil']:r for r in receipt['underlag'] if r.get('status')=='laddad'}
    for r in rows.values():
        p=root/r['plats']
        if not p.is_file() or stegbevis.sha(p)!=r.get('sha256'):raise Vagrad('laddat underlag ändrat: '+r['fil'])
    if BILDFIL not in rows or KONTRAKT not in rows:raise Vagrad('manifest eller kriterier saknas i faktisk laddning')
    m=rows[BILDFIL];p=root/m['plats'];d=stegbevis.las(p);manifest(d,root/'underlag/kund')
    if d['kriterier_sha256']!=rows[KONTRAKT]['sha256']:raise Vagrad('kriteriehash skiljer från laddningen')
    if d['kravfil'] not in rows or rows[d['kravfil']]['sha256']!=d['krav_sha256']:raise Vagrad('fördefinierade bildkrav saknas i laddningen')
    for b in d['bilder']:
        r=rows.get(b['fil'],{})
        if r.get('klass')!='kund' or r.get('obligatorisk') is not True or r.get('sha256')!=b['sha256'] or r.get('plats')!='underlag/kund/'+b['fil']:
            raise Vagrad('obligatorisk bild saknas/avviker i LADDNING: '+b['fil'])
    return bindning(d,stegbevis.sha(p)),d


def bildbelagg(kvitto):
    executor=(kvitto.get('parameters') or {}).get('executor');how=(kvitto.get('images') or {}).get('how')
    if executor=='claude' and how=='opened with Read (from the stream)':return 'Read-spår för Claude'
    if executor=='codex' and how=='attached on the command line (read back from argv)':return 'argv-bilagor för Codex; bildläsning självrapporterad, inte självständigt verifierad'
    return None


def dom(svar, expected, underlag, kvitto):
    """Formgiltighet är separat. Denna kontroll kan bara verifiera bindning och observerad bildleverans."""
    try:
        stegbevis.sammanhang(underlag.get('sammanhang') or {})
    except (stegbevis.Vagrad, OSError, TypeError) as e:
        return 'inaktuell: kandidat eller konfiguration kan inte återbindas: ' + str(e)
    if not isinstance(svar, dict) or svar.get('kriterieversion') != VERSION or svar.get('bedomningsbindning') != expected:
        return 'ogiltig bindning: domens kandidat, miljö, konfiguration, räckvidd eller kriterier skiljer sig'
    if expected.get('domkod_sha256')!=domkod() or expected!=bindning(underlag,expected.get('underlag_sha256')):
        return 'ogiltig bindning: omräknat manifest eller domkod skiljer sig'
    verdict = svar.get('verdict')
    if verdict == 'ej_bedombart':
        return 'ej bedömbart: ' + '; '.join(svar.get('could_not_review') or ['underlag saknas'])
    if verdict == 'rejected':
        return 'underkänd: professionell dom rejected'
    if verdict != 'approved' or svar.get('blocking_findings') or svar.get('could_not_review'):
        return 'underkänd: ingen motsägelsefri approved-dom'
    if not bildbelagg(kvitto):
        return 'ej bedömbart: bildbeläggets utförare/metod saknas eller är okänd'
    image = kvitto.get('images') or {}
    required = {b['plats'] for b in underlag['bilder']}
    if image.get('complete') is not True or not required <= set(image.get('delivered_or_opened') or []):
        return 'ej bedömbart: Runtime saknar belagd bildleverans/Read för obligatoriska bilder'
    if not required <= set(svar.get('seen_files') or []):
        return 'ej bedömbart: bedömaren redovisar inte obligatoriska bilder som sedda'
    comparisons = svar.get('referensjamforelser') or []
    if not comparisons:
        return 'ej bedömbart: faktisk referensjämförelse saknas'
    by_place = {b['plats']: b for b in underlag['bilder']}
    for c in comparisons:
        ref = by_place.get(c.get('referensbild')); candidate = by_place.get(c.get('kandidatbild'))
        if not ref or ref['roll'] != 'referens' or not candidate or candidate['roll'] != 'kandidat':
            return 'ogiltig jämförelse: bild saknas i bundet manifest'
        if any(c.get(k) != ref[k] for k in ('kalla', 'tid', 'vy')) or not all(c.get(k) for k in ('drag', 'observation', 'konsekvens', 'beslut_och_skal')):
            return 'ogiltig jämförelse: proveniens, drag eller motiverat beslut saknas/skiljer sig'
    dagens = svar.get('dagensjamforelser')
    if not isinstance(dagens,list):
        return 'ej bedömbart: dagensjamforelser saknas'
    compared=set()
    for c in dagens:
        old=by_place.get(c.get('dagensbild'));candidate=by_place.get(c.get('kandidatbild'))
        if not old or old['roll']!='dagens' or not candidate or candidate['roll']!='kandidat':
            return 'ogiltig DAGENS-jämförelse: bild saknas i bundet manifest'
        if any(c.get(k)!=old[k] for k in ('kalla','tid','vy')) or not all(c.get(k) for k in ('drag','observation','konsekvens','beslut_och_skal')):
            return 'ogiltig DAGENS-jämförelse: proveniens eller motiverat beslut saknas/skiljer sig'
        compared.update(old.get('tacker',[]))
    if not {r['id'] for r in underlag['dagens']['tackning']} <= compared:
        return 'ej bedömbart: faktisk DAGENS-jämförelse saknas för fastställda vyer'
    return 'ok'
