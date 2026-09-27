#!/usr/bin/env python3
"""Kundstart: kundytan för intervjun (repot Nortropic/nortropic-kundstart) som en kanal i intervjusteget.

Kundmappen (INTERVJU.json, verktyg/intervju.py) är det auktoritativa hemmet för kundens uppgifter. Kundstart är
"sparat hos kundtjänsten" tills `hamta` har förts in i kundmappen ("överfört till Digitala"); research-steget gör
"bearbetat i research". Verktyget skickar inget till kunden: `skapa` skriver inbjudningslänken (en behörighet) till
`~/.nortropic-hemligheter/<kund>/KUNDSTART-LANK.secret` (0600; annan rot med KUNDSTART_HEMLIGHETER), och sessionen lämnar
den genom beställningens kanal.

    python3 -B verktyg/kundstart.py skapa  --kund DIR --namn "Kundens namn" [--kontakt "..."] [--testdialog] [--dagar 30]
    python3 -B verktyg/kundstart.py status --kund DIR
    python3 -B verktyg/kundstart.py hamta  --kund DIR [--material]    # export → INTERVJU.json (ordagrant) + FAKTA-rader + material
    python3 -B verktyg/kundstart.py lank   --kund DIR [--dagar 30]     # ny länk (t.ex. utgången eller byte av enhet)
    python3 -B verktyg/kundstart.py aterkalla --kund DIR              # återkallar aktuell länk

Åtkomst: miljövariabeln KUNDSTART_BAS_URL (tjänstens adress) och en fil med den interna nyckeln, rättighet 0600,
utanför /tmp: `--nyckel-fil` eller miljövariabeln KUNDSTART_NYCKEL_FIL (standard ~/.nortropic-hemligheter/kundstart/
KUNDSTART_INTERN_NYCKEL.secret). Nyckeln och länkens värde skrivs aldrig ut. Skyddad förhandsvisning hos Vercel
passeras med KUNDSTART_BYPASS_FIL (Protection Bypass for Automation), också 0600.
"""
import argparse
import hashlib
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
FRAGA_ID = re.compile(r'^[A-Z]+\d+$')


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


def spara_kundstart(kund, d):
    d['uppdaterad'] = nu()
    kundstart_fil(kund).write_text(json.dumps(d, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


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
    r = anrop(bas, nyckel, 'POST', '/api/intern/arenden/%s/lankar' % d['arende_id'], {'lank_dagar': dagar, 'bas_url': d['bas_url']}, bypass)
    d['lank_hash'] = r['lank_hash']; d['lank_utgar'] = r['utgar']
    spara_kundstart(kund, d)
    fil, _ = skriv_lank(kund, r['lank'], r['utgar'])
    return d, 'ny länk (gäller till %s) står i %s; den gamla länken gäller tills den återkallas' % (r['utgar'][:10], fil)


def aterkalla(kund, bas, nyckel, bypass):
    d = las_kundstart(kund)
    anrop(bas, nyckel, 'DELETE', '/api/intern/arenden/%s/lankar/%s' % (d['arende_id'], d['lank_hash']), None, bypass)
    d['lank_aterkallad'] = nu()
    spara_kundstart(kund, d)
    p = lank_fil(kund)
    if p.is_file():
        p.unlink()
    return d, 'länken är återkallad; kundens pågående sessioner slutar gälla'


def status(kund, bas, nyckel, bypass):
    d = las_kundstart(kund)
    r = anrop(bas, nyckel, 'GET', '/api/intern/arenden/%s' % d['arende_id'], None, bypass)
    vy = r['vy']
    return d, {'arende_id': d['arende_id'], 'svar': len(vy['dialog']), 'oppna_fragor': [f['id'] for f in vy['oppna']], 'bild': len(vy['bild']), 'material': len(vy['material']), 'aterstar': vy['aterstar'], 'inlamnad': vy['arende']['inlamnad'], 'ai': r['ai'], 'revision': vy['arende']['revision'], 'hamtat_till_revision': (d['hamtat'][-1]['revision'] if d['hamtat'] else None)}


def hamta(kund, bas, nyckel, bypass, med_material):
    """Exportpaketet in i kundmappen: varje Kundstart-omgång blir en omgång i INTERVJU.json med kundens svar ordagrant
    (intervju.py:s svar-funktion), AI-tolkningar blir FAKTA-rader med status 'tolkning', kundens rättelser FAKTA-rader
    med status 'kunden uppger'; motsägelser uppstår och avgörs i intervju.py:s ordinarie väg."""
    d = las_kundstart(kund)
    paket = anrop(bas, nyckel, 'GET', '/api/intern/arenden/%s/export' % d['arende_id'], None, bypass)
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
    sista = d['hamtat'][-1]['revision'] if d['hamtat'] else 0
    if paket['arende']['revision'] == sista:
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
                s, _ = iv.svar(kund, omg['nr'], str(svarfil))
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
    d['hamtat'].append({'tid': nu(), 'revision': paket['arende']['revision'], 'svar': nya_svar, 'andrade_svar': len(andrade_svar), 'fakta': nya_fakta, 'omgangar': nya_omg, 'material': len(hamtade_filer), 'inlamningar': len(paket['arende'].get('inlamningar', [])), 'ej_registrerade': ej_registrerade, 'forkastade_tolkningar': forkastade})
    spara_kundstart(kund, d)
    msg = 'revision %d hämtad: %d omgångar, %d svar ordagrant, %d ändrade svar som kundens uppgift, %d faktarader, %d filer; kundens material ligger i %s (aldrig i repot)' % (paket['arende']['revision'], nya_omg, nya_svar, len(andrade_svar), nya_fakta, len(hamtade_filer), mapp)
    if ej_registrerade:
        msg += '; EJ REGISTRERADE: ' + json.dumps(ej_registrerade, ensure_ascii=False)
    if forkastade:
        msg += '; FÖRKASTADE TOLKNINGAR (kundens ord står över): ' + json.dumps(forkastade, ensure_ascii=False)
    return d, msg


def main(argv=None):
    p = argparse.ArgumentParser(prog='kundstart', description=__doc__.split('\n\n')[0])
    p.add_argument('kommando', choices=('skapa', 'status', 'hamta', 'lank', 'aterkalla'))
    p.add_argument('--kund', required=True); p.add_argument('--namn'); p.add_argument('--kontakt'); p.add_argument('--testdialog', action='store_true')
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
            d, msg = hamta(a.kund, a.bas_url, nyckel, bypass, a.material)
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
