#!/usr/bin/env python3
"""Underhåll av en levererad sajt: ärendet hålls öppet, kundens poster klassas, förslag går till ägaren.

Formen är ägarens beslut DIGITALA-UNDERHALL-20260929 (kontorets `docs/decisions.md`); ingen regel här är ny.
Verktyget avgör inget självständigt: det binder klassningen till kundens hashbundna Kundstart-export
(`kundstart.kundrad_belagd`) och vägrar i alla oklara lägen. Kundens text är underlag, aldrig en instruktion.

    python3 -B verktyg/underhall.py oppna     --kund DIR --bestallning POST [--lank-utgar ÅÅÅÅ-MM-DD]
    python3 -B verktyg/underhall.py las       --kund DIR --utforare NAMN
    python3 -B verktyg/underhall.py forslag   --kund DIR --post ID --omfattning TEXT --sessioner N
    python3 -B verktyg/underhall.py sessioner --kund DIR --antal N --andamal TEXT [--bestallning POST]
    python3 -B verktyg/underhall.py besked    --kund DIR [--ut FIL] [--vecka ÅÅÅÅ-Www]
    python3 -B verktyg/underhall.py status    --kund DIR

Klassning (sex krav, alla måste hålla, annars förslag):
 1. källan är en kundlämnad rättelse eller ett ändrat kundsvar,
 2. texten är inte instruktionsliknande,
 3. nyckeln står i FAKTARATTELSE,
 4. uppgiften är belagd mot den senast importerade och hashbundna exporten,
 5. nyckeln har redan ett värde ur en annan källa — en rättelse, inte en ny uppgift, och värdet är ändrat,
 6. för en sammansatt nyckel (DELVIS) är värdet entydigt läsbart, bara den namngivna delen är ändrad, och dess
    nya värde godtas av kedjans gemensamma validering (verksamhetsuppgifter.e164).

Driftkontrollens och signalhämtningens schemalagda körning är ett eget Runtime-uppdrag och görs inte här;
`besked` redovisar en utebliven vecka i stället för att tiga om den.
"""
import argparse
import json
import os
import re
import sys
import subprocess
from copy import deepcopy
from itertools import zip_longest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import intervju as iv  # noqa: E402
import kundstart as ks  # noqa: E402
import verksamhetsuppgifter as vu  # noqa: E402

TAK_SESSIONER = 20  # läsande modellsessioner per kalendermånad (DIGITALA-UNDERHALL-20260929)
BESTALLNING = re.compile(r'^[A-ZÅÄÖ0-9-]{6,80}$')

# De fyra exemplen i den text ägaren godtog 2026-09-29 07:33Z ("öppettider, telefon, pris, en medarbetare som
# slutat") — inte ägarens egna ord, men innehållet i det han godtog. Listan är stängd och tolkas smalt: en nyckel
# utanför den blir ett förslag till ägaren, och att vidga den kräver ägarens beslut.
#
# Det fjärde exemplet, en medarbetare som slutat, står inte här. Skälet är namngivet och inte ett förbiseende:
# formens del 4 lägger personuppgifter i förslagsvägen, och en fri textrad går inte att skilja mekaniskt från att
# en medarbetare tillkommit. Tills ägaren avgör det är en personaländring ett förslag (den säkra sidan).
FAKTARATTELSE = {
    'oppettider': 'öppettider',
    'kontaktvagar': 'telefonnummer',
    'pris': 'pris kunden själv anger',
}

# Nycklar vars värde är sammansatt och där bara en namngiven del får rättas inom stående mandat. Exemplet ägaren
# godtog är "telefon", inte kontaktvägar i stort: en ändrad formulärsökväg eller e-postadress är alltså ett förslag.
DELVIS = {'kontaktvagar': ('telefon',)}

# Formkrav för den tillåtna delens nya värde. Utan det kan fri prosa rida med inne i telefonledet och ändå räknas som
# att bara telefonnumret ändrats; ett värde som inte ser ut som ett nummer avgörs av ägaren.
# PTS svenska nummerplan, läst 2026-09-30:
# https://pts.se/internet-och-telefoni/telefonnummer-och-adressering/
BETALNUMMER_E164 = ('+46900', '+46939', '+46944')
DELNAMN = {'telefon': 'telefonnummer'}   # läsbart namn i skälet

# Kundtext som ser ut som en instruktion till utföraren. Träff stoppar inte posten, men den kan aldrig bli
# faktarättelse: den redovisas som underlag och går till ägaren.
INSTRUKTION = re.compile(
    r'(?i)(ignorera|bortse från|glöm)\s+(alla\s+|tidigare\s+|föregående\s+|dina\s+)*(regler|instruktioner|mandat|beställning)'
    r'|\b(ta bort|radera|publicera|lansera|driftsätt|släpp)\s+(sidan|sajten|webbplatsen|allt)\b'
    r'|\b(du ska|du måste|systemprompt|system prompt)\b'
    r'|\b(ignore|disregard|forget)\s+(all\s+|previous\s+|prior\s+|your\s+)*(instructions|rules|prompt)\b'
    r'|\b(delete|remove|publish|deploy)\s+(the\s+)?(page|site|website|everything)\b')

KUNDKALLA = re.compile(r'^kundstart (rättelse rev [1-9][0-9]*|ändrat svar [A-Z0-9_]+ rev [1-9][0-9]*)$')


class Vagrad(Exception):
    pass


def nu():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def fil(kund):
    return Path(kund) / 'UNDERHALL.json'


def las(kund):
    p = fil(kund)
    if not p.is_file():
        raise Vagrad('ärendet hålls inte öppet för underhåll i %s (kör oppna)' % kund)
    return json.loads(p.read_text(encoding='utf-8'))


def spara(kund, d):
    d['uppdaterad'] = nu()
    ks.privat_json(fil(kund), d)


def oppna(kund, bestallning, lank_utgar=None):
    """Märker ärendet som öppet efter leveransen. Kundstarts länk gäller i 30 dagar; datumet bokförs så att
    `besked` kan påminna innan den går ut (en ny länk ges med kundstart.py lank)."""
    if not BESTALLNING.match(str(bestallning or '')):
        raise Vagrad('--bestallning ska vara beslutspostens namn, t.ex. DIGITALA-UNDERHALL-20260929')
    if not Path(kund).is_dir():
        raise Vagrad('kundmappen finns inte: %s' % kund)
    if lank_utgar is not None and not re.fullmatch(r'\d{4}-\d{2}-\d{2}', lank_utgar):
        raise Vagrad('--lank-utgar ska vara ÅÅÅÅ-MM-DD')
    p = fil(kund)
    if p.is_file():
        d = las(kund)
        d['bestallning'] = bestallning
        if lank_utgar:
            d['lank_utgar'] = lank_utgar
        spara(kund, d)
        return d, 'ärendet var redan öppet; beställning och länkdatum uppdaterade'
    d = {'schema': 1, 'kund': Path(kund).name, 'bestallning': bestallning, 'oppet_efter_leverans': True,
         'oppnat': nu(), 'lank_utgar': lank_utgar, 'poster': [], 'sessioner': [], 'besked': []}
    spara(kund, d)
    return d, 'ärendet hålls öppet efter leveransen'


def _kanda_nycklar_utan(s, kalla):
    """Nycklar som redan har ett värde ur en annan källa än den rad vi prövar.

    Första träffen gäller, alltså kundmappens ursprungliga uppgift före kundens rättelser. Det är medvetet och
    försiktigt: en sammansatt rad jämförs mot originalet, så varje avvikelse utanför den tillåtna delen blir ett
    förslag även i en kedja av rättelser. Felet går åt det säkra hållet (fler förslag, aldrig fler egna ändringar).
    """
    ut = {}
    for f in s.get('fakta', []):
        if f.get('kalla') == kalla:
            continue
        if str(f.get('varde', '')).strip() and not iv.okand(f):
            ut.setdefault(f['nyckel'], f)
    return ut


def _delar(varde):
    """'telefon: 070-…; formular: /kontakt' → {'telefon': '070-…', 'formular': '/kontakt'} (intervju.py:s form).

    Strikt, och None så snart värdet inte är entydigt läsbart: varje del ska vara "typ: värde" med båda leden
    ifyllda, och ingen typ får förekomma två gånger. Annars kan text utanför de kända delarna åka med i en rättelse
    som ser ut att bara röra telefonnumret, eller en dubblett maskera vilken del som ändrats. Ett avslutande
    semikolon är ingen del.
    """
    ut = {}
    bitar = [b.strip() for b in str(varde or '').split(';') if b.strip()]
    if not bitar:
        return None
    for bit in bitar:
        if ':' not in bit:
            return None
        typ, v = bit.split(':', 1)
        typ, v = typ.strip().lower(), v.strip()
        if not typ or not v or typ in ut:
            return None
        ut[typ] = v
    return ut


def _bara_tillaten_del(nyckel, gammalt, nytt):
    """(ok, skal) för en nyckel i DELVIS: bara den namngivna delen får skilja, och ingen del får läggas till."""
    tillatna = DELVIS[nyckel]
    g, n = _delar(gammalt), _delar(nytt)
    if g is None or n is None:
        return False, 'det sammansatta värdet går inte att läsa entydigt i delar; avgörs av ägaren'
    if set(g) != set(n):
        return False, 'en kontaktväg har lagts till eller tagits bort, inte bara %s' % ', '.join(tillatna)
    andrade = sorted(k for k in g if g[k] != n[k])
    if not andrade:
        return False, 'ingen del av värdet är ändrad'
    utanfor = [k for k in andrade if k not in tillatna]
    if utanfor:
        return False, 'ändringen rör %s, inte bara %s' % (', '.join(utanfor), ', '.join(tillatna))
    for k in andrade:
        number = vu.e164(n[k]) if k == 'telefon' else None
        if k == 'telefon' and number is None:
            return False, ('det nya värdet ser inte ut som ett %s; avgörs av ägaren' % DELNAMN.get(k, k))
        if number and number.startswith(BETALNUMMER_E164):
            return False, 'betalnummer enligt PTS nummerplan; avgörs av ägaren'
    return True, ''


def klassa(kund, uppgift, s=None):
    """(klass, skal) för en kundrad. Fail-closed: bara alla sex uppfyllda krav ger faktarättelse."""
    s = s if s is not None else iv.las(kund)
    nyckel = str(uppgift.get('nyckel', ''))
    kalla = str(uppgift.get('kalla', ''))
    if not KUNDKALLA.match(kalla):
        return 'forslag', 'källan %r är inte en kundlämnad rättelse eller ett ändrat kundsvar' % kalla[:60]
    if INSTRUKTION.search(str(uppgift.get('varde', ''))):
        return 'forslag', 'kundtexten är formulerad som en instruktion; den är underlag och avgörs av ägaren'
    if nyckel not in FAKTARATTELSE:
        return 'forslag', 'nyckeln %r står inte i den stängda listan över faktarättelser' % nyckel
    if not ks.kundrad_belagd(kund, uppgift):
        return 'forslag', 'uppgiften är inte belagd mot den senast importerade exporten'
    kanda = _kanda_nycklar_utan(s, kalla)
    if nyckel not in kanda:
        return 'forslag', 'nyckeln %r har inget tidigare värde: en ny uppgift, inte en rättelse' % nyckel
    if str(kanda[nyckel].get('varde', '')).strip() == str(uppgift.get('varde', '')).strip():
        return 'forslag', 'värdet är oförändrat mot det kända; ingen rättelse att göra'
    if nyckel in DELVIS:
        ok, skal = _bara_tillaten_del(nyckel, kanda[nyckel].get('varde'), uppgift.get('varde'))
        if not ok:
            return 'forslag', skal
    if nyckel == 'oppettider':
        parsed = vu.tolka_oppettider(uppgift.get('varde'))
        if parsed is None:
            return 'forslag', 'öppettiderna saknar entydig veckoform; prosa, delad dag och midnatt avgörs av ägaren'
        old = vu.tolka_oppettider(kanda[nyckel].get('varde'))
        if parsed == old:
            return 'forslag', 'öppettiderna är oförändrade i strukturerad form; ingen rättelse att göra'
        try:
            verksamhet = json.loads((Path(kund) / 'VERKSAMHET.json').read_text(encoding='utf-8'))
            verksamhet['oppettider'] = parsed
            vu.validera(verksamhet)
        except (OSError, ValueError, TypeError, vu.Vagrad):
            return 'forslag', 'öppettiderna kan inte valideras i VERKSAMHET.json; avgörs av ägaren'
    return 'faktarattelse', 'kundens egen rättelse av %s, belagd mot exporten' % FAKTARATTELSE[nyckel]


def las_poster(kund, utforare):
    """Läser kundmappens fakta, klassar varje kundlämnad rad och bokför den. Ingen ändring av sajten görs här."""
    if not str(utforare or '').strip():
        raise Vagrad('las kräver namngiven --utforare')
    d = las(kund)
    if not d.get('oppet_efter_leverans'):
        raise Vagrad('ärendet är inte öppet efter leveransen')
    s = iv.las(kund)
    kanda = {(p['nyckel'], p['kalla']) for p in d['poster']}
    nya = []
    for f in s.get('fakta', []):
        kalla = str(f.get('kalla', ''))
        if not KUNDKALLA.match(kalla) or (f['nyckel'], kalla) in kanda:
            continue
        klass, skal = klassa(kund, f, s)
        post = {'id': 'u_%s_%s' % (f['nyckel'], re.sub(r'[^0-9]', '', kalla) or '0'),
                'nyckel': f['nyckel'], 'varde': f['varde'], 'kalla': kalla, 'klass': klass, 'skal': skal,
                'instruktionslik': bool(INSTRUKTION.search(str(f.get('varde', '')))),
                'sedd': nu(), 'utforare': utforare, 'atgard': None}
        d['poster'].append(post); nya.append(post)
    spara(kund, d)
    return d, nya


def kontrollera_filer(fore, efter, nyckel, gammalt, nytt):
    """Ren diffkontroll: endast exakta värdebyten och motsvarande verksamhetsfält.

    Mappningarna innehåller filnamn och UTF-8-bytes. Nya/raderade filer, binärer,
    andra värden och omformatering vägras. Inga modeller eller kundskrivningar.
    """
    if nyckel == 'kontaktvagar':
        ok, skal = _bara_tillaten_del(nyckel, gammalt, nytt)
        if not ok:
            return [{'fil': None, 'rad': None, 'skal': skal}]
        old, new = _delar(gammalt)['telefon'], _delar(nytt)['telefon']
        pairs = [(old, new)]
        if vu.e164(old):
            pairs.append((vu.e164(old), vu.e164(new)))
    elif nyckel == 'oppettider':
        old, new = vu.tolka_oppettider(gammalt), vu.tolka_oppettider(nytt)
        if old is None or new is None:
            return [{'fil': None, 'rad': None, 'skal': 'gamla och nya öppettider måste ha entydig veckoform'}]
        pairs = [(str(gammalt), str(nytt))]
        for ascii_ in (False, True):
            for separators in (None, (',', ':')):
                pairs.append((json.dumps(old, ensure_ascii=ascii_, separators=separators),
                              json.dumps(new, ensure_ascii=ascii_, separators=separators)))
    else:
        return [{'fil': None, 'rad': None, 'skal': 'diffkontrollen omfattar telefon och öppettider; annat kräver separat prövning'}]
    replacements = dict((a, b) for a, b in pairs if a and a != b)
    if not replacements:
        return [{'fil': None, 'rad': None, 'skal': 'ingen ändring att kontrollera'}]
    pattern = re.compile('|'.join(re.escape(a) for a in sorted(replacements, key=len, reverse=True)))
    fynd = []
    for name in sorted(set(fore) | set(efter)):
        if name not in fore or name not in efter:
            fynd.append({'fil': name, 'rad': 1, 'skal': 'fil tillagd eller borttagen'}); continue
        if fore[name] == efter[name]:
            continue
        try:
            before, after = fore[name].decode('utf-8'), efter[name].decode('utf-8')
            expected = pattern.sub(lambda m: replacements[m[0]], before)
            if name == 'VERKSAMHET.json':
                original, actual = json.loads(before), json.loads(after)
                wanted = deepcopy(original)
                if nyckel == 'oppettider':
                    if original.get('oppettider') != old:
                        raise ValueError('gamla verksamhetstider skiljer sig från belagd rättelse')
                    wanted['oppettider'] = new
                else:
                    for row in wanted.get('kontaktvagar', []):
                        if row.get('typ') == 'telefon' and row.get('varde') in replacements:
                            row['varde'] = replacements[row['varde']]
                vu.validera(actual)
                if wanted == actual:
                    continue
            elif expected == after:
                continue
            rad = next((i for i, (a, b) in enumerate(zip_longest(expected.splitlines(), after.splitlines()), 1)
                        if a != b), 1)
            fynd.append({'fil': name, 'rad': rad, 'skal': 'ändring utöver den belagda faktarättelsen'})
        except (ValueError, TypeError, KeyError, vu.Vagrad):
            fynd.append({'fil': name, 'rad': 1, 'skal': 'oläsbar eller ogiltig fil för faktarättelsen'})
    return fynd


def kontrollera(kund, post_id, repo, bas, kandidat):
    """Läs två exakta Git-träd; belägg kundraden på nytt före diffkontroll."""
    if not repo or not all(re.fullmatch('[0-9a-f]{40}', x or '') for x in (bas, kandidat)):
        raise Vagrad('kontrollera kräver --repo samt fullständiga --bas och --kandidat')
    post = next((p for p in las(kund)['poster'] if p['id'] == post_id), None)
    s = iv.las(kund)
    if post is None or klassa(kund, post, s)[0] != 'faktarattelse':
        raise Vagrad('posten är inte en nu belagd faktarättelse')
    gammalt = _kanda_nycklar_utan(s, post['kalla'])[post['nyckel']]['varde']
    def git(*args):
        return subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True, timeout=30).stdout
    def tree(ref):
        if git('cat-file', '-t', ref).strip() != b'commit':
            raise Vagrad('bas och kandidat ska vara commits')
        return {name.decode('utf-8'): head.decode().split() for head, name in
                (entry.split(b'\t', 1) for entry in git('ls-tree', '-rz', ref).split(b'\0') if entry)}
    try:
        first, last = tree(bas), tree(kandidat)
        changed = {name for name in set(first) | set(last) if first.get(name) != last.get(name)}
        fore, efter = {}, {}
        for name in changed:
            for index, result in ((first, fore), (last, efter)):
                if name in index:
                    mode, kind, oid = index[name]
                    if kind != 'blob' or mode not in ('100644', '100755'):
                        raise Vagrad('faktarättelse får bara ändra vanliga filer: ' + name)
                    result[name] = git('cat-file', 'blob', oid)
            if name in first and name in last and first[name][:2] != last[name][:2]:
                raise Vagrad('filtyp eller rättighet ändrad: ' + name)
        fynd = kontrollera_filer(fore, efter, post['nyckel'], gammalt, post['varde'])
        if not changed:
            fynd.append({'fil': None, 'rad': None, 'skal': 'ingen införd rättelse mellan bas och kandidat'})
        return {'schema': 1, 'bas': bas, 'kandidat': kandidat, 'post': post_id,
                'godkand': not fynd, 'fynd': fynd, 'not': 'modellfri diffkontroll; ordinarie kvalitetskontroller kvarstår'}
    except (subprocess.SubprocessError, OSError, UnicodeError, ValueError) as error:
        raise Vagrad('Git-underlaget kunde inte kontrolleras: ' + type(error).__name__) from error


def forslag(kund, post_id, omfattning, sessioner):
    """Ett förslag till ägaren med omfattning och uppskattat antal sessioner. Ägaren säger ja eller nej."""
    if sessioner < 1:
        raise Vagrad('--sessioner ska vara minst 1 (uppskattat antal modellsessioner)')
    if not str(omfattning or '').strip():
        raise Vagrad('--omfattning krävs: vad förslaget omfattar')
    d = las(kund)
    post = next((p for p in d['poster'] if p['id'] == post_id), None)
    if post is None:
        raise Vagrad('okänd post %r (kör las och status)' % post_id)
    if post['klass'] != 'forslag':
        raise Vagrad('post %s är klassad %s, inte forslag' % (post_id, post['klass']))
    post['atgard'] = {'typ': 'forslag_till_agaren', 'omfattning': str(omfattning).strip()[:400],
                      'uppskattade_sessioner': int(sessioner), 'skrivet': nu(), 'agarens_svar': None}
    spara(kund, d)
    return d, post


def sessioner(kund, antal, andamal, bestallning=None):
    """Bokför läsande modellsessioner mot taket. Över taket krävs en beställning; ingen tyst överskridning."""
    if antal < 1:
        raise Vagrad('--antal ska vara minst 1')
    if not str(andamal or '').strip():
        raise Vagrad('--andamal krävs')
    d = las(kund)
    manad = nu()[:7]
    forbrukat = sum(x['antal'] for x in d['sessioner'] if x['tid'][:7] == manad)
    if forbrukat + antal > TAK_SESSIONER and not bestallning:
        raise Vagrad('taket %d läsande modellsessioner för %s är förbrukat (%d bokförda, %d begärda); '
                     'en utvidgning kräver ägarens beställning (--bestallning POST)'
                     % (TAK_SESSIONER, manad, forbrukat, antal))
    if bestallning and not BESTALLNING.match(str(bestallning)):
        raise Vagrad('--bestallning ska vara beslutspostens namn')
    d['sessioner'].append({'tid': nu(), 'antal': int(antal), 'andamal': str(andamal).strip()[:200],
                           'over_taket_bestallning': bestallning})
    spara(kund, d)
    return d, 'bokfört: %d sessioner (%d av %d för %s)' % (antal, forbrukat + antal, TAK_SESSIONER, manad)


def _veckonummer(dt):
    y, w, _ = dt.isocalendar()
    return '%04d-W%02d' % (y, w)


def besked(kund, vecka=None):
    """Ägarens korta veckobesked: gjorda faktarättelser, förslag som väntar, förbrukning mot taket,
    driftkontrollens senaste kvitto och en utebliven vecka redovisad."""
    d = las(kund)
    nu_dt = datetime.now(timezone.utc)
    vecka = vecka or _veckonummer(nu_dt)
    if not re.fullmatch(r'\d{4}-W\d{2}', vecka):
        raise Vagrad('--vecka ska vara ÅÅÅÅ-Www')
    manad = nu()[:7]
    forbrukat = sum(x['antal'] for x in d['sessioner'] if x['tid'][:7] == manad)
    gjorda = [p for p in d['poster'] if p['klass'] == 'faktarattelse']
    vantar = [p for p in d['poster'] if p['klass'] == 'forslag'
              and (p.get('atgard') or {}).get('agarens_svar') in (None,)]
    kvitto, kvitto_tid, okanda = _senaste_driftkvitto(kund, med_okanda=True)
    rader = ['# Veckobesked — %s, %s' % (d['kund'], vecka), '',
             'Underhållsform: DIGITALA-UNDERHALL-20260929. Ärendet hålls öppet efter leveransen.', '']
    rader += ['## Faktarättelser Digitala gjort', '']
    rader += (['- %s: "%s" (%s)' % (p['nyckel'], str(p['varde'])[:120], p['skal']) for p in gjorda] or ['- inga'])
    rader += ['', '## Förslag som väntar på ditt ja eller nej', '']
    for p in vantar:
        a = p.get('atgard') or {}
        rader.append('- %s: "%s" — %s' % (p['nyckel'], str(p['varde'])[:120],
                     ('omfattning: %s, uppskattat %d sessioner' % (a['omfattning'], a['uppskattade_sessioner']))
                     if a else 'förslag inte skrivet än (%s)' % p['skal']))
    if not vantar:
        rader.append('- inga')
    instruktionslika = [p for p in d['poster'] if p.get('instruktionslik')]
    if instruktionslika:
        rader += ['', '## Kundtext som såg ut som en instruktion (behandlad som underlag, inget utfört)', '']
        rader += ['- %s: "%s"' % (p['nyckel'], str(p['varde'])[:160]) for p in instruktionslika]
    rader += ['', '## Förbrukning', '',
              '- %d av %d läsande modellsessioner för %s' % (forbrukat, TAK_SESSIONER, manad),
              '', '## Driftkontroll', '']
    rader.append('- senaste kvitto: %s' % (kvitto_tid or 'inget kvitto funnet i kundmappen'))
    if kvitto is not None:
        rader.append('- incidenter: %s' % (', '.join(kvitto) if kvitto else 'inga'))
    if okanda:
        rader += ['', '## Okända driftlägen', ''] + ['- ' + rad for rad in okanda]
    if kvitto_tid:
        alder = (nu_dt - datetime.strptime(kvitto_tid[:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc)).days
        if alder > 7:
            rader.append('- UTEBLIVEN VECKA: kvittot är %d dagar gammalt; veckokontrollen har inte körts' % alder)
    else:
        rader.append('- UTEBLIVEN VECKA: ingen körning bokförd. Den schemalagda körningen är ett eget Runtime-uppdrag.')
    if d.get('lank_utgar'):
        dagar = (datetime.strptime(d['lank_utgar'], '%Y-%m-%d').replace(tzinfo=timezone.utc) - nu_dt).days
        rader += ['', '## Kundens länk', '',
                  '- gäller till %s (%d dagar kvar)%s' % (d['lank_utgar'], dagar,
                  '; ge en ny länk med kundstart.py lank' if dagar <= 7 else '')]
    text = '\n'.join(rader) + '\n'
    d['besked'].append({'vecka': vecka, 'skrivet': nu(), 'gjorda': len(gjorda), 'vantar': len(vantar),
                        'sessioner_manad': forbrukat})
    spara(kund, d)
    return d, text


def _senaste_driftkvitto(kund, med_okanda=False):
    """Driftkontrollens senaste kvitto i kundmappen, om något finns. Läsning, ingen körning.

    Kvittot skrivs av drift_kontroll.py som DRIFT-<tid>.json: 'tid', 'sajter' (rad per sajt med 'incident' och
    'fynd') och 'incidenter' som antal. Namnet bär komprimerad ISO-tid och sorterar därför kronologiskt.
    """
    kvitton = sorted(Path(kund).glob('**/DRIFT-*.json'))
    if not kvitton:
        return (None, None, []) if med_okanda else (None, None)
    try:
        k = json.loads(kvitton[-1].read_text(encoding='utf-8'))
    except (ValueError, OSError):
        return (None, None, []) if med_okanda else (None, None)
    inc = ['%s: %s' % (str(r.get('adress')), '; '.join(str(x) for x in (r.get('fynd') or [])) or 'incident')
           for r in (k.get('sajter') or []) if r.get('incident')]
    tid = str(k.get('tid') or '')[:20] or None
    if med_okanda:
        okanda = ['%s: %s' % (r.get('adress'), x) for r in k.get('sajter', []) for x in r.get('okanda', [])]
        return inc, tid, okanda
    return inc, tid


def status(kund):
    d = las(kund)
    manad = nu()[:7]
    forbrukat = sum(x['antal'] for x in d['sessioner'] if x['tid'][:7] == manad)
    return d, ('öppet: %s | poster: %d (%d faktarättelser, %d förslag) | sessioner %s: %d av %d'
               % (d.get('oppet_efter_leverans'), len(d['poster']),
                  sum(1 for p in d['poster'] if p['klass'] == 'faktarattelse'),
                  sum(1 for p in d['poster'] if p['klass'] == 'forslag'), manad, forbrukat, TAK_SESSIONER))


def main(argv=None):
    p = argparse.ArgumentParser(description='Underhåll av en levererad sajt enligt DIGITALA-UNDERHALL-20260929')
    p.add_argument('kommando', choices=('oppna', 'las', 'forslag', 'sessioner', 'besked', 'status', 'kontrollera'))
    p.add_argument('--kund', required=True)
    p.add_argument('--bestallning')
    p.add_argument('--lank-utgar')
    p.add_argument('--utforare')
    p.add_argument('--post')
    p.add_argument('--omfattning')
    p.add_argument('--sessioner', type=int)
    p.add_argument('--antal', type=int)
    p.add_argument('--andamal')
    p.add_argument('--vecka')
    p.add_argument('--ut')
    p.add_argument('--repo')
    p.add_argument('--bas')
    p.add_argument('--kandidat')
    a = p.parse_args(argv)
    try:
        if a.kommando == 'kontrollera':
            result = kontrollera(a.kund, a.post, a.repo, a.bas, a.kandidat)
            text = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
            if a.ut:
                ks.privat_skriv(Path(a.ut), text)
            else:
                print(text, end='')
            return 0 if result['godkand'] else 1
        elif a.kommando == 'oppna':
            _, msg = oppna(a.kund, a.bestallning, a.lank_utgar)
            print(msg)
        elif a.kommando == 'las':
            _, nya = las_poster(a.kund, a.utforare)
            print('%d nya poster' % len(nya))
            for x in nya:
                print(' %-14s %-16s %s' % (x['klass'], x['nyckel'], x['skal']))
        elif a.kommando == 'forslag':
            _, post = forslag(a.kund, a.post, a.omfattning, a.sessioner or 0)
            print('förslag skrivet för %s (%d sessioner)' % (post['id'], post['atgard']['uppskattade_sessioner']))
        elif a.kommando == 'sessioner':
            _, msg = sessioner(a.kund, a.antal or 0, a.andamal, a.bestallning)
            print(msg)
        elif a.kommando == 'besked':
            _, text = besked(a.kund, a.vecka)
            if a.ut:
                ks.privat_skriv(Path(a.ut), text); print('veckobesked skrivet: %s' % a.ut)
            else:
                sys.stdout.write(text)
        else:
            _, msg = status(a.kund)
            print(msg)
    except (Vagrad, ks.Vagrad, iv.Vagrad) as e:
        print('VÄGRAD: %s' % e.args[0], file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
