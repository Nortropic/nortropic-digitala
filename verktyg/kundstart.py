#!/usr/bin/env python3
"""Kundstart: kundytan för intervjun (repot Nortropic/nortropic-kundstart) som en kanal i intervjusteget.

Kundmappen (INTERVJU.json, verktyg/intervju.py) är det auktoritativa hemmet för kundens uppgifter. Kundstart är
"sparat hos kundtjänsten" tills `hamta` har förts in i kundmappen ("överfört till Digitala"); research-steget gör
"bearbetat i research". Returfrågor kan uttryckligen lämnas i samma kunddialog; `skapa` skriver inbjudningslänken (en behörighet) till
`~/.nortropic-hemligheter/<kund>/KUNDSTART-LANK.secret` (0600; annan rot med KUNDSTART_HEMLIGHETER), och sessionen lämnar
den genom beställningens kanal.

    python3 -B verktyg/kundstart.py skapa  --kund DIR --namn "Kundens namn" [--kontakt "..."] [--testdialog] [--dagar 30]
    python3 -B verktyg/kundstart.py status --kund DIR
    python3 -B verktyg/kundstart.py hamta  --kund DIR [--material]    # export → INTERVJU.json (ordagrant) + FAKTA-rader + material
    python3 -B verktyg/kundstart.py lank   --kund DIR [--dagar 30]     # ny länk (t.ex. utgången eller byte av enhet)
    python3 -B verktyg/kundstart.py aterkalla --kund DIR              # återkallar aktuell länk
    python3 -B verktyg/kundstart.py konsumera --kund DIR --utforare NAMN  # signal → fryst export → import/research → kvittens
    python3 -B verktyg/kundstart.py returfragor --kund DIR --utforare NAMN --fragor FIL.json
    python3 -B verktyg/kundstart.py last --kund DIR --utforare NAMN --material-id ID --lasbevis FIL.json

Åtkomst: miljövariabeln KUNDSTART_BAS_URL (tjänstens adress) och en fil med den interna nyckeln, rättighet 0600,
utanför /tmp: `--nyckel-fil` eller miljövariabeln KUNDSTART_NYCKEL_FIL (standard ~/.nortropic-hemligheter/kundstart/
KUNDSTART_INTERN_NYCKEL.secret). Nyckeln och länkens värde skrivs aldrig ut. Skyddad förhandsvisning hos Vercel
passeras med KUNDSTART_BYPASS_FIL (Protection Bypass for Automation), också 0600.
"""
import argparse
import hashlib
import fcntl
from contextlib import contextmanager
import urllib.parse
import json
import os
import re
import stat
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import intervju as iv  # noqa: E402

KALLA_LASBAR = 'det vi redan hade antecknat om er'  # VERKSAMHET.json:s belägg är interna; kunden ser en neutral, sann källa
MATERIAL_ID = re.compile(r'^m_[A-Za-z0-9_-]{6,24}$')
FRAGA_ID = re.compile(r'^(?:[A-Z]+\d+|(?:RET|BEH)\d+_\d+)$')


class Vagrad(Exception):
    pass


def nu():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def las_hemlig_fil(p):
    p = Path(p).expanduser()
    if not p.is_file():
        raise Vagrad('hemlig fil saknas: ' + str(p))
    for kandidat in (p, p.resolve()):
        delar = kandidat.parts
        if delar[1:3] == ('private', 'tmp') or delar[1:3] == ('private', 'etc'):
            delar = ('/',) + delar[2:]
        if delar[:2] in (('/', 'tmp'), ('/', 'etc')) or '/var/folders' in str(kandidat) or '/private/var/folders' in str(kandidat):
            raise Vagrad('hemlig fil får inte ligga i /tmp, /etc eller /var/folders')
    if stat.S_IMODE(p.stat().st_mode) != 0o600:
        raise Vagrad('hemlig fil måste ha rättighet exakt 0600: ' + str(p))
    v = p.read_text(encoding='utf-8').strip()
    if len(v) < 16:
        raise Vagrad('hemlig fil är för kort')
    return v


def anrop(bas, nyckel, metod, vag, kropp=None, bypass=None, rå=False):
    req = urllib.request.Request(bas.rstrip('/') + vag, method=metod)
    req.add_header('Authorization', 'Bearer ' + nyckel)
    if bypass:
        req.add_header('x-vercel-protection-bypass', bypass)
    data = None
    if kropp is not None:
        data = json.dumps(kropp, ensure_ascii=False).encode('utf-8')
        req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, data=data, timeout=60) as r:
            return r.read() if rå else json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        text = e.read().decode('utf-8', 'replace')[:300]
        raise Vagrad('kundstart svarade %d på %s %s: %s' % (e.code, metod, vag, re.sub(r'[A-Za-z0-9_-]{40,}', '…', text)))
    except urllib.error.URLError as e:
        raise Vagrad('kundstart nås inte (%s): %s' % (bas, e.reason))


def kundstart_fil(kund):
    return Path(kund) / 'KUNDSTART.json'


def las_kundstart(kund):
    p = kundstart_fil(kund)
    if not p.is_file():
        raise Vagrad('inget Kundstart-ärende i %s (kör skapa)' % kund)
    return json.loads(p.read_text(encoding='utf-8'))


def bunden(d, bas):
    if not d.get('bas_url') or d['bas_url'].rstrip('/') != bas.rstrip('/'):
        raise Vagrad('bas-url skiljer från ärendets bundna tjänst')


def json_sha(d):
    return hashlib.sha256(json.dumps(d, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()


def privat_skriv(p, text):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True); p.parent.chmod(0o700)
    tmp = p.with_name(p.name + '.tmp-%d' % os.getpid())
    with tmp.open('w', encoding='utf-8') as out:
        os.chmod(tmp, 0o600); out.write(text); out.flush(); os.fsync(out.fileno())
    os.replace(tmp, p)


def privat_json(p, d):
    privat_skriv(p, json.dumps(d, ensure_ascii=False, indent=1) + '\n')


@contextmanager
def konsumtionslas(kund):
    p = Path(kund) / 'KUNDSTART' / '.konsumtion.lock'; p.parent.mkdir(exist_ok=True); p.parent.chmod(0o700)
    with p.open('a') as lock:
        p.chmod(0o600)
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as e:
            raise Vagrad('ärendets import bearbetas redan av en utförare; försök nästa tick') from e
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def spara_kundstart(kund, d):
    d['uppdaterad'] = nu()
    privat_json(kundstart_fil(kund), d)


def lank_fil(kund):
    d = Path(os.environ.get('KUNDSTART_HEMLIGHETER') or (Path.home() / '.nortropic-hemligheter')) / Path(kund).name
    d.mkdir(parents=True, exist_ok=True); os.chmod(d, 0o700)
    return d / 'KUNDSTART-LANK.secret'


def skriv_lank(kund, lank, utgar):
    p = lank_fil(kund)
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(lank + '\n')
    os.chmod(p, 0o600)
    return str(p), utgar


def forifyllda_fakta(kund):
    """Kända uppgifter ur kundmappen med läsbar källa: VERKSAMHET.json (intervju.py:s regel) och tidigare fakta."""
    ut = []
    for f in iv.fro_verksamhet(kund):
        ut.append({**f, 'kalla': KALLA_LASBAR})
    p = iv.stig(kund)
    if p.is_file():
        s = json.loads(p.read_text(encoding='utf-8'))
        for f in s.get('fakta', []):
            if f.get('ersatt') or f.get('status') == 'okänt':
                continue
            if any(x['nyckel'] == f['nyckel'] for x in ut):
                continue
            ut.append({'nyckel': f['nyckel'], 'varde': f['varde'], 'status': f['status'], 'kalla': KALLA_LASBAR if f['status'] != 'kunden uppger' else 'det ni uppgett tidigare', 'omrade': f.get('omrade', 'A'), 'datum': f.get('datum', nu()[:10])})
    return ut


def skapa(kund, bas, nyckel, bypass, namn, kontakt, testdialog, dagar):
    if kundstart_fil(kund).is_file():
        d = las_kundstart(kund)
        return d, 'Kundstart-ärende finns redan (%s); använd status, hamta eller lank' % d['arende_id']
    slug = re.sub(r'[^a-z0-9]+', '-', Path(kund).name.lower()).strip('-')[:40] or 'kund'
    kropp = {'kund': {'slug': slug, 'namn': namn}, 'kontakt': kontakt, 'kanal': 'Kundstart-länk' + (' (TESTDIALOG)' if testdialog else ''), 'testdialog': bool(testdialog), 'fakta': forifyllda_fakta(kund), 'lank_dagar': dagar, 'bas_url': bas.rstrip('/')}
    r = anrop(bas, nyckel, 'POST', '/api/intern/arenden', kropp, bypass)
    if not re.match(r'^ar_[A-Za-z0-9_-]{8,20}$', str(r.get('arende_id', ''))) or not re.match(r'^[a-f0-9]{64}$', str(r.get('lank_hash', ''))):
        raise Vagrad('tjänsten svarade med ett ärende-id eller en länkhash i fel form')
    d = {'schema': 1, 'arende_id': r['arende_id'], 'bas_url': bas.rstrip('/'), 'testdialog': bool(testdialog), 'skapad': nu(), 'lank_hash': r['lank_hash'], 'lank_utgar': r['utgar'], 'ai': r.get('ai'), 'forifyllda': len(kropp['fakta']), 'hamtat': []}
    spara_kundstart(kund, d)
    fil, _ = skriv_lank(kund, r['lank'], r['utgar'])
    return d, 'ärende %s skapat; länken (gäller till %s) står i %s med rättighet 0600 och lämnas genom beställningens kanal' % (d['arende_id'], r['utgar'][:10], fil)


def ny_lank(kund, bas, nyckel, bypass, dagar):
    d = las_kundstart(kund)
    bunden(d, bas)
    r = anrop(bas, nyckel, 'POST', '/api/intern/arenden/%s/lankar' % d['arende_id'], {'lank_dagar': dagar, 'bas_url': d['bas_url']}, bypass)
    d['lank_hash'] = r['lank_hash']; d['lank_utgar'] = r['utgar']
    spara_kundstart(kund, d)
    fil, _ = skriv_lank(kund, r['lank'], r['utgar'])
    return d, 'ny länk (gäller till %s) står i %s; den gamla länken gäller tills den återkallas' % (r['utgar'][:10], fil)


def aterkalla(kund, bas, nyckel, bypass):
    d = las_kundstart(kund)
    bunden(d, bas)
    anrop(bas, nyckel, 'DELETE', '/api/intern/arenden/%s/lankar/%s' % (d['arende_id'], d['lank_hash']), None, bypass)
    d['lank_aterkallad'] = nu()
    spara_kundstart(kund, d)
    p = lank_fil(kund)
    if p.is_file():
        p.unlink()
    return d, 'länken är återkallad; kundens pågående sessioner slutar gälla'


def status(kund, bas, nyckel, bypass):
    d = las_kundstart(kund)
    bunden(d, bas)
    r = anrop(bas, nyckel, 'GET', '/api/intern/arenden/%s' % d['arende_id'], None, bypass)
    vy = r['vy']
    return d, {'arende_id': d['arende_id'], 'svar': len(vy['dialog']), 'oppna_fragor': [f['id'] for f in vy['oppna']], 'bild': len(vy['bild']), 'material': len(vy['material']), 'aterstar': vy['aterstar'], 'inlamnad': vy['arende']['inlamnad'], 'ai': r['ai'], 'revision': vy['arende']['revision'], 'hamtat_till_revision': (d['hamtat'][-1]['revision'] if d['hamtat'] else None)}


def hamta(kund, bas, nyckel, bypass, med_material, paket=None, export_sha256=None):
    """Exportpaketet in i kundmappen: varje Kundstart-omgång blir en omgång i INTERVJU.json med kundens svar ordagrant
    (intervju.py:s svar-funktion), AI-tolkningar blir FAKTA-rader med status 'tolkning', kundens rättelser FAKTA-rader
    med status 'kunden uppger'; motsägelser uppstår och avgörs i intervju.py:s ordinarie väg."""
    d = las_kundstart(kund)
    bunden(d, bas)
    paket = paket if paket is not None else anrop(bas, nyckel, 'GET', '/api/intern/arenden/%s/export' % d['arende_id'], None, bypass)
    if (paket.get('arende') or {}).get('id') != d['arende_id']:
        raise Vagrad('exporten gäller ett annat ärende')
    if paket.get('schema') != 'kundstart-export/1':
        raise Vagrad('okänt exportschema: %s' % paket.get('schema'))
    for f in ('arende', 'omgangar', 'svar', 'rattelser', 'fakta_ai', 'rattelser_fakta', 'material'):
        if f not in paket or not isinstance(paket[f], (list, dict)):
            raise Vagrad('exportpaketet saknar fältet %s eller har fel form' % f)
    for f in ('id', 'revision', 'kanal', 'testdialog'):
        if f not in paket['arende']:
            raise Vagrad('exportpaketet saknar arende.%s' % f)
    for o in paket['omgangar']:
        for sv in o.get('svar', []):
            if not all(k in sv for k in ('fraga_id', 'text', 'mottaget', 'revision')):
                raise Vagrad('ett svar i omgång %s saknar fraga_id, text, mottaget eller revision' % o.get('nr'))
    digest = export_sha256 or json_sha(paket)
    if type(paket['arende']['revision']) is not int or paket['arende']['revision'] < 1:
        raise Vagrad('exportrevision måste vara ett positivt heltal')
    sista = d['hamtat'][-1]['revision'] if d['hamtat'] else 0
    if paket['arende']['revision'] < sista:
        raise Vagrad('äldre export får inte skriva över senare importerad revision')
    if (paket['arende']['revision'] == sista and d['hamtat'][-1].get('export_sha256') == digest
            and not d['hamtat'][-1].get('ej_registrerade')):
        return d, 'inget nytt sedan revision %d' % sista
    kanal = paket['arende']['kanal']
    if not iv.stig(kund).is_file():
        s = {'schema': 1, 'kund': Path(kund).name, 'kanal': kanal, 'testdialog': bool(paket['arende']['testdialog']), 'startad': nu(), 'omgangar': [], 'svar': [], 'fakta': iv.fro_verksamhet(kund), 'motsagelser': [], 'foljdregler_utlosta': []}
        iv.spara(kund, s)
    s = iv.las(kund)
    if paket['arende']['testdialog'] and not s.get('testdialog'):
        raise Vagrad('exporten är en testdialog men intervjun i kundmappen är det inte; blanda inte')
    mapp = Path(kund) / 'KUNDSTART'
    mapp.mkdir(exist_ok=True)
    (mapp / ('export-rev%d.json' % paket['arende']['revision'])).write_text(json.dumps(paket, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    nya_svar = 0; nya_fakta = 0; nya_omg = 0; andrade_svar = []; ej_registrerade = []
    registrerade = {(x['fraga_id'], x.get('kundstart_revision')) for x in s['svar'] if x.get('kalla') == 'kundstart'}
    def giltig_fraga(f):
        return isinstance(f, dict) and FRAGA_ID.match(str(f.get('id', ''))) and str(f.get('omrade')) in iv.OMRADEN and re.match(r'^[a-zåäö0-9_]{2,60}$', str(f.get('nyckel', ''))) and isinstance(f.get('text'), str) and 0 < len(f['text']) <= 1000
    for o in paket['omgangar']:
        etikett = 'kundstart-%d' % o['nr']
        ogiltiga = [f for f in o['fragor'] if not giltig_fraga(f)] + [sv for sv in o['svar'] if not FRAGA_ID.match(str(sv.get('fraga_id', '')))]
        if ogiltiga:
            ej_registrerade.append({'omgang': o['nr'], 'skal': 'fråga eller svar i fel form (finns kvar i exportfilen)', 'fragor': [str(x.get('id') or x.get('fraga_id'))[:40] for x in ogiltiga]})
        giltiga = [{'id': f['id'], 'omrade': f['omrade'], 'nyckel': f['nyckel'], 'text': f['text'], 'paverkar': str(f.get('paverkar') or '')[:300], 'utlost_av': (str(f['utlost_av'])[:200] if f.get('utlost_av') else None), 'banktext': f.get('banktext'), 'valjare': f.get('valjare')} for f in o['fragor'] if giltig_fraga(f)]
        omg = next((x for x in s['omgangar'] if x.get('kundstart_omgang') == o['nr']), None)
        if not omg:
            fragor = [{k: f[k] for k in ('id', 'omrade', 'nyckel', 'text', 'paverkar', 'utlost_av')} for f in giltiga]
            if not fragor:
                if o['svar']:
                    ej_registrerade.append({'omgang': o['nr'], 'skal': 'omgången saknar giltiga frågor; svaren finns kvar i exportfilen', 'fragor': [str(sv.get('fraga_id')) for sv in o['svar']]})
                continue
            omg = iv.ny_omgang(s, fragor, 'Kundstart-länk: omgång %d i kundytan (%s)' % (o['nr'], 'AI valde' if any(f.get('valjare') == 'ai' for f in o['fragor']) else 'regelstyrd'))
            omg['kundstart_omgang'] = o['nr']; nya_omg += 1
        else:
            # frågor som tjänsten lagt till i omgången efter förra hämtningen
            for f in giltiga:
                if not any(q['id'] == f['id'] for q in omg['fragor']):
                    omg['fragor'].append({'id': f['id'], 'omrade': f['omrade'], 'nyckel': f['nyckel'], 'text': f['text'], 'paverkar': f['paverkar'], 'utlost_av': f['utlost_av'], 'status': 'stalld'})
        for f in omg['fragor']:
            k = next((x for x in giltiga if x['id'] == f['id']), {})
            if k.get('banktext'):
                f['omformulerad_av_ai'] = True; f['banktext'] = k['banktext']
        nya = sorted([sv for sv in o['svar'] if FRAGA_ID.match(str(sv.get('fraga_id', ''))) and (sv['fraga_id'], sv.get('revision')) not in registrerade], key=lambda sv: (sv['mottaget'], sv['revision']))
        if not nya:
            continue
        iv.spara(kund, s)
        # Svar som redan är besvarade i INTERVJU.json (kunden ändrade sitt svar i kundytan) går in som kundens
        # uppgift i fakta, eftersom intervju.py:s svarslista bara tar första svaret per fråga; det senaste ordet vinner synligt.
        besvarade = {q['id'] for oo in s['omgangar'] for q in oo['fragor'] if q.get('status') == 'besvarad'}
        forsta = []; andrade = []
        for sv in nya:
            if sv['fraga_id'] in besvarade or any(x['fraga_id'] == sv['fraga_id'] for x in forsta):
                andrade.append(sv)
            else:
                forsta.append(sv)
        if forsta:
            svarfil = mapp / ('%s-svar-rev%d.json' % (etikett, paket['arende']['revision']))
            svarfil.write_text(json.dumps([{'id': sv['fraga_id'], 'text': sv['text']} for sv in forsta], ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
            fore = len(s['svar'])
            try:
                s, _ = iv.svar(kund, omg['nr'], str(svarfil), kallmetadata={sv['fraga_id']: {'kalla': 'kundstart', 'mottaget': sv['mottaget'], 'kundstart_revision': sv['revision'], 'vet_inte': sv.get('typ') == 'vet_inte'} for sv in forsta})
            except iv.Vagrad as e:
                ej_registrerade.append({'omgang': o['nr'], 'skal': e.args[0][:200], 'fragor': [sv['fraga_id'] for sv in forsta]})
                s = iv.las(kund)
            else:
                for x in s['svar'][fore:]:
                    sv = next((y for y in forsta if y['fraga_id'] == x['fraga_id']), None)
                    if sv is None or x['text'] != sv['text']:
                        ej_registrerade.append({'omgang': o['nr'], 'skal': 'texten registrerades inte ordagrant', 'fragor': [x['fraga_id']]}); continue
                    x['kalla'] = 'kundstart'; x['mottaget'] = sv['mottaget']; x['kundstart_revision'] = sv['revision']
                    if sv.get('typ') == 'vet_inte':
                        x['vet_inte'] = True
                    nya_svar += 1
                saknade = [sv['fraga_id'] for sv in forsta if not any(x['fraga_id'] == sv['fraga_id'] and x.get('kundstart_revision') == sv['revision'] for x in s['svar'])]
                if saknade:
                    ej_registrerade.append({'omgang': o['nr'], 'skal': 'intervju.py registrerade inte svaret (okänt id eller redan besvarad)', 'fragor': saknade})
                iv.spara(kund, s)
        registrerade.update((x['fraga_id'], x.get('kundstart_revision')) for x in s['svar'] if x.get('kalla') == 'kundstart')
        for sv in andrade:
            fr = next((q for q in omg['fragor'] if q['id'] == sv['fraga_id']), None)
            andrade_svar.append({'nyckel': (fr or {}).get('nyckel') or sv.get('nyckel'), 'varde': sv['text'], 'status': 'kunden uppger', 'kalla': 'kundstart ändrat svar %s rev %s' % (sv['fraga_id'], sv['revision']), 'omrade': (fr or {}).get('omrade') or sv.get('omrade') or 'H', 'datum': str(sv['mottaget'])[:10]})
    iv.spara(kund, s)
    # Paketets egna listor svar och rattelser: varje post ska återfinnas i omgångarna respektive rattelser_fakta;
    # annars redovisas den, så att ingen kundutsaga kan försvinna spårlöst (texten finns kvar i exportfilen).
    i_omgangar = {(sv.get('fraga_id'), sv.get('revision')) for o in paket['omgangar'] for sv in o.get('svar', [])}
    saknade_svar = [sv for sv in paket['svar'] if (sv.get('fraga_id'), sv.get('revision')) not in i_omgangar]
    if saknade_svar:
        ej_registrerade.append({'omgang': None, 'skal': 'svar i paketets svar-lista utan omgång (finns kvar i exportfilen)', 'fragor': [str(sv.get('fraga_id')) for sv in saknade_svar]})
    speglade = {(r.get('nyckel'), r.get('kalla'), r.get('varde')) for r in paket['rattelser_fakta']}
    saknade_rattelser = [r for r in paket['rattelser'] if (r.get('nyckel'), 'kundstart rättelse rev %s' % r.get('revision'), r.get('varde')) not in speglade]
    if saknade_rattelser:
        ej_registrerade.append({'omgang': None, 'skal': 'rättelse i paketets rattelser-lista utan spegling i rattelser_fakta (finns kvar i exportfilen)', 'fragor': [str(r.get('nyckel')) for r in saknade_rattelser]})
    fakta_rader = []; forkastade = []
    def kalla_text(v, standard):
        v = re.sub(r'[\x00-\x1f]', ' ', str(v or standard)).strip()[:160]
        return v or standard
    def rev_i(kalla):
        m = re.search(r'\brev (\d+)', str(kalla or ''))
        return int(m.group(1)) if m else -1
    def giltig_rad(f):
        return isinstance(f, dict) and re.match(r'^[a-zåäö0-9_]{2,60}$', str(f.get('nyckel', ''))) and isinstance(f.get('varde'), str) and f['varde'].strip() and len(f['varde']) <= 4000 and str(f.get('omrade') or 'H') in iv.OMRADEN
    kund_rader = []
    for f in list(paket['rattelser_fakta']) + andrade_svar:
        if not giltig_rad(f):
            ej_registrerade.append({'omgang': None, 'skal': 'kundrad i fel form (finns kvar i exportfilen)', 'fragor': [str((f or {}).get('nyckel') if isinstance(f, dict) else f)[:60]]}); continue
        kund_rader.append({'nyckel': f['nyckel'], 'varde': f['varde'], 'kalla': kalla_text(f.get('kalla'), 'kundstart'), 'omrade': f.get('omrade') or 'H', 'datum': str(f.get('datum') or nu()[:10])[:10]})
    # Kundens ord som redan står i kundmappen (tidigare hämtningar) står över varje AI-tolkning skriven mot en äldre
    # revision; en tolkning som kommer i samma hämtning som kundens rättelse registreras och avgörs synligt nedan.
    kund_rev = {}
    for x in s['fakta']:
        if x.get('status') == 'kunden uppger' and str(x.get('kalla', '')).startswith('kundstart'):
            kund_rev[x['nyckel']] = max(kund_rev.get(x['nyckel'], -1), rev_i(x.get('kalla')))
    for f in kund_rader:
        kund_rev[f['nyckel']] = max(kund_rev.get(f['nyckel'], -1), rev_i(f.get('kalla')))
    for f in paket['fakta_ai']:
        if not giltig_rad(f):
            forkastade.append({'nyckel': str(f.get('nyckel'))[:60], 'skal': 'fel form'}); continue
        # samma tolkning som redan finns (även en ersatt) registreras aldrig igen: exporten är kumulativ
        if any(x['nyckel'] == f['nyckel'] and x['status'] == 'tolkning' and x['varde'] == f['varde'] for x in s['fakta']):
            continue
        if f['nyckel'] in kund_rev and rev_i(f.get('kalla')) <= kund_rev[f['nyckel']]:
            forkastade.append({'nyckel': f['nyckel'], 'skal': 'kundens senare uppgift (rev %d) står över tolkningen (rev %d)' % (kund_rev[f['nyckel']], rev_i(f.get('kalla')))}); continue
        fakta_rader.append({'nyckel': f['nyckel'], 'varde': f['varde'], 'status': 'tolkning', 'kalla': kalla_text(f.get('kalla'), 'kundstart AI'), 'omrade': f.get('omrade') or 'H', 'datum': str(f.get('datum') or nu()[:10])[:10]})
    for f in kund_rader:
        # jämförelsen görs mot samma sanerade form som lagras, så en kumulativ omhämtning aldrig ger dubbla kundrader
        if not any(x['nyckel'] == f['nyckel'] and x.get('kalla') == f['kalla'] and x['varde'] == f['varde'] for x in s['fakta']):
            fakta_rader.append({'nyckel': f['nyckel'], 'varde': f['varde'], 'status': 'kunden uppger', 'kalla': f['kalla'], 'omrade': f['omrade'], 'datum': f['datum']})
    if fakta_rader:
        faktafil = mapp / ('fakta-rev%d.json' % paket['arende']['revision'])
        faktafil.write_text(json.dumps(fakta_rader, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        try:
            s, _ = iv.fakta(kund, str(faktafil))
        except iv.Vagrad as e:
            ej_registrerade.append({'omgang': None, 'skal': 'faktarader vägrades av intervju.py: ' + e.args[0][:200], 'fragor': [f['nyckel'] for f in fakta_rader]})
            s = iv.las(kund); fakta_rader = []
        nya_fakta = len(fakta_rader)
        # En motsägelse där den äldre uppgiften bara var vår tolkning avgörs till kundens ord (rättelse eller ändrat svar), synligt och med skäl.
        for m in s['motsagelser']:
            if m['lage'] != 'oavgjord':
                continue
            r = next((x for x in kund_rader if x['nyckel'] == m['nyckel'] and x['varde'] == m['uppgift_2']['varde']), None)
            if r and m['uppgift_1']['status'] in ('tolkning', 'hypotes'):
                s, _ = iv.avgor(kund, m['id'], r['varde'], 'kundens ord i Kundstart (%s) ersätter vår %s' % (r['kalla'], m['uppgift_1']['status']))
    hamtade_filer = []
    if med_material:
        for m in paket['material']:
            # Paketet är data: id valideras, hämtningsvägen byggs här (aldrig ur paketets 'hamta'), filnamnet saneras.
            if m.get('typ') != 'fil' or not MATERIAL_ID.match(str(m.get('id', ''))) or not re.match(r'^[a-f0-9]{64}$', str(m.get('sha256', ''))):
                continue
            namn = re.sub(r'[^A-Za-z0-9._åäöÅÄÖ-]', '_', (m.get('filnamn') or 'fil'))[:120].strip('.') or 'fil'
            mal = (mapp / 'material' / ('%s-%s' % (m['id'], namn))).resolve()
            if mapp.resolve() not in mal.parents:
                continue
            if mal.is_file() and hashlib.sha256(mal.read_bytes()).hexdigest() == m['sha256']:
                continue
            mal.parent.mkdir(parents=True, exist_ok=True)
            data = anrop(bas, nyckel, 'GET', '/api/intern/arenden/%s/material/%s' % (d['arende_id'], m['id']), None, bypass, rå=True)
            if hashlib.sha256(data).hexdigest() != m['sha256']:
                raise Vagrad('materialets kontrollsumma stämmer inte: ' + m['id'])
            mal.write_bytes(data); hamtade_filer.append(str(mal))
    d['hamtat'].append({'tid': nu(), 'revision': paket['arende']['revision'], 'export_sha256': digest, 'svar': nya_svar, 'andrade_svar': len(andrade_svar), 'fakta': nya_fakta, 'omgangar': nya_omg, 'material': len(hamtade_filer), 'inlamningar': len(paket['arende'].get('inlamningar', [])), 'ej_registrerade': ej_registrerade, 'forkastade_tolkningar': forkastade})
    spara_kundstart(kund, d)
    msg = 'revision %d hämtad: %d omgångar, %d svar ordagrant, %d ändrade svar som kundens uppgift, %d faktarader, %d filer; kundens material ligger i %s (aldrig i repot)' % (paket['arende']['revision'], nya_omg, nya_svar, len(andrade_svar), nya_fakta, len(hamtade_filer), mapp)
    if ej_registrerade:
        msg += '; EJ REGISTRERADE: ' + json.dumps(ej_registrerade, ensure_ascii=False)
    if forkastade:
        msg += '; FÖRKASTADE TOLKNINGAR (kundens ord står över): ' + json.dumps(forkastade, ensure_ascii=False)
    return d, msg


def signaler(bas, nyckel, bypass):
    rows = []; cursor = None; seen = set()
    while True:
        path = '/api/intern/signaler' + ('?cursor=' + urllib.parse.quote(cursor, safe='') if cursor else '')
        r = anrop(bas, nyckel, 'GET', path, None, bypass)
        if r.get('schema') != 'kundstart-signaler/1' or not isinstance(r.get('signaler'), list):
            raise Vagrad('okänt signalschema')
        rows.extend(r['signaler']); cursor = r.get('cursor')
        if not cursor:
            return rows
        if not isinstance(cursor, str) or cursor in seen or len(seen) >= 10000:
            raise Vagrad('ogiltig eller upprepad signalcursor; ingen delscan kvitteras')
        seen.add(cursor)


def las_avvikelseplan(path, signal, digest, avvikelser):
    plan = json.loads(Path(path).read_text(encoding='utf-8'))
    if (plan.get('schema') != 'digitala-importavvikelse/1' or plan.get('signal_id') != signal['id']
            or plan.get('export_sha256') != digest or plan.get('avvikelser_sha256') != json_sha(avvikelser)
            or any(not isinstance(plan.get(k), str) or not plan[k].strip() for k in ('ansvarig', 'skal', 'nasta'))):
        raise Vagrad('avvikelseplan måste binda exakt signal, exporthash och avvikelser samt ange ansvarig, skal och nasta')
    return plan


def konsumera(kund, bas, nyckel, bypass, utforare, avvikelseplan=None):
    """Beständig mottagningskvittens med explicit importstatus. Öppna avvikelser kräver namngiven plan."""
    if not utforare:
        raise Vagrad('konsumera kräver namngiven --utforare')
    with konsumtionslas(kund):
        d = las_kundstart(kund)
        bunden(d, bas)
        aktuella = [r for r in signaler(bas, nyckel, bypass) if r.get('arende_id') == d['arende_id']]
        if not aktuella:
            # The server may have committed an ack whose response was lost. Reconcile exactly that ack.
            pending = [json.loads(p.read_text()) for p in (Path(kund) / 'KUNDSTART').glob('signal-*/KONSUMTION.json')]
            aktuella = [p['signal'] for p in pending if p.get('lage') == 'importerad']
            if not aktuella:
                return d, {'lage': 'inget nytt', 'arende_id': d['arende_id']}
        signal = max(aktuella, key=lambda r: r.get('revision', -1))
        if signal.get('id') != '%s:%s' % (d['arende_id'], signal.get('revision')) or not isinstance(signal.get('revision'), int):
            raise Vagrad('signalens id/revision har fel form')
        base = Path(kund) / 'KUNDSTART' / ('signal-' + str(signal['revision'])); base.mkdir(exist_ok=True)
        raw = base / 'EXPORT.json'; progress = base / 'KONSUMTION.json'
        if raw.is_file():
            paket = json.loads(raw.read_text())
        else:
            raw_bytes = anrop(bas, nyckel, 'GET', '/api/intern/arenden/%s/export' % d['arende_id'], None, bypass, rå=True)
            paket = json.loads(raw_bytes)
            if paket.get('signal', {}).get('id') != signal['id']:
                raise Vagrad('signalen ändrades före export; gör ny full scan nästa tick')
            privat_skriv(raw, raw_bytes.decode('utf-8'))
        if paket.get('signal', {}).get('id') != signal['id'] or paket.get('arende', {}).get('id') != d['arende_id']:
            raise Vagrad('sparad export gäller annat ärende/signal')
        digest = hashlib.sha256(raw.read_bytes()).hexdigest()
        state = json.loads(progress.read_text()) if progress.exists() else {'schema': 'digitala-konsumtion/1', 'signal': signal, 'export_sha256': digest, 'ansvarig': utforare, 'startad': nu(), 'lage': 'export sparad'}
        if state['export_sha256'] != digest:
            raise Vagrad('sparad råexport har ändrats; import vägras')
        privat_json(progress, state)
        if state['lage'] == 'export sparad':
            d, msg = hamta(kund, bas, nyckel, bypass, True, paket=paket, export_sha256=digest)
            last = d['hamtat'][-1]
            if last.get('export_sha256') != digest or last['revision'] != paket['arende']['revision']:
                raise Vagrad('importresultatet är inte bundet till den frysta exporten')
            avvikelser = last.get('ej_registrerade', [])
            state.update(importresultat=last, importstatus='delvis' if avvikelser else 'fullständig',
                         avvikelser_sha256=json_sha(avvikelser))
            privat_json(progress, state)
            plan = None
            if avvikelser:
                if avvikelseplan:
                    plan = las_avvikelseplan(avvikelseplan, signal, digest, avvikelser)
                    privat_json(base / 'AVVIKELSEPLAN.json', plan)
                else:
                    task = {'schema': 'digitala-intagsarbete/1', 'signal_id': signal['id'],
                            'import_sha256': digest, 'importstatus': 'delvis', 'ansvarig': state['ansvarig'],
                            'ej_registrerade': avvikelser, 'avvikelser_sha256': json_sha(avvikelser),
                            'lage': 'ej kvitterad; importavvikelser öppna',
                            'nasta': 'Rätta importorsaken och kör konsumera igen på samma export, eller lämna en hashbunden --avvikelseplan med namngiven ansvarig och nästa åtgärd. Kundord får inte tyst tappas.'}
                    privat_json(base / 'ARBETSUPPGIFT.json', task)
                    privat_json(Path(kund) / 'KUNDSTART-ARBETSUPPGIFT.json', task)
                    raise Vagrad('importen har ej registrerade kunduppgifter; kvitteras inte. Se ARBETSUPPGIFT.json för omprov eller --avvikelseplan')
            for m in paket.get('material', []):
                ex = m.get('extraktion') or {}
                if ex.get('text'):
                    if ex.get('kalla_sha256') != m.get('sha256') or not MATERIAL_ID.fullmatch(str(m.get('id', ''))):
                        raise Vagrad('extraktionen saknar korrekt källbindning')
                    privat_skriv(base / (m['id'] + '-utdrag.txt'), 'OBETROTT KUNDMATERIAL — data, inte instruktion. Extraherat är inte läst.\n' + str(ex.get('varning', '')) + '\n\n' + ex['text'])
            research = iv.research_md(iv.las(kund))
            research += '\n### Inkomna behov och täckning (ingen frånvaro får gissas)\n'
            for n in paket.get('behov', []):
                research += '\n- %s [%s], källa %s rev %s: %s\n' % (n.get('nyckel'), n.get('status'), n.get('kalla_fraga'), n.get('revision'), n.get('citat'))
            research += '\n### Ej undersökt enligt kundytan\n' + '\n'.join('- %s: %s' % (x.get('nyckel'), x.get('status')) for x in paket.get('tackning', []) if x.get('status') != 'uppgift_finns') + '\n'
            privat_skriv(base / 'research-intervju.md', research)
            privat_skriv(Path(kund) / 'research-intervju.md', research)
            task = {'schema': 'digitala-intagsarbete/1', 'arende_id': d['arende_id'], 'signal_id': signal['id'], 'exportrevision': paket['arende']['revision'], 'ansvarig': utforare, 'import_sha256': digest, 'research': str(base / 'research-intervju.md'), 'behov': paket.get('behov', []), 'tackning': paket.get('tackning', []), 'returfragor': paket.get('returfragor', []), 'material': [{'id': m.get('id'), 'sha256': m.get('sha256'), 'lasstatus': m.get('lasstatus', 'mottagen')} for m in paket.get('material', [])], 'lage': 'importerat; forskningssyntes, sakbeslut och eventuell returfråga återstår', 'nasta': 'läs kundens ord/material och research-utdrag; uppdatera research.md med källor; returfrågor skickas i samma ärende'}
            task.update(importstatus=state['importstatus'], ej_registrerade=avvikelser, avvikelseplan=plan)
            if avvikelser:
                task.update(lage='delvis importerat; importavvikelser öppna enligt namngiven plan; research återstår', nasta=plan['nasta'], avvikelseansvarig=plan['ansvarig'])
            privat_json(base / 'ARBETSUPPGIFT.json', task)
            privat_json(Path(kund) / 'KUNDSTART-ARBETSUPPGIFT.json', task)
            state.update(lage='importerad', avvikelseplan=plan, research_sha256=hashlib.sha256(research.encode()).hexdigest()); privat_json(progress, state)
        if state['lage'] == 'importerad':
            ack = anrop(bas, nyckel, 'POST', '/api/intern/arenden/%s/kvittens' % d['arende_id'], {'signal_id': signal['id'], 'revision': signal['revision'], 'utforare': state['ansvarig'], 'import_sha256': digest}, bypass)
            state.update(lage='kvitterad', kvittens=ack, avslutad=nu()); privat_json(progress, state)
        if state['lage'] == 'kvitterad':
            # A newer import includes the earlier customer history. Do not retry obsolete acks forever.
            for old_path in (Path(kund) / 'KUNDSTART').glob('signal-*/KONSUMTION.json'):
                old = json.loads(old_path.read_text())
                if old.get('lage') in ('export sparad', 'importerad') and old.get('signal', {}).get('revision', -1) < signal['revision']:
                    old.update(lage='ersatt av nyare import', ersatt_av=signal['id'], avslutad=nu())
                    privat_json(old_path, old)
        return d, {'lage': state['lage'], 'importstatus': state.get('importstatus', 'okänd (äldre kvitto)'), 'signal_id': signal['id'], 'ansvarig': state['ansvarig'], 'export_sha256': digest, 'kvitto': str(progress), 'arbete': str(base / 'ARBETSUPPGIFT.json')}


def returfragor(kund, bas, nyckel, bypass, path, utforare):
    body = json.loads(Path(path).read_text())
    if not utforare or not all(body.get(k) for k in ('idempotens', 'bas_revision', 'fragor')):
        raise Vagrad('returfragor kräver utforare och {idempotens, bas_revision, fragor}; revision från läst export')
    d = las_kundstart(kund)
    bunden(d, bas)
    if not d.get('hamtat') or body['bas_revision'] != d['hamtat'][-1]['revision']:
        raise Vagrad('returfrågor måste bindas till senast faktiskt importerad exportrevision')
    r = anrop(bas, nyckel, 'POST', '/api/intern/arenden/%s/returfragor' % d['arende_id'], {**body, 'utforare': utforare}, bypass)
    h = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    privat_json(Path(kund) / 'KUNDSTART' / ('returfragor-' + h + '.json'), {'begaran': body, 'utfall': r, 'utforare': utforare, 'tid': nu()})
    return d, r


def material_last(kund, bas, nyckel, bypass, mid, path, utforare):
    if not mid or not MATERIAL_ID.fullmatch(mid) or not utforare:
        raise Vagrad('last kräver giltigt --material-id och --utforare')
    proof = json.loads(Path(path).read_text())
    if not proof.get('resultat') or not proof.get('fil') or not re.fullmatch(r'[a-f0-9]{64}', str(proof.get('sha256', ''))):
        raise Vagrad('läsbevis kräver fil, sha256 och konkret resultat av faktisk läsning')
    p = Path(proof['fil']).resolve(); root = (Path(kund) / 'KUNDSTART' / 'material').resolve()
    if root not in p.parents or not p.name.startswith(mid + '-') or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != proof['sha256']:
        raise Vagrad('läsbeviset gäller inte hämtat material med samma hash')
    d = las_kundstart(kund)
    bunden(d, bas)
    r = anrop(bas, nyckel, 'POST', '/api/intern/arenden/%s/material/%s/lasning' % (d['arende_id'], mid), {'sha256': proof['sha256'], 'utforare': utforare, 'resultat': proof['resultat']}, bypass)
    privat_json(Path(kund) / 'KUNDSTART' / ('lasning-' + mid + '.json'), {'bevis': proof, 'utfall': r, 'tid': nu()})
    return d, r


def main(argv=None):
    p = argparse.ArgumentParser(prog='kundstart', description=__doc__.split('\n\n')[0])
    p.add_argument('kommando', choices=('skapa', 'status', 'hamta', 'lank', 'aterkalla', 'konsumera', 'returfragor', 'last'))
    p.add_argument('--kund', required=True); p.add_argument('--namn'); p.add_argument('--kontakt'); p.add_argument('--testdialog', action='store_true')
    p.add_argument('--avvikelseplan'); p.add_argument('--utforare'); p.add_argument('--fragor'); p.add_argument('--material-id'); p.add_argument('--lasbevis')
    p.add_argument('--dagar', type=int, default=30); p.add_argument('--material', action='store_true')
    p.add_argument('--bas-url', default=os.environ.get('KUNDSTART_BAS_URL')); p.add_argument('--nyckel-fil', default=os.environ.get('KUNDSTART_NYCKEL_FIL', '~/.nortropic-hemligheter/kundstart/KUNDSTART_INTERN_NYCKEL.secret'))
    p.add_argument('--bypass-fil', default=os.environ.get('KUNDSTART_BYPASS_FIL'))
    a = p.parse_args(argv)
    try:
        kund = Path(a.kund)
        if not kund.is_dir():
            raise Vagrad('kundmappen finns inte: ' + a.kund)
        if kund.resolve().is_relative_to(Path(__file__).resolve().parent.parent):
            raise Vagrad('kundmappen får inte ligga i repot')
        if not a.bas_url:
            raise Vagrad('ange --bas-url eller KUNDSTART_BAS_URL')
        nyckel = las_hemlig_fil(a.nyckel_fil)
        bypass = las_hemlig_fil(a.bypass_fil) if a.bypass_fil else None
        if a.kommando == 'skapa':
            if not a.namn:
                raise Vagrad('skapa kräver --namn')
            d, msg = skapa(a.kund, a.bas_url, nyckel, bypass, a.namn, a.kontakt, a.testdialog, a.dagar)
        elif a.kommando == 'status':
            d, msg = status(a.kund, a.bas_url, nyckel, bypass)
        elif a.kommando == 'hamta':
            with konsumtionslas(a.kund):
                d, msg = hamta(a.kund, a.bas_url, nyckel, bypass, a.material)
        elif a.kommando == 'konsumera':
            d, msg = konsumera(a.kund, a.bas_url, nyckel, bypass, a.utforare, a.avvikelseplan)
        elif a.kommando == 'returfragor':
            if not a.fragor: raise Vagrad('returfragor kräver --fragor')
            d, msg = returfragor(a.kund, a.bas_url, nyckel, bypass, a.fragor, a.utforare)
        elif a.kommando == 'last':
            if not a.lasbevis: raise Vagrad('last kräver --lasbevis')
            d, msg = material_last(a.kund, a.bas_url, nyckel, bypass, a.material_id, a.lasbevis, a.utforare)
        elif a.kommando == 'lank':
            d, msg = ny_lank(a.kund, a.bas_url, nyckel, bypass, a.dagar)
        else:
            d, msg = aterkalla(a.kund, a.bas_url, nyckel, bypass)
    except (Vagrad, iv.Vagrad) as e:
        print(json.dumps({'vagrad': e.args[0]}, ensure_ascii=False)); return 2
    print(json.dumps({'kommando': a.kommando, 'meddelande': msg, 'arende_id': d.get('arende_id'), 'testdialog': d.get('testdialog')}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
