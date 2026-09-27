#!/usr/bin/env python3
"""Verksamhetsuppgifter: kundens VERKSAMHET.json — en sanning för namn, adress, telefon (NAP), räckvidd, öppettider,
kategorier, tjänster, sökkonsolens ägare (sokkonsol_agare) och omdömeskällan (omdomen_kalla), som SEO-kontrollen, lokal synlighet, annonsberedningen och sökkonsolen läser i stället för att
var och en gissa. Filen bor i kundmappen (aldrig i detta repo). `fiktiv: true` spärrar varje verklig extern åtgärd
(företagsprofil, sökkonsol-egenskap, annonser, citationer): en fiktiv verksamhet får aldrig en verklig profil.

    python3 -B verktyg/verksamhetsuppgifter.py kontrollera VERKSAMHET.json
    python3 -B verktyg/verksamhetsuppgifter.py nap VERKSAMHET.json
    python3 -B verktyg/verksamhetsuppgifter.py krav VERKSAMHET.json --ut KRAV.json   # obligatoriska copyelement till copy_kontroll

Utdata är JSON på stdout; exit 0 = giltig, 2 = ogiltig eller vägrad. Inga nätanrop, inga skrivningar utom --ut.
"""
import argparse
import json
import re
import sys
from pathlib import Path

SCHEMA = 1
KONTAKTTYPER = ('telefon', 'formular', 'dm', 'bokning', 'plats')
ROLLER = ('verksamhetsstalle', 'besoksadress', 'hemvist')
RACKVIDDER = ('lokal', 'regional', 'nationell', 'gransoverskridande')
DAGAR = ('man', 'tis', 'ons', 'tor', 'fre', 'lor', 'son')
ORGNR = re.compile(r'^\d{6}-\d{4}$')
POSTNUMMER = re.compile(r'^\d{3} \d{2}$')
KLOCKA = re.compile(r'^([01]\d|2[0-3]):[0-5]\d$')
E164_SE = re.compile(r'^\+46[1-9]\d{6,9}$')
NATIONELLT = re.compile(r'^0[1-9][\d\s-]{5,12}$')


class Vagrad(Exception):
    pass


def _str(v, name, errors, required=True, minlen=1):
    if v is None:
        if required:
            errors.append('%s saknas' % name)
        return
    if not isinstance(v, str) or len(v.strip()) < minlen:
        errors.append('%s ska vara en icke-tom sträng' % name)


def _list(v, name, errors, required=True, minst=0):
    if v is None:
        if required:
            errors.append('%s saknas' % name)
        return []
    if not isinstance(v, list) or any(not isinstance(x, str) or not x.strip() for x in v):
        errors.append('%s ska vara en lista av icke-tomma strängar' % name)
        return []
    if len(v) < minst:
        errors.append('%s ska ha minst %d post(er)' % (name, minst))
    return v


def e164(telefon):
    """Svenskt nummer i E.164; nationellt format (0xx-xxx xx xx) räknas om. Okänt format → None."""
    t = re.sub(r'[\s-]', '', telefon or '')
    if E164_SE.match(t):
        return t
    if t.startswith('0046'):
        t = '+' + t[2:]
        return t if E164_SE.match(t) else None
    if NATIONELLT.match(telefon or '') and t.startswith('0'):
        t = '+46' + t[1:]
        return t if E164_SE.match(t) else None
    return None


def validera(v):
    errors, varningar = [], []
    if not isinstance(v, dict):
        raise Vagrad(['VERKSAMHET.json ska vara ett objekt'])
    if v.get('schema') != SCHEMA:
        errors.append('schema ska vara %d' % SCHEMA)
    _str(v.get('namn'), 'namn', errors)
    if not isinstance(v.get('fiktiv'), bool):
        errors.append('fiktiv ska vara true eller false (obligatoriskt: fiktiva verksamheter får aldrig verkliga profiler)')
    if v.get('orgnr') is not None and not (isinstance(v['orgnr'], str) and ORGNR.match(v['orgnr'])):
        errors.append('orgnr ska ha formen NNNNNN-NNNN')
    kv = v.get('kontaktvagar')
    if not isinstance(kv, list) or not kv:
        errors.append('kontaktvagar ska vara en lista med minst en typad kontaktväg')
    else:
        for i, k in enumerate(kv):
            if not isinstance(k, dict) or k.get('typ') not in KONTAKTTYPER:
                errors.append('kontaktvagar[%d].typ ska vara en av %s' % (i, ', '.join(KONTAKTTYPER)))
                continue
            _str(k.get('varde'), 'kontaktvagar[%d].varde' % i, errors)
            _str(k.get('belagg'), 'kontaktvagar[%d].belagg' % i, errors)
            if k.get('typ') == 'telefon' and isinstance(k.get('varde'), str) and e164(k['varde']) is None:
                errors.append('kontaktvagar[%d].varde: telefonnumret är inte ett svenskt nummer i E.164 eller nationellt format' % i)
    adr = v.get('adress')
    if adr is not None:
        if not isinstance(adr, dict):
            errors.append('adress ska vara ett objekt')
        else:
            _str(adr.get('gata'), 'adress.gata', errors, required=False)
            if not (isinstance(adr.get('postnummer'), str) and POSTNUMMER.match(adr['postnummer'])):
                errors.append('adress.postnummer ska ha formen "NNN NN"')
            _str(adr.get('ort'), 'adress.ort', errors)
            if not isinstance(adr.get('publik'), bool):
                errors.append('adress.publik ska vara true eller false (styr om gatuadressen visas och läggs i strukturerad data)')
            if adr.get('roll') not in ROLLER:
                errors.append('adress.roll ska vara en av %s' % ', '.join(ROLLER))
            if adr.get('publik') is True and not adr.get('gata'):
                errors.append('adress.publik är true men gata saknas')
            if adr.get('roll') == 'hemvist' and adr.get('publik') is True:
                varningar.append('adressen är enbart registrerad hemvist men markerad publik; kontrollera att den får visas')
    rv = v.get('rackvidd')
    if not isinstance(rv, dict) or rv.get('typ') not in RACKVIDDER:
        errors.append('rackvidd.typ ska vara en av %s' % ', '.join(RACKVIDDER))
    else:
        orter = _list(rv.get('orter'), 'rackvidd.orter', errors, required=False)
        if rv['typ'] in ('lokal', 'regional') and not orter:
            errors.append('rackvidd.orter ska namnge minst en ort för lokal eller regional räckvidd')
        if adr is None and rv['typ'] == 'lokal' and not orter:
            errors.append('lokal räckvidd utan adress och utan orter')
    for i, o in enumerate(v.get('oppettider') or []):
        if not isinstance(o, dict) or o.get('dag') not in DAGAR or not all(isinstance(o.get(k), str) and KLOCKA.match(o[k]) for k in ('oppnar', 'stanger')):
            errors.append('oppettider[%d] ska vara {dag: man..son, oppnar: HH:MM, stanger: HH:MM}' % i)
    _list(v.get('kategorier'), 'kategorier', errors, required=False)
    _list(v.get('tjanster'), 'tjanster', errors, minst=1)
    if v.get('sprak') is not None:
        _str(v.get('sprak'), 'sprak', errors)
    webb = v.get('webb')
    if webb is not None and (not isinstance(webb, dict) or any(not isinstance(x, str) for x in webb.values())):
        errors.append('webb ska vara ett objekt med strängvärden (t.ex. doman)')
    agare = v.get('sokkonsol_agare')
    if agare is not None and (not isinstance(agare, list) or not agare or any(not isinstance(a, str) or '@' not in a for a in agare)):
        errors.append('sokkonsol_agare ska vara en lista med minst en e-postadress (kundens Google-konto som ägare av sökkonsolens egenskap)')
    ok = v.get('omdomen_kalla')
    if ok is not None:
        if not isinstance(ok, dict) or not isinstance(ok.get('plattform'), str) or not ok['plattform'].strip() or not isinstance(ok.get('datum'), str) or not re.match(r'^\d{4}-\d{2}-\d{2}$', ok['datum']):
            errors.append('omdomen_kalla ska vara {plattform, datum (ÅÅÅÅ-MM-DD), betyg?, antal?, url?}: verklig plattformsdata med datum, annars visas inget betyg')
        elif ('betyg' in ok and not isinstance(ok['betyg'], (int, float))) or ('antal' in ok and not isinstance(ok['antal'], int)):
            errors.append('omdomen_kalla.betyg ska vara ett tal och antal ett heltal')
    okanda = set(v) - {'schema', 'namn', 'fiktiv', 'orgnr', 'kontaktvagar', 'adress', 'rackvidd', 'oppettider', 'kategorier', 'tjanster', 'sprak', 'webb', 'e_post', 'not', 'sokkonsol_agare', 'omdomen_kalla'}
    if okanda:
        errors.append('okända fält: ' + ', '.join(sorted(okanda)))
    if errors:
        raise Vagrad(errors)
    return varningar


def las(path):
    try:
        v = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError) as e:
        raise Vagrad(['kan inte läsa %s: %s' % (path, e)])
    validera(v)
    return v


def telefon(v):
    for k in v.get('kontaktvagar') or []:
        if k.get('typ') == 'telefon':
            return k['varde'], e164(k['varde'])
    return None, None


def nap(v):
    """Namn, adress och telefon i den form som ska vara identisk i sajt, företagsprofil och citationer."""
    visning, e = telefon(v)
    adr = v.get('adress')
    return {'namn': v['namn'], 'adress_visas': bool(adr and adr.get('publik')),
            'adress': ('%s, %s %s' % (adr['gata'], adr['postnummer'], adr['ort'])) if adr and adr.get('publik') else None,
            'ort': adr['ort'] if adr else None, 'omrade': (v.get('rackvidd') or {}).get('orter') or [],
            'telefon_visning': visning, 'telefon_e164': e, 'fiktiv': v['fiktiv']}


def kraver_verklig(v, atgard):
    """Spärr före varje verklig extern åtgärd: en fiktiv verksamhet får ingen profil, egenskap, kampanj eller citation."""
    if v.get('fiktiv'):
        raise Vagrad(['%s vägras: verksamheten är markerad fiktiv (fiktiv: true) och får ingen verklig extern profil eller åtgärd' % atgard])


def krav(v):
    """Obligatoriska copyelement för copy_kontroll.py, härledda ur verksamhetsuppgifterna (inte ur en branschmall)."""
    rows = []
    visning, e = telefon(v)
    if visning:
        siffror = re.sub(r'\D', '', visning)
        nat = siffror if siffror.startswith('0') else '0' + siffror[2:] if siffror.startswith('46') else siffror
        mellan = r'[\s-]?'.join(re.escape(c) for c in nat)
        rows.append({'namn': 'telefon', 'var': 'varje sida', 'regex': '(%s|%s)' % (mellan, re.escape(e or visning)),
                     'skal': 'kontaktvägen telefon finns i verksamhetsuppgifterna; numret ska vara läsbar text på varje sida'})
    if v.get('orgnr'):
        rows.append({'namn': 'organisationsnummer', 'var': 'nagon sida', 'regex': re.escape(v['orgnr']), 'skal': 'företagsuppgifter (juridikflaggornas bas)'})
    orter = (v.get('rackvidd') or {}).get('orter') or []
    if orter:
        rows.append({'namn': 'serviceomrade', 'var': 'nagon sida', 'regex': '(' + '|'.join(re.escape(o) for o in orter) + ')', 'skal': 'räckviddens orter ska nämnas i text (lokal räckvidd)'})
    adr = v.get('adress')
    if adr and adr.get('publik'):
        rows.append({'namn': 'adress', 'var': 'nagon sida', 'regex': re.escape(adr['postnummer']) + r'\s+' + re.escape(adr['ort']), 'skal': 'publik adress ska stå med postnummer och ort'})
    return {'schema': 1, 'kalla': 'verksamhetsuppgifter.krav', 'namn': v['namn'], 'fiktiv': v['fiktiv'], 'krav': rows}


def main(argv=None):
    p = argparse.ArgumentParser(prog='verksamhetsuppgifter', description=__doc__.split('\n\n')[0])
    p.add_argument('kommando', choices=('kontrollera', 'nap', 'krav'))
    p.add_argument('fil')
    p.add_argument('--ut')
    a = p.parse_args(argv)
    try:
        v = las(a.fil)
        if a.kommando == 'kontrollera':
            out = {'giltig': True, 'namn': v['namn'], 'fiktiv': v['fiktiv'], 'varningar': validera(v)}
        elif a.kommando == 'nap':
            out = nap(v)
        else:
            out = krav(v)
            if a.ut:
                Path(a.ut).write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    except Vagrad as e:
        print(json.dumps({'giltig': False, 'fel': e.args[0]}, ensure_ascii=False, indent=1))
        return 2
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
