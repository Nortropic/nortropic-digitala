#!/usr/bin/env python3
"""Kundintervju: en adaptiv, återupptagbar intervjuväg i den kontaktkanal beställningen anger (ägarens tillägg 2,
2026-09-27). Verktyget läser kundmappens befintliga underlag (VERKSAMHET.json, tidigare INTERVJU.json) före frågor,
bygger frågeomgångar per område A–H ur de luckor som påverkar lösningen, härleder följdfrågor ur svaren med
namngivna regler (inte en fast enkät), bevarar kundens svar ordagrant skilda från tolkningen, registrerar fakta med
status (kunden uppger · observerat · externt belagt · tolkning · hypotes · preferens · okänt), gör motsägelser spårbara
och skriver intervjuavsnittet till research.md. Allt tillstånd ligger i kundmappen (INTERVJU.json, INTERVJU/), aldrig i
detta repo; en färsk utförare fortsätter med `status` och `nasta`. Verktyget skickar inget: omgången skrivs som en
läsbar fil som sessionen skickar genom kundens tillåtna kanal, och svaren registreras som text.

    python3 -B verktyg/intervju.py start   --kund DIR --kanal "e-post till kontaktpersonen enligt beställningen" [--testdialog]
    python3 -B verktyg/intervju.py svar    --kund DIR --omgang N --fil SVAR.md      # ### <fråge-id> följt av kundens svar ordagrant
    python3 -B verktyg/intervju.py fakta   --kund DIR --fil FAKTA.json             # utförarens tolkning: [{nyckel, varde, status, kalla, omrade}]
    python3 -B verktyg/intervju.py nasta   --kund DIR                               # nästa omgång ur följdfrågor och kvarvarande luckor
    python3 -B verktyg/intervju.py status  --kund DIR
    python3 -B verktyg/intervju.py research --kund DIR --ut research-intervju.md   # avsnitt 19 till research.md

En intervju med företagets representant är inte ett användartest; en testdialog (--testdialog) märks i varje utdata och
är aldrig kundresearch. Inga lösenord eller nycklar efterfrågas; svar som ser ut som hemligheter vägras.
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

STATUSAR = ('kunden uppger', 'observerat', 'externt belagt', 'tolkning', 'hypotes', 'preferens', 'okänt')
OMRADEN = {'A': 'Verksamhet, mål och erbjudande', 'B': 'Besökare och faktiska situationer', 'C': 'Hela verksamhetsflödet', 'D': 'Befintliga system och åtkomster',
           'E': 'Varumärke, innehåll och förtroende', 'F': 'Synlighet och mätning', 'G': 'Förvaltning och redaktörsarbete', 'H': 'Ramar och osäkerheter'}
PER_OMGANG = 8
HEMLIGT = re.compile(r'(l[öo]senord|password|api[- ]?nyckel|api key|secret|token)\s*[:=]\s*\S{4,}|\b(sk_live|re_|AKIA|ghp_)[A-Za-z0-9]{8,}', re.I)

# Grundfrågor: id · område · nyckel (faktanyckel som svaret fyller) · text · vad svaret påverkar · prioritet 1–3
GRUND = [
    ('A1', 'A', 'verksamhetsmal', 'Vad vill ni att webbplatsen ska förändra för verksamheten det närmaste året? Ge gärna ett konkret exempel på ett bra utfall.', 'verksamhetsmål och framgångskriterier (brief §1, §11)', 1),
    ('A2', 'A', 'erbjudande', 'Vilka tjänster eller produkter erbjuder ni, till vem, och med vilka verkliga villkor (område, tider, priser eller prisprincip, minsta uppdrag)?', 'erbjudande, sidor och innehåll (brief §1, §3)', 1),
    ('A3', 'A', 'nulage', 'Vad fungerar bra och vad fungerar dåligt i dag när kunder hittar er, kontaktar er eller köper?', 'interventionsbeslut och prioritering (beredning)', 1),
    ('A4', 'A', 'undvik', 'Vilka förfrågningar eller uppdrag vill ni helst slippa?', 'innehåll som styr bort fel förfrågningar (brief §4, §6)', 2),
    ('B1', 'B', 'besokare', 'Vilka är det som faktiskt hör av sig? Beskriv de två eller tre vanligaste typerna av kunder och situationer.', 'målgrupper och uppgifter (brief §2)', 1),
    ('B2', 'B', 'senaste_forfragan', 'Beskriv den senaste förfrågan eller bokningen ni fick: vad ville personen, hur kom den in, och vad hände sedan?', 'viktigaste uppgiften och handlingskedjan (brief §2, §4)', 1),
    ('B3', 'B', 'fore_handling', 'Vad behöver en ny kund förstå eller veta innan hen vågar kontakta er, boka eller köpa?', 'innehållsstruktur och första vyn (brief §3)', 2),
    ('B4', 'B', 'insiktskalla', 'Vad av det ni sagt om kunderna har ni sett (statistik, samtal, frågor), och vad är er känsla?', 'insiktskälla: observerat eller antaganden (beredning)', 2),
    ('C1', 'C', 'efter_inskick', 'När någon skickar ett formulär, bokar eller ringer: vem tar emot, i vilket system, och vad händer den första timmen och den första dagen?', 'formulärets och bokningens efterled, mottagande system (integrationer.md)', 1),
    ('C2', 'C', 'fordelning', 'Hur fördelas inkommande ärenden mellan er, och vad händer när den som brukar ta emot är borta?', 'mottagare, reservväg, sant besked till kunden (integrationer.md)', 2),
    ('C3', 'C', 'felvag', 'Vad händer i dag när något går fel: dubbelbokning, obesvarat mejl, fel uppgifter?', 'felvägar och dubbletthantering (integrationer.md)', 2),
    ('D1', 'D', 'system', 'Vilka system använder ni i dag: mejl, kalender, bokning, kassa eller betalning, kundregister, nyhetsbrev, hemsideverktyg, analys- eller annonskonton? Vilka ska vara kvar?', 'integrationer och redigeringsväg (brief §9)', 1),
    ('D2', 'D', 'kontoagare', 'Vem äger kontona (domän, webbhotell, Google, sociala medier) och kan ge åtkomst när det behövs? Skicka inga lösenord i svaret; åtkomst ordnas på säker väg.', 'åtkomstberoenden (brief §9, lansering)', 1),
    ('E1', 'E', 'ton', 'Hur vill ni uppfattas? Tre ord, och gärna ett exempel på en text eller ett sätt att skriva som känns rätt.', 'röst och positionering (brief §6, §7)', 2),
    ('E2', 'E', 'material', 'Vilka texter, bilder, logotyper, omdömen, certifikat och meriter finns, och vad får vi använda och visa?', 'innehåll, bild och förtroende med rättigheter (brief §6, §8)', 1),
    ('E3', 'E', 'referenser', 'Finns det webbplatser ni gillar eller ogillar? Vad är det ni gillar eller ogillar med dem?', 'preferenser skilda från fakta (research §13)', 3),
    ('F1', 'F', 'hittar', 'Hur hittar folk er i dag: rekommendation, sökning, sociala medier, skyltar, annonser? Vilka ord tror ni att de söker på?', 'kanalbehov och sökintention (brief §5)', 1),
    ('F2', 'F', 'data', 'Finns statistik från en Google-företagsprofil, en tidigare hemsida eller annonskonton som vi får titta på?', 'befintligt underlag och mätning (beredning, uppföljning)', 2),
    ('F3', 'F', 'bra_forfragan', 'Vad räknas som en bra förfrågan för er, och hur vet ni efteråt om den blev ett uppdrag?', 'konverteringsdefinition och affärsmått (uppfoljning.md)', 1),
    ('G1', 'G', 'redaktor', 'Vem ska uppdatera innehållet när sajten är igång, hur ofta, och hur van är den personen vid sådana verktyg?', 'redigeringsväg och innehållsmodell (integrationer.md, brief §9)', 2),
    ('G2', 'G', 'hantering', 'Vem tar hand om förfrågningar, bokningar, driftproblem och åtkomster när sajten är igång?', 'drift och ansvar (drift.md)', 2),
    ('G3', 'G', 'migrering', 'Finns en befintlig hemsida med adresser, texter eller annat innehåll som måste bevaras eller flyttas?', 'migrering och omdirigeringar (seo.md, lansering.md)', 1),
    ('H1', 'H', 'ramar', 'Vilka ramar gäller: budget, tidpunkt, vad som måste vara publicerat, integritetskrav, verksamhetsgränser?', 'proportion och mandatgränser (beredning)', 1),
    ('H2', 'H', 'okant', 'Vad vet ni inte själva just nu, och vem skulle kunna svara?', 'luckor och vem som avgör (research §17)', 2),
]

# Följdregler: (namn, regex på svarets text, frågor som läggs till, vad de påverkar)
NEGATION = re.compile(r'(?i)\b(inga|ingen|inget|inte|ej|aldrig|utan|slipper)\b')

FOLJDREGLER = [
    ('bokning', re.compile(r'\bbok(a|ad|ade|at|ar|as|ning|ningar|ningen)\b|tidsbokning|boka tid|\bkalender\b', re.I), [
        ('BOK1', 'C', 'bokning_tjanster', 'Vilka tjänster ska kunna bokas, hur långa är de, och behövs olika längder eller resurser (person, rum, utrustning)?'),
        ('BOK2', 'C', 'bokning_tillganglighet', 'Vilka tider är bokningsbara, hur många kan bokas samtidigt, och behövs buffertar mellan bokningar?'),
        ('BOK3', 'C', 'bokning_bekraftelse', 'Hur ska kunden få bekräftelse, och hur ska ombokning och avbokning gå till (regler, tidsgräns)?'),
        ('BOK4', 'D', 'bokning_system', 'Använder ni redan ett bokningssystem eller en kalender? Vilket, och ska det vara kvar?'),
    ], 'bokningsintegrationens nivå och leveranskrav: länk, inbäddning, kalenderhändelse eller verifierad bokning (integrationer.md)'),
    ('betalning', re.compile(r'betal|kassa|swish|faktur|kortbetal', re.I), [
        ('BET1', 'C', 'betalning_vad', 'Vad ska kunna betalas på webbplatsen, och vad faktureras i efterhand?'),
        ('BET2', 'D', 'betalning_system', 'Vilken betal- eller kassalösning använder ni i dag, och vem äger det avtalet?'),
    ], 'betalningsintegration, villkor och juridikflagga e-handel (integrationer.md, juridikflaggor.md)'),
    ('crm', re.compile(r'\bcrm\b|kundregister|hubspot|pipedrive|fortnox|visma|lime', re.I), [
        ('CRM1', 'D', 'crm_falt', 'Vilka uppgifter om en förfrågan ska hamna i kundregistret, och vem ska se dem?'),
        ('CRM2', 'D', 'crm_agare', 'Vem administrerar kundregistret och kan ge en begränsad åtkomst för koppling (inga lösenord i svaret)?'),
    ], 'datamappning och rättigheter för CRM-koppling (integrationer.md)'),
    ('nyhetsbrev', re.compile(r'nyhetsbrev|mailchimp|utskick', re.I), [
        ('NYH1', 'D', 'nyhetsbrev', 'Hur hanteras nyhetsbrevet i dag (verktyg, lista, samtycke), och ska webbplatsen samla prenumeranter?'),
    ], 'samtyckesläge och integration för nyhetsbrev (uppfoljning.md)'),
    ('sprak', re.compile(r'engelsk|flerspråk|finsk|norsk|dansk|arabisk|språk', re.I), [
        ('SPR1', 'A', 'sprak', 'Vilka språk behöver webbplatsen ha, och finns översatt innehåll eller någon som kan översätta?'),
    ], 'språkvarianter, hreflang och innehållsmängd (seo.md)'),
    ('migrering', re.compile(r'gammal|befintlig(a)?\s+(hemsida|sajt|webbplats)|nuvarande (hemsida|sajt)|flytta', re.I), [
        ('MIG1', 'G', 'migrering_adresser', 'Vilka sidor eller adresser på den befintliga webbplatsen får besökare eller länkar i dag och måste behållas?'),
        ('MIG2', 'G', 'migrering_innehall', 'Vilket innehåll (texter, bilder, dokument) ska följa med, och vad ska bort?'),
        ('MIG3', 'D', 'migrering_vard', 'Var ligger den befintliga webbplatsen (leverantör, verktyg), och vem har åtkomst till domänen?'),
    ], 'omdirigeringar, innehållsflytt och lansering (seo.md, lansering.md)'),
    ('okant', re.compile(r'vet inte|vet ej|osäker|ingen aning|inte säker', re.I), [
        ('OK1', 'H', 'okant_vem', 'Ni skrev att ni inte vet det säkert. Vem skulle kunna svara, och hur påverkas arbetet om vi inte får veta?'),
    ], 'luckans ägare och påverkan (research §17)'),
    ('rackvidd', re.compile(r'hela landet|nationellt|riks|flera orter|hela sverige|utomlands', re.I), [
        ('RACK1', 'A', 'rackvidd', 'Vilka orter eller områden arbetar ni faktiskt i, och finns någon ort som är viktigare än andra?'),
    ], 'räckvidd och lokal synlighet (research §5, lokal-synlighet.md)'),
    ('besok', re.compile(r'butik|besök(a|er)? oss|showroom|lokal(en)?\b|mottagning|kontor(et)?\b', re.I), [
        ('BES1', 'C', 'besok', 'Ska kunder kunna besöka er? Vilka tider, hur hittar man, och vad ska vara klart före ett besök?'),
    ], 'fysiskt besök som handling, öppettider och vägbeskrivning (brief §4)'),
]


class Vagrad(Exception):
    pass


def nu():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def stig(kund):
    return Path(kund) / 'INTERVJU.json'


def las(kund):
    p = stig(kund)
    if not p.is_file():
        raise Vagrad('ingen intervju startad i %s (kör start)' % kund)
    return json.loads(p.read_text(encoding='utf-8'))


def spara(kund, s):
    s['uppdaterad'] = nu()
    stig(kund).write_text(json.dumps(s, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


def kanda_nycklar(s):
    return {f['nyckel'] for f in s['fakta'] if f['status'] != 'okänt'} | {sv['nyckel'] for sv in s['svar']}


def fro_verksamhet(kund):
    """Fakta som redan finns i VERKSAMHET.json (kundens uppgifter med belägg) — frågas inte om igen."""
    p = Path(kund) / 'VERKSAMHET.json'
    if not p.is_file():
        return []
    try:
        v = json.loads(p.read_text(encoding='utf-8'))
    except ValueError:
        return []
    import datetime
    datum = datetime.datetime.fromtimestamp(p.stat().st_mtime, datetime.timezone.utc).strftime('%Y-%m-%d')
    fakta = []
    if v.get('tjanster'):
        fakta.append({'nyckel': 'erbjudande', 'varde': ', '.join(v['tjanster']), 'status': 'kunden uppger', 'kalla': 'VERKSAMHET.json tjanster', 'omrade': 'A', 'datum': datum, 'not': 'status kunden uppger om inte belägget säger annat; datum = filens ändringstid'})
    if v.get('kontaktvagar'):
        fakta.append({'nyckel': 'kontaktvagar', 'varde': '; '.join('%s: %s' % (k.get('typ'), k.get('varde')) for k in v['kontaktvagar']), 'status': 'kunden uppger', 'kalla': 'VERKSAMHET.json kontaktvagar (belägg per rad)', 'omrade': 'D', 'datum': datum})
    if v.get('rackvidd'):
        fakta.append({'nyckel': 'rackvidd', 'varde': '%s: %s' % (v['rackvidd'].get('typ'), ', '.join(v['rackvidd'].get('orter') or [])), 'status': 'kunden uppger', 'kalla': 'VERKSAMHET.json rackvidd', 'omrade': 'A', 'datum': datum})
    if v.get('oppettider'):
        fakta.append({'nyckel': 'oppettider', 'varde': json.dumps(v['oppettider'], ensure_ascii=False), 'status': 'kunden uppger', 'kalla': 'VERKSAMHET.json oppettider', 'omrade': 'C', 'datum': datum})
    return fakta


def stalld_utan_svar(s, fid):
    """Omgångar där frågan ställts utan att svar registrerats (kundens uteblivna svar döljs aldrig)."""
    return [o['nr'] for o in s['omgangar'] for q in o['fragor'] if q['id'] == fid and q['status'] != 'besvarad']


def luckor(s):
    """Grundfrågor vars nyckel varken är besvarad eller känd, i prioritetsordning; en ställd men obesvarad fråga är
    fortfarande en lucka och ställs igen, märkt med omgångarna den ställts i."""
    kanda = kanda_nycklar(s)
    ut = []
    for g in sorted(GRUND, key=lambda g: (g[5], g[0])):
        if g[2] in kanda:
            continue
        ut.append(g + (stalld_utan_svar(s, g[0]),))
    return ut


def ny_omgang(s, fragor, skal):
    nr = len(s['omgangar']) + 1
    o = {'nr': nr, 'skapad': nu(), 'skal': skal, 'fragor': [{'id': q['id'], 'omrade': q['omrade'], 'nyckel': q['nyckel'], 'text': q['text'], 'paverkar': q['paverkar'], 'utlost_av': q.get('utlost_av'), 'status': 'stalld'} for q in fragor], 'svar_mottagna': None}
    s['omgangar'].append(o)
    return o


def omgang_md(s, o):
    lines = ['# Frågor till %s — omgång %d%s' % (s['kund'], o['nr'], ' — TESTDIALOG (inte kundresearch)' if s.get('testdialog') else ''), '',
             'Kanal: %s. Svara gärna kort och i era egna ord; det går bra att svara "vet inte". Skicka inga lösenord eller nycklar — åtkomst ordnar vi på säker väg.' % s['kanal'], '']
    aktuell = None
    for q in o['fragor']:
        if q['omrade'] != aktuell:
            aktuell = q['omrade']; lines += ['## %s. %s' % (aktuell, OMRADEN[aktuell]), '']
        lines += ['### %s' % q['id'], q['text'], '']
    lines += ['---', 'Varför vi frågar: ' + '; '.join('%s → %s' % (q['id'], q['paverkar']) for q in o['fragor'])]
    return '\n'.join(lines) + '\n'


def start(kund, kanal, testdialog=False, om=False):
    p = stig(kund)
    if p.is_file() and not om:
        s = las(kund)
        return s, 'intervju finns redan (%d omgångar, %d svar); fortsätt med status/nasta' % (len(s['omgangar']), len(s['svar']))
    s = {'schema': 1, 'kund': Path(kund).name, 'kanal': kanal, 'testdialog': bool(testdialog), 'startad': nu(), 'omgangar': [], 'svar': [], 'fakta': fro_verksamhet(kund), 'motsagelser': [], 'foljdregler_utlosta': []}
    fragor = [{'id': g[0], 'omrade': g[1], 'nyckel': g[2], 'text': g[3], 'paverkar': g[4]} for g in luckor(s)][:PER_OMGANG]
    o = ny_omgang(s, fragor, 'första omgången: luckor med högst prioritet efter läsning av kundmappen (%d kända fakta ur VERKSAMHET.json)' % len(s['fakta']))
    (Path(kund) / 'INTERVJU').mkdir(exist_ok=True)
    (Path(kund) / 'INTERVJU' / ('omgang-%d.md' % o['nr'])).write_text(omgang_md(s, o), encoding='utf-8')
    spara(kund, s)
    return s, 'omgång 1 skriven: %d frågor' % len(fragor)


def tolka_svarsfil(text):
    """### <id> följt av kundens svar ordagrant, till nästa ###."""
    delar = re.split(r'(?m)^###\s+([A-Z]+\d+)\s*$', text)
    ut = {}
    for i in range(1, len(delar) - 1, 2):
        ut[delar[i]] = delar[i + 1].strip()
    return ut


def svar(kund, omgang, fil):
    s = las(kund)
    o = next((x for x in s['omgangar'] if x['nr'] == omgang), None)
    if not o:
        raise Vagrad('omgång %d finns inte' % omgang)
    text = Path(fil).read_text(encoding='utf-8')
    svaren = tolka_svarsfil(text) if fil.endswith('.md') else {x['id']: x['text'] for x in json.loads(text)}
    if not svaren:
        raise Vagrad('inga svar hittades (### <fråge-id> följt av svaret)')
    nya = 0; foljd = []; okanda = []
    alla_fragor = {q['id']: (q, oo) for oo in s['omgangar'] for q in oo['fragor']}
    for fid in svaren:
        if fid not in alla_fragor:
            okanda.append(fid)
    for fid, (q, oo) in alla_fragor.items():
        if fid in svaren and svaren[fid] and q['status'] != 'besvarad':
            t = svaren[q['id']]
            if HEMLIGT.search(t):
                raise Vagrad('svaret på %s ser ut att innehålla ett lösenord eller en nyckel; vägras och sparas inte — be kunden ta bort det och använd säker åtkomstväg' % q['id'])
            s['svar'].append({'fraga_id': q['id'], 'omgang': oo['nr'], 'svarsfil_omgang': omgang, 'nyckel': q['nyckel'], 'omrade': q['omrade'], 'text': t, 'mottaget': nu(), 'status': 'kunden uppger'})
            for oo2 in s['omgangar']:
                for q2 in oo2['fragor']:
                    if q2['id'] == fid:
                        q2['status'] = 'besvarad'
            nya += 1
            for namn, rx, fragor, paverkar in FOLJDREGLER:
                m = rx.search(t)
                if m:
                    # negationsspärr (iakttagelse ur Kundstarts prov): "Inga bokningar via nätet, folk ringer" ska inte utlösa
                    # bokningsfrågorna automatiskt; träffen bokförs som negerad så att utföraren avgör i fakta
                    sats = re.split(r'[.;!?]', t[max(0, m.start() - 40):m.start()])[-1]
                    if NEGATION.search(sats):
                        s.setdefault('foljdregler_negerade', [])
                        if not any(n['regel'] == namn and n['fraga_id'] == q['id'] for n in s['foljdregler_negerade']):
                            s['foljdregler_negerade'].append({'regel': namn, 'fraga_id': q['id'], 'traff': m.group(0), 'sats': (sats + m.group(0)).strip()[-80:], 'tid': nu(), 'not': 'nämnd med negation: ingen följdfråga automatiskt; avgör i fakta om behovet finns i annan form'})
                        continue
                if m and not any(u['regel'] == namn and u['fraga_id'] == q['id'] for u in s['foljdregler_utlosta']):
                    s['foljdregler_utlosta'].append({'regel': namn, 'fraga_id': q['id'], 'traff': m.group(0), 'paverkar': paverkar, 'tid': nu()})
                    for fid, omr, nyckel, ftext in fragor:
                        foljd.append({'id': fid, 'omrade': omr, 'nyckel': nyckel, 'text': ftext, 'paverkar': paverkar, 'utlost_av': '%s: "%s"' % (q['id'], m.group(0))})
    o['svar_mottagna'] = nu()
    s['vantande_foljdfragor'] = s.get('vantande_foljdfragor', [])
    kanda_id = {q['id'] for oo in s['omgangar'] for q in oo['fragor']} | {f['id'] for f in s['vantande_foljdfragor']}
    for f in foljd:
        if f['id'] not in kanda_id:
            s['vantande_foljdfragor'].append(f); kanda_id.add(f['id'])
    spara(kund, s)
    s.setdefault('okanda_svar', []).extend({'omgang': omgang, 'fraga_id': fid, 'tid': nu()} for fid in okanda)
    spara(kund, s)
    return s, 'omgång %d: %d svar registrerade ordagrant; %d följdfrågor väntar (regler: %s)%s' % (omgang, nya, len(s['vantande_foljdfragor']), ', '.join(sorted({u['regel'] for u in s['foljdregler_utlosta']})) or 'inga', ('; VARNING: okända fråge-id ignorerade: ' + ', '.join(okanda)) if okanda else '')


def fakta(kund, fil):
    """Utförarens tolkning av svaren som fakta med status; motsägelse mot befintlig uppgift registreras och ger följdfråga."""
    s = las(kund)
    rader = json.loads(Path(fil).read_text(encoding='utf-8'))
    if not isinstance(rader, list):
        raise Vagrad('FAKTA.json ska vara en lista')
    nya = 0
    for r in rader:
        for f in ('nyckel', 'varde', 'status', 'kalla', 'omrade'):
            if f not in r:
                raise Vagrad('faktarad saknar ' + f)
        if r['status'] not in STATUSAR:
            raise Vagrad('status ska vara en av ' + ', '.join(STATUSAR))
        if r['omrade'] not in OMRADEN:
            raise Vagrad('omrade ska vara A–H')
        if HEMLIGT.search(str(r['varde'])):
            raise Vagrad('faktaraden %s ser ut att innehålla ett lösenord eller en nyckel; vägras' % r['nyckel'])
        r.setdefault('datum', nu()[:10])
        bef = next((f for f in s['fakta'] if f['nyckel'] == r['nyckel'] and f.get('varde') != r['varde'] and not f.get('ersatt')), None)
        if bef:
            mid = 'MOT%d' % (len(s['motsagelser']) + 1)
            s['motsagelser'].append({'id': mid, 'nyckel': r['nyckel'], 'uppgift_1': {'varde': bef['varde'], 'status': bef['status'], 'kalla': bef['kalla'], 'datum': bef.get('datum')}, 'uppgift_2': {'varde': r['varde'], 'status': r['status'], 'kalla': r['kalla'], 'datum': r['datum']}, 'lage': 'oavgjord', 'tid': nu()})
            r['motsagelse'] = mid; bef['motsagelse'] = mid
            s.setdefault('vantande_foljdfragor', []).append({'id': mid, 'omrade': r['omrade'], 'nyckel': r['nyckel'], 'text': 'Vi har två uppgifter om %s: "%s" (%s) och "%s" (%s). Vilken gäller, och från när?' % (r['nyckel'], bef['varde'], bef['kalla'], r['varde'], r['kalla']), 'paverkar': 'alla delar som bygger på ' + r['nyckel'] + ' (brief, innehåll, strukturerad data, prov)', 'utlost_av': 'motsägelse ' + mid})
        s['fakta'].append(r); nya += 1
    spara(kund, s)
    return s, '%d fakta registrerade; %d motsägelser oavgjorda' % (nya, sum(1 for m in s['motsagelser'] if m['lage'] == 'oavgjord'))


def avgor(kund, mid, galler, skal):
    s = las(kund)
    m = next((x for x in s['motsagelser'] if x['id'] == mid), None)
    if not m:
        raise Vagrad('motsägelsen finns inte')
    m['lage'] = 'avgjord'; m['galler'] = galler; m['skal'] = skal; m['avgjord'] = nu()
    s['vantande_foljdfragor'] = [f for f in s.get('vantande_foljdfragor', []) if f['id'] != mid]
    for f in s['fakta']:
        if f.get('motsagelse') == mid:
            f['ersatt'] = f['varde'] != galler
    spara(kund, s)
    return s, 'motsägelsen %s avgjord: %s' % (mid, galler)


def nasta(kund):
    s = las(kund)
    oppna = [o for o in s['omgangar'] if o['svar_mottagna'] is None]
    if oppna:
        return s, 'omgång %d väntar på svar; registrera dem med svar innan nästa omgång' % oppna[0]['nr']
    vantande = s.get('vantande_foljdfragor', [])
    grund = [{'id': g[0], 'omrade': g[1], 'nyckel': g[2], 'text': (('(ställdes i omgång %s utan svar) ' % ', '.join(map(str, g[6]))) if g[6] else '') + g[3], 'paverkar': g[4]} for g in luckor(s)]
    fragor = (vantande + grund)[:PER_OMGANG]
    if not fragor:
        return s, 'inga luckor som påverkar lösningen kvar; intervjun kan avslutas (research skriver avsnittet)'
    s['vantande_foljdfragor'] = vantande[len([f for f in fragor if f in vantande]):]
    o = ny_omgang(s, fragor, 'följdfrågor ur svaren (%d) och kvarvarande luckor (%d)' % (sum(1 for f in fragor if f.get('utlost_av')), sum(1 for f in fragor if not f.get('utlost_av'))))
    (Path(kund) / 'INTERVJU').mkdir(exist_ok=True)
    (Path(kund) / 'INTERVJU' / ('omgang-%d.md' % o['nr'])).write_text(omgang_md(s, o), encoding='utf-8')
    spara(kund, s)
    return s, 'omgång %d skriven: %d frågor (%d följdfrågor)' % (o['nr'], len(fragor), sum(1 for f in fragor if f.get('utlost_av')))


def status(s):
    return {'kund': s['kund'], 'testdialog': s.get('testdialog', False), 'kanal': s['kanal'], 'omgangar': len(s['omgangar']), 'svar': len(s['svar']), 'fakta': len(s['fakta']),
            'vantar_pa_svar': [o['nr'] for o in s['omgangar'] if o['svar_mottagna'] is None], 'foljdfragor_vantande': len(s.get('vantande_foljdfragor', [])),
            'luckor_kvar': [g[0] + ('(ställd utan svar i omgång %s)' % ','.join(map(str, g[6])) if g[6] else '') for g in luckor(s)], 'motsagelser_oavgjorda': [m['id'] for m in s['motsagelser'] if m['lage'] == 'oavgjord'], 'uppdaterad': s.get('uppdaterad')}


def anvandbarhet(s):
    """De fyra frågorna research.md ska kunna besvara; 'okänt' när underlaget saknas."""
    def hitta(*nycklar):
        for n in nycklar:
            f = [x for x in s['fakta'] if x['nyckel'] == n and not x.get('ersatt') and x['status'] != 'okänt']
            if f:
                return '%s (%s, %s)' % (f[-1]['varde'], f[-1]['status'], f[-1]['kalla'])
            sv = [x for x in s['svar'] if x['nyckel'] == n]
            if sv:
                return 'kunden uppger (svar %s): %s' % (sv[-1]['fraga_id'], sv[-1]['text'][:200])
        return 'okänt'
    return {'viktigaste uppgift': hitta('viktigaste_uppgift', 'senaste_forfragan', 'besokare'), 'vad formuläret ska åstadkomma efter inskick': hitta('efter_inskick', 'bokning_bekraftelse'),
            'vilket befintligt system som ska ta emot': hitta('mottagande_system', 'system', 'bokning_system', 'crm_falt'), 'vad vi ännu inte vet': ', '.join(g[2] for g in luckor(s)) or 'inga öppna grundluckor; se motsägelser'}


def research_md(s):
    m = ' — **TESTDIALOG: inte kundresearch, inte bevis för mänsklig användbarhet**' if s.get('testdialog') else ''
    lines = ['## 19. Intervju och status per uppgift%s' % m, '', 'Kanal: %s. Startad %s. Omgångar: %d. Svar: %d. Kundens svar återges ordagrant; tolkningar står som fakta med status.' % (s['kanal'], s['startad'][:10], len(s['omgangar']), len(s['svar'])), '']
    for omr, namn in OMRADEN.items():
        sv = [x for x in s['svar'] if x['omrade'] == omr]; fk = [x for x in s['fakta'] if x['omrade'] == omr and not x.get('ersatt')]
        lines += ['### %s. %s' % (omr, namn), '']
        if not sv and not fk:
            lines += ['- inte utrett', '']; continue
        for x in sv:
            lines += ['> **%s** (%s, %s): %s' % (x['fraga_id'], x['mottaget'][:10], x['status'], x['text'].replace('\n', ' ')), '']
        if fk:
            lines += ['| Uppgift | Värde | Status | Källa | Datum |', '|---|---|---|---|---|'] + ['| %s | %s | %s | %s | %s |' % (x['nyckel'], str(x['varde']).replace('|', '/'), x['status'] + (' — motsägelse ' + x['motsagelse'] if x.get('motsagelse') else ''), x['kalla'], x.get('datum', '')) for x in fk] + ['']
    lines += ['### Motsägelser', ''] + (['- %s (%s): "%s" (%s) mot "%s" (%s) — %s%s' % (mm['id'], mm['nyckel'], mm['uppgift_1']['varde'], mm['uppgift_1']['kalla'], mm['uppgift_2']['varde'], mm['uppgift_2']['kalla'], mm['lage'], (': gäller "%s" — %s' % (mm.get('galler'), mm.get('skal'))) if mm['lage'] == 'avgjord' else '') for mm in s['motsagelser']] or ['- inga']) + ['']
    lines += ['### Luckor som påverkar lösningen', ''] + (['- %s (%s%s): %s' % (g[2], g[0], (', ställd utan svar i omgång %s' % ','.join(map(str, g[6]))) if g[6] else '', g[4]) for g in luckor(s)] or ['- inga öppna grundfrågor']) + ['']
    if s.get('okanda_svar'):
        lines += ['- svar med okända fråge-id ignorerades: ' + ', '.join(x['fraga_id'] for x in s['okanda_svar']), '']
    lines += ['### Kan research.md besvara', ''] + ['- %s: %s' % (k, v) for k, v in anvandbarhet(s).items()] + ['']
    lines += ['### Följdregler som utlöstes', ''] + (['- %s ur %s ("%s") → %s' % (u['regel'], u['fraga_id'], u['traff'], u['paverkar']) for u in s['foljdregler_utlosta']] or ['- inga'])
    lines += ['', '### Regler nämnda med negation (ingen följdfråga automatiskt; avgör i fakta)', ''] + (['- %s ur %s: "%s"' % (n['regel'], n['fraga_id'], n['sats']) for n in s.get('foljdregler_negerade', [])] or ['- inga'])
    return '\n'.join(lines) + '\n'


def main(argv=None):
    p = argparse.ArgumentParser(prog='intervju', description=__doc__.split('\n\n')[0])
    p.add_argument('kommando', choices=('start', 'svar', 'fakta', 'nasta', 'status', 'research', 'avgor'))
    p.add_argument('--kund', required=True); p.add_argument('--kanal'); p.add_argument('--testdialog', action='store_true'); p.add_argument('--omgang', type=int); p.add_argument('--fil'); p.add_argument('--ut')
    p.add_argument('--motsagelse'); p.add_argument('--galler'); p.add_argument('--skal')
    a = p.parse_args(argv)
    try:
        if not Path(a.kund).is_dir():
            raise Vagrad('kundmappen finns inte: ' + a.kund)
        if a.kommando == 'start':
            s, msg = start(a.kund, a.kanal or 'kontaktvägen enligt beställningen', a.testdialog)
        elif a.kommando == 'svar':
            if not (a.omgang and a.fil):
                raise Vagrad('svar kräver --omgang och --fil')
            s, msg = svar(a.kund, a.omgang, a.fil)
        elif a.kommando == 'fakta':
            if not a.fil:
                raise Vagrad('fakta kräver --fil')
            s, msg = fakta(a.kund, a.fil)
        elif a.kommando == 'avgor':
            if not (a.motsagelse and a.galler and a.skal):
                raise Vagrad('avgor kräver --motsagelse --galler --skal')
            s, msg = avgor(a.kund, a.motsagelse, a.galler, a.skal)
        elif a.kommando == 'nasta':
            s, msg = nasta(a.kund)
        elif a.kommando == 'status':
            s, msg = las(a.kund), 'status'
        else:
            s = las(a.kund)
            if not a.ut:
                raise Vagrad('research kräver --ut')
            if Path(a.ut).resolve().is_relative_to(Path(__file__).resolve().parents[1]):
                raise Vagrad('research-avsnittet skrivs i kundmappen, aldrig i repot')
            Path(a.ut).write_text(research_md(s), encoding='utf-8'); msg = 'avsnitt 19 skrivet till ' + a.ut
    except Vagrad as e:
        td = False
        try:
            td = bool(las(a.kund).get('testdialog')) if Path(a.kund).is_dir() and stig(a.kund).is_file() else False
        except Vagrad:
            td = False
        print(json.dumps({'vagrad': e.args[0], 'testdialog': td}, ensure_ascii=False)); return 2
    print(json.dumps({'kommando': a.kommando, 'meddelande': msg, **status(s)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
