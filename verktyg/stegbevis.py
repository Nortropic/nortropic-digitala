"""Verifierar Digitalas avgränsade stegbevis mot fallets fördefinierade BEVISKRAV.json.

Detta bevisar bindning och rapporterat utfall, inte att en modell eller människa talar sant.
Råresultat, utförare och provnivå förblir synliga. Inga äldre kvitton uppgraderas automatiskt.
"""
import hashlib
import json
from pathlib import Path
import subprocess


class Vagrad(Exception):
    pass


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def las(p):
    try:
        d = json.loads(Path(p).read_text(encoding='utf-8'))
        if not isinstance(d, dict):
            raise ValueError('objekt krävs')
        return d
    except (OSError, ValueError) as e:
        raise Vagrad('oläsbart bevis/krav: %s (%s)' % (p, type(e).__name__)) from e


def fil(r):
    if not isinstance(r, dict) or not isinstance(r.get('fil'), str) or not Path(r['fil']).is_absolute():
        raise Vagrad('bevisfil kräver absolut fil och sha256')
    p = Path(r['fil'])
    if not p.is_file() or r.get('sha256') != sha(p):
        raise Vagrad('saknat eller ändrat bevis: ' + str(p))
    return {'fil': str(p.resolve()), 'sha256': r['sha256']}


def kandidat(k):
    if not isinstance(k, dict):
        raise Vagrad('kandidat saknas')
    if k.get('typ') == 'git':
        root = Path(k.get('rot', ''))
        if not root.is_absolute() or not root.is_dir():
            raise Vagrad('kandidatens gitrot saknas')
        def git(*args):
            d = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True)
            if d.returncode:
                raise Vagrad('kandidatens gitidentitet kan inte läsas')
            return d.stdout.strip()
        if k.get('commit') != git('rev-parse', 'HEAD') or k.get('tree') != git('rev-parse', 'HEAD^{tree}'):
            raise Vagrad('annan kandidat: commit/träd har ändrats')
        if git('status', '--porcelain', '--untracked-files=normal'):
            raise Vagrad('kandidatens arbetsyta är ändrad; frys och prova exakt kandidat')
    elif k.get('typ') == 'filer' and k.get('filer'):
        for r in k['filer']:
            fil(r)
    else:
        raise Vagrad('kandidat kräver gitidentitet eller en icke tom fillista med hashar')


def sammanhang(k):
    if not isinstance(k, dict):
        raise Vagrad('sammanhang ska vara ett objekt')
    kandidat(k.get('kandidat'))
    if not isinstance(k.get('miljo'), dict) or not all(k['miljo'].get(x) for x in ('namn', 'typ')):
        raise Vagrad('miljö kräver namn och typ')
    c = k.get('konfiguration')
    if not isinstance(c, dict) or (not c.get('filer') and not (isinstance(c.get('ej_tillampligt'), str) and c['ej_tillampligt'].strip())):
        raise Vagrad('konfiguration kräver hashbundna filer eller motiverat ej_tillampligt')
    for r in c.get('filer', []):
        fil(r)


def pekare(d, p):
    if not isinstance(p, list) or not p:
        raise Vagrad('utfallspekare kräver en icke tom lista av nycklar/index')
    try:
        for key in p:
            d = d[key]
        return d
    except (KeyError, IndexError, TypeError) as e:
        raise Vagrad('utfallspekaren saknas i faktiskt råresultat') from e


def kontrollera(path, fall, kund, steg, laddning=None, utfall='klar'):
    b = las(path)
    kravfil = Path(fall) / 'BEVISKRAV.json'
    krav = las(kravfil)
    if krav.get('schema') != 'digitala-beviskrav/1' or not krav.get('version'):
        raise Vagrad('BEVISKRAV.json kräver schema digitala-beviskrav/1 och version före bedömning')
    k = krav.get('steg', {}).get(steg)
    if not isinstance(k, dict) or not isinstance(k.get('kontroller'), dict) or not k['kontroller'] or not all(isinstance(v, dict) and v.get('forvantat') for v in k['kontroller'].values()):
        raise Vagrad('fördefinierade obligatoriska beviskrav saknas för ' + steg)
    if b.get('schema') != 'digitala-stegbevis/1' or b.get('steg') != steg or b.get('kund') != str(Path(kund).resolve()):
        raise Vagrad('beviset gäller fel schema, steg eller kund')
    if b.get('krav_sha256') != sha(kravfil):
        raise Vagrad('beviset gäller en annan kravversion')
    if b.get('utfall') != utfall or b.get('genomfort') is not True or not b.get('utforare') or not b.get('omfattning'):
        raise Vagrad('beviset saknar genomfört utfall, utförare eller omfattning')
    if laddning and (b.get('laddning_sha256') != sha(laddning)):
        raise Vagrad('beviset gäller annan laddning')
    if b.get('sammanhang') != k.get('sammanhang') or b.get('niva') != k.get('niva'):
        raise Vagrad('beviset gäller fel kandidat, miljö, konfiguration eller provnivå')
    sammanhang(k.get('sammanhang') or {})
    if k.get('niva') not in ('dokument', 'statik', 'lokal', 'privat-preview', 'drift'):
        raise Vagrad('okänd provnivå')
    kontroller = b.get('kontroller')
    if not isinstance(kontroller, list) or not all(isinstance(r, dict) and isinstance(r.get('id'), str) for r in kontroller) or len({r.get('id') for r in kontroller}) != len(kontroller):
        raise Vagrad('kontroller saknas eller dubblerade kontroll-id')
    rows = {r.get('id'): r for r in kontroller}
    for id_, definition in k['kontroller'].items():
        r = rows.get(id_)
        if not r or not r.get('observerat'):
            raise Vagrad('obligatorisk kontroll saknas: ' + id_)
        if r.get('utfall') == 'inte-tillampligt':
            if not definition.get('na_skal') or r.get('na_skal') != definition['na_skal']:
                raise Vagrad('N/A är inte fördefinierat och motiverat för ' + id_)
            continue
        if r.get('utfall') != 'godkant':
            raise Vagrad('obligatorisk kontroll inte godkänd: ' + id_)
        fil(r)
        raw = las(r['fil'])
        result = pekare(raw, r.get('utfallspekare'))
        # The raw receipt must identify the same context, not merely an envelope attached later.
        for key in ('kandidat', 'miljo', 'konfiguration'):
            actual = pekare(raw, (r.get('bindningspekare') or {}).get(key))
            if actual != b['sammanhang'][key]:
                raise Vagrad('råresultatet gäller annan ' + key + ': ' + id_)

        # Exact statuses only; no prefix matching, and false/zero are never a pass.
        if result is not True and result not in ('approved', 'godkant', 'godkänd', 'PASS', 'pass', 'passed'):
            raise Vagrad('råresultatet är inte godkänt: ' + id_)
        if raw.get('torr') is True or raw.get('genomfort') is False or raw.get('exit', 0) != 0:
            raise Vagrad('torr/avbruten/misslyckad körning kan inte vara godkänt prov')
    if utfall == 'inte-tillampligt' and (not k.get('na_skal') or b.get('na_skal') != k['na_skal']):
        raise Vagrad('stegets N/A kräver fördefinierat sakskäl; åtkomstbrist är väntan')
    return {'fil': str(Path(path).resolve()), 'sha256': sha(path), 'kravfil': str(kravfil.resolve()),
            'krav_sha256': sha(kravfil), 'stegkrav': k, 'bevis': b}


def giltigt(g, fall, kund, steg, laddning):
    if not g:
        raise Vagrad('äldre klarstatus saknar verifierat stegbevis; historiken bevaras, nytt omprov krävs')
    fil(g)
    # A new criteria file invalidates only changed step requirements, not unrelated completed steps.
    current = las(Path(fall) / 'BEVISKRAV.json')
    if current.get('steg', {}).get(steg) != g.get('stegkrav'):
        raise Vagrad('stegets krav eller sammanhang har ändrats')
    b = g['bevis']; sammanhang(b['sammanhang'])
    if b.get('laddning_sha256') != sha(laddning):
        raise Vagrad('laddningskvittot har ändrats')
    for r in b['kontroller']:
        if r.get('utfall') == 'godkant':
            fil(r)
    for r in g.get('fakta', []):
        if r['sha256'] is None:
            if Path(r['fil']).exists():
                raise Vagrad('nytt faktaunderlag: ' + r['fil'])
        else:
            fil(r)
    return True
