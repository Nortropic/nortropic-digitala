#!/usr/bin/env python3
"""Start- och fortsättningsvägen (HELHET-20260927, avsnitt 8): en beställning bär hela uppdraget från uppstart till
färdig privat leverans utan ägarstopp. Vägen är ansvarig för laddning (verktyg/ladda_steg.py per steg), nästa handling,
granskningsutfall, rättning, bevis och återupptagning — inte fler instruktioner att minnas. Tillståndet ligger i fallets
LAGE.json (utanför repot) med händelselogg per utförare; en färsk utförare (Claude eller Codex) kör `fortsatt` och får
nästa handling med laddad arbetsyta. Underkänt går till diagnos → åtgärd → omprov av samma steg. Utförda sidoeffekter
(driftsättningar, skickade meddelanden, kvitton) bokförs så att återupptagning inte upprepar leveranser.

    python3 -B verktyg/fortsatt.py --kund KUNDMAPP --fall FALL [--bestallning POST-ID] [--utforare claude|codex] [fortsatt]
    python3 -B verktyg/fortsatt.py --kund … --fall … klart --steg S --utfall klar|underkand|inte-tillampligt|vantar --not TEXT [--kvitto FIL …] [--sidoeffekt TEXT …] [--beroende TEXT]
    python3 -B verktyg/fortsatt.py --kund … --fall … omprova --steg S --not TEXT
    python3 -B verktyg/fortsatt.py --kund … --fall … status

Beställningen binds, inte bara namnges: kundmappens BESTALLNING.json är ett utdrag ur beställningens beslutspost
({"schema": 1, "post": "POST-ID", "kalla": "kontorets docs/decisions.md @ commit", "kund": "namn som i VERKSAMHET.json",
"omfattning": "privat-leverans" | "helhet" | [steg…], "lanseringsmandat": "POST-ID" eller null, "utdrag": "ordagrant …",
"testfall": true bara för fiktiv verksamhet}). Filens sha256 bokförs i LAGE.json; ändras filen bokförs ombindningen.
Utan filen blockeras varje beställningssteg med namngivet beroende; ett steg utanför omfattningen markeras 'inte
tillämpligt' av verktyget och omprövas vid varje körning (en senare utvidgad beställning återöppnar det).

Kanalstegen (seo, sokkonsol, lokal-synlighet, annonsberedning, uppfoljning) styrs av kundmappens KANALBEHOV.json ur
beredningen ({"seo": true, "sokkonsol": false, …}); saknas filen när ett kanalsteg står på tur blockeras vägen med ett
namngivet beroende i stället för att gissa. Lansering, sokkonsol och drift kräver lanseringsmandatet i BESTALLNING.json;
utan det slutar vägen vid färdig privat leverans (leverans), vilket är normalfallet — kommer mandatet senare återöppnas
stegen automatiskt. Verktygets egna markeringar ('markering': 'verktyg') omprövas varje körning; utförarens rapporterade
utfall ('markering': 'utforare') står tills `omprova` sätter steget i omprövning med en not.
"""
import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROT = HERE.parent
sys.path.insert(0, str(HERE))
import ladda_steg  # noqa: E402

KANALSTEG = ('seo', 'sokkonsol', 'lokal-synlighet', 'annonsberedning', 'uppfoljning')
LANSERINGSSTEG = ('lansering', 'sokkonsol', 'drift')
UTFALL = ('klar', 'underkand', 'inte-tillampligt', 'vantar')
STATUS_VERKTYG = 'inte tillämpligt'
STATUS_VANTAR = 'väntar (externt beroende)'


class Vagrad(Exception):
    pass


def nu():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def lage_stig(fall):
    return Path(fall) / 'LAGE.json'


def _kontrollera_fall(fall, rot):
    f = Path(fall).resolve()
    r = Path(rot).resolve()
    if f == r or r in f.parents:
        raise Vagrad('fallkatalogen får inte ligga i repot: ' + str(f))


def las(fall, kund=None, bestallning=None, rot=ROT):
    _kontrollera_fall(fall, rot)
    p = lage_stig(fall)
    if p.is_file():
        s = json.loads(p.read_text(encoding='utf-8'))
        if isinstance(s.get('bestallning'), str):  # schema 1: bara ett namngivet id, ingen bindning
            s['bestallning_begard'] = s['bestallning']; s['bestallning'] = None; s['schema'] = 2
        s.setdefault('bestallning', None)
        return s
    if not kund:
        raise Vagrad('ny LAGE.json kräver --kund')
    ordning = list(ladda_steg.las_steg(rot)['steg'].keys())
    return {'schema': 2, 'kund': str(Path(kund).resolve()), 'fall': str(Path(fall).resolve()), 'bestallning': None, 'bestallning_begard': bestallning, 'skapad': nu(), 'uppdaterad': nu(),
            'ordning': ordning, 'steg': {n: {'status': 'inte påbörjat', 'kvitton': [], 'noter': [], 'sidoeffekter': [], 'beroenden': [], 'underkanda': 0} for n in ordning},
            'logg': [], 'nasta': None}


def _skriv_privat(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(p.parent, 0o700)
    except OSError:
        pass
    p.write_text(text, encoding='utf-8')
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass


def spara(fall, s):
    s['uppdaterad'] = nu()
    _skriv_privat(lage_stig(fall), json.dumps(s, ensure_ascii=False, indent=1) + '\n')


def logga(s, utforare, handling, steg=None, detalj=None):
    s['logg'].append({'tid': nu(), 'utforare': utforare, 'handling': handling, 'steg': steg, 'detalj': detalj})


def _notera(st, text):
    if text not in st['noter']:
        st['noter'].append(text)


def _beroende(st, text):
    if text not in st['beroenden']:
        st['beroenden'].append(text)


def kanalbehov(s):
    p = Path(s['kund']) / 'KANALBEHOV.json'
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except ValueError:
        raise Vagrad('KANALBEHOV.json är inte giltig JSON')


def las_bestallning(s, rot=ROT):
    """Läser och prövar kundmappens BESTALLNING.json; returnerar (bindning, None) eller (None, skäl)."""
    p = Path(s['kund']) / 'BESTALLNING.json'
    if not p.is_file():
        return None, 'BESTALLNING.json saknas i kundmappen (utdrag ur beställningens beslutspost: post, kalla, kund, omfattning, lanseringsmandat, utdrag)'
    rå = p.read_bytes()
    try:
        b = json.loads(rå.decode('utf-8'))
    except ValueError:
        raise Vagrad('BESTALLNING.json är inte giltig JSON')
    for k in ('post', 'kalla', 'kund', 'omfattning', 'utdrag'):
        if not b.get(k):
            raise Vagrad('BESTALLNING.json saknar fältet %r' % k)
    if not ladda_steg.BESTALLNING.match(str(b['post'])):
        raise Vagrad('BESTALLNING.json: post ska vara beslutspostens namn, t.ex. DIGITALA-1-AGARBESLUT-20260926')
    if s.get('bestallning_begard') and s['bestallning_begard'] != b['post']:
        raise Vagrad('--bestallning %s stämmer inte med BESTALLNING.json (post %s)' % (s['bestallning_begard'], b['post']))
    steg = list(ladda_steg.las_steg(rot)['steg'].keys())
    omf = b['omfattning']
    if omf == 'helhet':
        omf_steg = steg
    elif omf == 'privat-leverans':
        omf_steg = [n for n in steg if n not in LANSERINGSSTEG]
    elif isinstance(omf, list) and omf and all(x in steg for x in omf):
        omf_steg = list(omf)
    else:
        raise Vagrad('BESTALLNING.json: omfattning ska vara "privat-leverans", "helhet" eller en lista av kända steg')
    lm = b.get('lanseringsmandat')
    if lm is not None and not ladda_steg.BESTALLNING.match(str(lm)):
        raise Vagrad('BESTALLNING.json: lanseringsmandat ska vara en beslutsposts namn eller null')
    v = Path(s['kund']) / 'VERKSAMHET.json'
    if not v.is_file():
        raise Vagrad('VERKSAMHET.json saknas i kundmappen: beställningen kan inte bindas till kunden (kund = VERKSAMHET.json:s namn)')
    if v.is_file():
        try:
            vd = json.loads(v.read_text(encoding='utf-8'))
        except ValueError:
            vd = {}
        if vd.get('namn') and vd['namn'] != b['kund']:
            raise Vagrad('BESTALLNING.json: kund %r är inte VERKSAMHET.json:s namn %r' % (b['kund'], vd['namn']))
        if vd.get('fiktiv') and not b.get('testfall'):
            raise Vagrad('BESTALLNING.json: fiktiv verksamhet kräver en beställning märkt "testfall": true')
        if b.get('testfall') and not vd.get('fiktiv'):
            raise Vagrad('BESTALLNING.json: "testfall": true kräver att VERKSAMHET.json anger fiktiv')
    return {'post': b['post'], 'kalla': b['kalla'], 'kund': b['kund'], 'omfattning': omf_steg, 'lanseringsmandat': lm, 'testfall': bool(b.get('testfall')),
            'fil': str(p.resolve()), 'sha256': hashlib.sha256(rå).hexdigest()}, None


def bind_bestallning(s, utforare, rot=ROT):
    """Binder (eller ombinder) beställningen i LAGE.json och bokför förändringar; returnerar skäl om den saknas."""
    b, skal = las_bestallning(s, rot)
    if b is None:
        return skal
    gammal = s.get('bestallning')
    if not gammal:
        b['bunden'] = nu(); s['bestallning'] = b; logga(s, utforare, 'beställning bunden', None, '%s sha256 %s' % (b['post'], b['sha256'][:12]))
    elif gammal.get('sha256') != b['sha256']:
        b['bunden'] = nu(); b['ersatte_sha256'] = gammal.get('sha256'); s['bestallning'] = b
        logga(s, utforare, 'beställning ombunden', None, 'BESTALLNING.json ändrad: sha256 %s → %s' % ((gammal.get('sha256') or '')[:12], b['sha256'][:12]))
    return None


def _verktygsmarkera(st, skal):
    st['status'] = STATUS_VERKTYG; st['markering'] = 'verktyg'; _notera(st, skal)


def _ateroppna(s, n, utforare, skal):
    st = s['steg'][n]
    st['status'] = 'inte påbörjat'; st.pop('markering', None); _notera(st, '%s återöppnat: %s' % (nu(), skal)); logga(s, utforare, 'återöppnat', n, skal)


def _tillamplighet(n, kb, best, defs):
    """Avgör ett stegs läge ur kanalbehov, beställning och lanseringsmandat: ('redo'|'markera'|'blockerad', skäl)."""
    if n in LANSERINGSSTEG:
        if not best:
            return 'blockerad', 'steget %s kräver en bunden beställning med lanseringsmandat (BESTALLNING.json)' % n
        if not best.get('lanseringsmandat'):
            return 'markera', 'inget lanseringsmandat i BESTALLNING.json: vägen slutar vid färdig privat leverans'
    if n in KANALSTEG:
        if kb is None:
            return 'blockerad', 'KANALBEHOV.json saknas i kundmappen (beredningens kanalbehov avgör vilka kanalsteg som ingår)'
        if kb.get(n) is False:
            return 'markera', 'kanalbehov: %s ingår inte i detta uppdrag (beredningen)' % n
        if kb.get(n) is not True:
            return 'blockerad', 'KANALBEHOV.json saknar avgörande för %s (true eller false)' % n
    if defs[n]['mandat'] == 'bestallning':
        if not best:
            return 'blockerad', 'steget %s kräver en bunden beställning: BESTALLNING.json saknas i kundmappen (utdrag ur beslutsposten)' % n
        if n not in best['omfattning']:
            return 'markera', 'beställningen %s omfattar inte steget' % best['post']
    return 'redo', None


def nasta_steg(s, utforare='claude', rot=ROT):
    """Första steget i ordningen som inte är klart, väntar eller inte tillämpligt; verktygets egna markeringar omprövas varje körning."""
    defs = ladda_steg.las_steg(rot)['steg']
    kb = kanalbehov(s)
    best = s.get('bestallning')
    saknade = [n for n in s['ordning'] if n not in defs]
    if saknade:
        raise Vagrad('fallets stegordning har steg som inte längre finns i steg/steg.json: %s (ny version av steg.json; avgör fallet manuellt)' % ', '.join(saknade))
    for n in s['ordning']:
        st = s['steg'][n]
        lage, skal = _tillamplighet(n, kb, best, defs)
        if st['status'] == STATUS_VERKTYG and st.get('markering') == 'verktyg':
            if lage == 'markera':
                _notera(st, skal); continue
            _ateroppna(s, n, utforare, 'verktygets markering gäller inte längre (%s)' % ('; '.join(x for x in st['noter'] if 'återöppnat' not in x)[-160:] or 'omprövad'))
        if st['status'] in ('klar', STATUS_VERKTYG, STATUS_VANTAR):
            continue
        if lage == 'blockerad':
            return n, 'blockerad', skal
        if lage == 'markera':
            _verktygsmarkera(st, skal); continue
        return n, 'redo', None
    vantar = [n for n, st in s['steg'].items() if st['status'] == STATUS_VANTAR]
    return None, 'slut', 'alla tillämpliga steg klara: färdig privat leverans' + (' och lansering' if s['steg'].get('lansering', {}).get('status') == 'klar' else '') + ('; väntar på externt beroende: ' + ', '.join(vantar) if vantar else '')


def nasta_md(s, namn, step, receipt):
    b = s.get('bestallning') or {}
    lines = ['# Nästa handling — %s (fall %s)' % (namn, Path(s['fall']).name), '',
             '**Utförare senast:** %s · **beställning:** %s (%s; omfattning %s; lanseringsmandat %s; sha256 %s) · **mandat:** %s' % (
                 (s['logg'][-1]['utforare'] if s['logg'] else '—'), b.get('post') or '—', b.get('kalla') or '—',
                 ('alla steg' if b.get('omfattning') == s['ordning'] else ', '.join(b.get('omfattning') or []) or '—'), b.get('lanseringsmandat') or 'inget', (b.get('sha256') or '')[:12] or '—', step['mandat']), '',
             '## Syfte', step['syfte'], '', '## Anvisning', step['anvisning'], '', '## Arbetsyta', receipt['arbetsyta'] + ' (läs UNDERLAG.md där; kvittot LADDNING.json binder körningarna)', '',
             '## Redan utfört i fallet (upprepa inte)']
    for n, st in s['steg'].items():
        for se in st['sidoeffekter']:
            lines.append('- %s: %s' % (n, se))
    if not any(st['sidoeffekter'] for st in s['steg'].values()):
        lines.append('- inga sidoeffekter bokförda')
    vantar = [(n, st) for n, st in s['steg'].items() if st['status'] == STATUS_VANTAR]
    if vantar:
        lines += ['', '## Väntar på externt beroende (omprova när det finns)']
        for n, st in vantar:
            lines.append('- %s: %s' % (n, '; '.join(st['beroenden']) or '—'))
    lines += ['', '## När steget är gjort', 'python3 -B verktyg/fortsatt.py --kund KUND --fall FALL klart --steg %s --utfall klar|underkand|inte-tillampligt|vantar --not "vad som gjordes" [--kvitto FIL] [--sidoeffekt "vad som verkställdes"] [--beroende "vad som saknas"]' % namn,
              '', 'Underkänt: diagnos → åtgärd → omprov av samma steg (KVALITET.md); ingen ägarfråga för sådant som ryms i uppdraget. Saknat externt beroende: --utfall vantar --beroende "vad" — vägen fortsätter med allt annat och steget omprövas med `omprova` när beroendet finns.']
    return '\n'.join(lines) + '\n'


def fortsatt(fall, kund, bestallning, utforare, rot=ROT, torr=False):
    s = las(fall, kund, bestallning, rot)
    if bestallning:
        s['bestallning_begard'] = bestallning
    s['bestallning_saknas'] = bind_bestallning(s, utforare, rot)
    namn, lage, skal = nasta_steg(s, utforare, rot)
    if lage == 'slut':
        s['nasta'] = {'steg': None, 'lage': 'slut', 'skal': skal}; logga(s, utforare, 'slut', None, skal); spara(fall, s)
        return s, {'nasta': None, 'lage': 'slut', 'meddelande': skal}
    if lage == 'blockerad':
        s['nasta'] = {'steg': namn, 'lage': 'blockerad', 'skal': skal}; _beroende(s['steg'][namn], skal); logga(s, utforare, 'blockerad', namn, skal); spara(fall, s)
        return s, {'nasta': namn, 'lage': 'blockerad', 'meddelande': skal}
    st = s['steg'][namn]
    defs = ladda_steg.las_steg(rot)['steg']
    if torr:
        return s, {'nasta': namn, 'lage': 'redo', 'meddelande': 'torr: skulle ladda ' + namn}
    if st['status'] == 'påbörjat' and st.get('laddning') and Path(st['laddning']).is_file():
        receipt = json.loads(Path(st['laddning']).read_text(encoding='utf-8'))
        _skriv_privat(Path(fall) / 'NASTA.md', nasta_md(s, namn, defs[namn], receipt))
        s['nasta'] = {'steg': namn, 'lage': 'påbörjat', 'arbetsyta': receipt['arbetsyta'], 'fil': str(Path(fall) / 'NASTA.md')}
        logga(s, utforare, 'återupptaget', namn, 'redan laddat: ' + Path(st['laddning']).parent.name); spara(fall, s)
        return s, {'nasta': namn, 'lage': 'påbörjat', 'arbetsyta': receipt['arbetsyta'], 'nasta_md': str(Path(fall) / 'NASTA.md'), 'meddelande': 'steget är redan laddat och påbörjat: läs NASTA.md och UNDERLAG.md i arbetsytan'}
    Path(fall).mkdir(parents=True, exist_ok=True)
    n = st['underkanda'] + 1 if st['status'] == 'underkänd' else 1
    ut = Path(fall) / ('laddning-%s-%d' % (namn, n))
    while ut.exists():
        n += 1; ut = Path(fall) / ('laddning-%s-%d' % (namn, n))
    post = s['bestallning']['post'] if (defs[namn]['mandat'] == 'bestallning' and s.get('bestallning')) else None
    receipt = ladda_steg.ladda(rot, namn, ut, kund=s['kund'], bestallning=post, utforare=utforare)
    st['status'] = 'påbörjat'; st['paborjat'] = st.get('paborjat') or nu(); st['laddning'] = str(ut / 'LADDNING.json'); st.pop('markering', None)
    _skriv_privat(Path(fall) / 'NASTA.md', nasta_md(s, namn, defs[namn], receipt))
    s['nasta'] = {'steg': namn, 'lage': 'påbörjat', 'arbetsyta': receipt['arbetsyta'], 'fil': str(Path(fall) / 'NASTA.md')}
    logga(s, utforare, 'påbörjat', namn, 'laddning ' + str(ut.name) + (' (omprov %d)' % (n - 1) if n > 1 else ''))
    spara(fall, s)
    return s, {'nasta': namn, 'lage': 'påbörjat', 'arbetsyta': receipt['arbetsyta'], 'nasta_md': str(Path(fall) / 'NASTA.md'), 'meddelande': 'läs NASTA.md och UNDERLAG.md i arbetsytan'}


def klart(fall, steg, utfall, notering, utforare, kvitton=(), sidoeffekter=(), beroende=None, rot=ROT):
    s = las(fall, rot=rot)
    if steg not in s['steg']:
        raise Vagrad('okänt steg: ' + steg)
    if utfall not in UTFALL:
        raise Vagrad('utfall ska vara en av ' + ', '.join(UTFALL))
    st = s['steg'][steg]
    if st['status'] != 'påbörjat':
        raise Vagrad('steget %s är inte laddat och påbörjat (status: %s); kör fortsatt först' % (steg, st['status']))
    if utfall == 'vantar' and not beroende:
        raise Vagrad('utfallet vantar kräver --beroende "vad som saknas"')
    for k in kvitton:
        if not Path(k).is_file():
            raise Vagrad('kvittot finns inte: ' + k)
        if str(Path(k).resolve()) not in st['kvitton']:
            st['kvitton'].append(str(Path(k).resolve()))
    for se in sidoeffekter:
        if se not in st['sidoeffekter']:
            st['sidoeffekter'].append(se)
    if beroende:
        _beroende(st, beroende)
    st['noter'].append('%s %s: %s' % (nu(), utfall, notering))
    st['markering'] = 'utforare'
    if utfall == 'klar':
        st['status'] = 'klar'; st['avslutat'] = nu()
    elif utfall == 'underkand':
        st['status'] = 'underkänd'; st['underkanda'] += 1
    elif utfall == 'vantar':
        st['status'] = STATUS_VANTAR
    else:
        st['status'] = STATUS_VERKTYG
    logga(s, utforare, utfall, steg, notering)
    s['nasta'] = None
    spara(fall, s)
    return s, {'steg': steg, 'status': st['status'], 'underkanda': st['underkanda'], 'nasta': 'kör fortsatt' if utfall != 'underkand' else 'diagnos → åtgärd → kör fortsatt (omprov av %s)' % steg}


def omprova(fall, steg, notering, utforare, rot=ROT):
    """Sätter ett rapporterat steg (klar, inte tillämpligt, väntar) i omprövning så att fortsatt laddar det igen."""
    s = las(fall, rot=rot)
    if steg not in s['steg']:
        raise Vagrad('okänt steg: ' + steg)
    st = s['steg'][steg]
    if st['status'] in ('påbörjat', 'inte påbörjat'):
        raise Vagrad('steget %s är redan öppet (status: %s)' % (steg, st['status']))
    tidigare = st['status']
    _ateroppna(s, steg, utforare, 'omprövning begärd (var %s): %s' % (tidigare, notering))
    s['nasta'] = None
    spara(fall, s)
    return s, {'steg': steg, 'status': st['status'], 'var': tidigare, 'nasta': 'kör fortsatt'}


def status(s):
    b = s.get('bestallning') or {}
    return {'kund': s['kund'], 'fall': s['fall'], 'bestallning': ({'post': b.get('post'), 'omfattning': b.get('omfattning'), 'lanseringsmandat': b.get('lanseringsmandat'), 'sha256': b.get('sha256'), 'testfall': b.get('testfall')} if b else None),
            'utforare_senast': s['logg'][-1]['utforare'] if s['logg'] else None,
            'steg': {n: st['status'] for n, st in s['steg'].items()}, 'underkanda': {n: st['underkanda'] for n, st in s['steg'].items() if st['underkanda']},
            'sidoeffekter': [n + ': ' + x for n, st in s['steg'].items() for x in st['sidoeffekter']], 'beroenden': [n + ': ' + x for n, st in s['steg'].items() for x in st['beroenden']],
            'vantar': [n for n, st in s['steg'].items() if st['status'] == STATUS_VANTAR],
            'nasta': s.get('nasta'), 'handelser': len(s['logg']), 'uppdaterad': s.get('uppdaterad')}


def main(argv=None):
    p = argparse.ArgumentParser(prog='fortsatt', description=__doc__.split('\n\n')[0])
    p.add_argument('kommando', nargs='?', default='fortsatt', choices=('fortsatt', 'klart', 'omprova', 'status'))
    p.add_argument('--kund'); p.add_argument('--fall', required=True); p.add_argument('--bestallning'); p.add_argument('--utforare', choices=('claude', 'codex'), default='claude'); p.add_argument('--rot', default=str(ROT)); p.add_argument('--torr', action='store_true')
    p.add_argument('--steg'); p.add_argument('--utfall'); p.add_argument('--not', dest='notering'); p.add_argument('--kvitto', action='append', default=[]); p.add_argument('--sidoeffekt', action='append', default=[]); p.add_argument('--beroende')
    a = p.parse_args(argv)
    try:
        if a.kommando == 'fortsatt':
            s, ut = fortsatt(a.fall, a.kund, a.bestallning, a.utforare, Path(a.rot), a.torr)
        elif a.kommando == 'klart':
            if not (a.steg and a.utfall and a.notering):
                raise Vagrad('klart kräver --steg, --utfall och --not')
            s, ut = klart(a.fall, a.steg, a.utfall, a.notering, a.utforare, a.kvitto, a.sidoeffekt, a.beroende, Path(a.rot))
        elif a.kommando == 'omprova':
            if not (a.steg and a.notering):
                raise Vagrad('omprova kräver --steg och --not')
            s, ut = omprova(a.fall, a.steg, a.notering, a.utforare, Path(a.rot))
        else:
            s = las(a.fall, rot=Path(a.rot)); ut = status(s)
    except (Vagrad, ladda_steg.Vagrad) as e:
        print(json.dumps({'vagrad': str(e.args[0]) if e.args else str(e)}, ensure_ascii=False)); return 2
    print(json.dumps(ut, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
