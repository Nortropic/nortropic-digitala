#!/usr/bin/env python3
"""Lokal synlighet (Google Business Profile och citationer): tillämplighet, behörig åtkomstväg, korrekta
verksamhetsuppgifter, kategorier, öppettider, serviceområde, bilder, länkar och uppföljning — som ett datablad ur
VERKSAMHET.json plus en konsistenskontroll mot sajtens strukturerade data. Skapar aldrig en profil: profilen skapas och
verifieras av en behörig människa i business.google.com (Business Profile API kräver godkänt projekt och kan inte
skapa nya profiler för engångsbruk); en fiktiv verksamhet får ingen profil, inga citationer och inga omdömesförfrågningar.

    python3 -B verktyg/lokal_synlighet.py datablad --verksamhet VERKSAMHET.json [--beskrivning FIL.txt] --ut LOKAL-SYNLIGHET.md
    python3 -B verktyg/lokal_synlighet.py kontrollera --verksamhet VERKSAMHET.json --bygge DIR --ut KONTROLL.json
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verksamhetsuppgifter as vu  # noqa: E402
import seo_kontroll as sk  # noqa: E402

KATALOGER = [('Google Företagsprofil', 'business.google.com', 'primär; skapas/anspråk av behörig människa'), ('hitta.se', 'hitta.se', 'anspråk på auto-genererad post; NAP, bilder, kategorier, öppettider, länk'),
             ('eniro.se', 'foretag.eniro.se', 'som hitta; matar proff.se'), ('Bing Places', 'bingplaces.com', 'import från Google-profilen'), ('Apple Business Connect', 'businessconnect.apple.com', 'Apple Maps'),
             ('reco.se', 'reco.se', 'bara om kunden vill arbeta med omdömen där'), ('allabolag/merinfo/proff/ratsit', '(auto)', 'verifiera adress, SNI-kod och webbadress efter ändring; skapa inte')]
DAG = {'man': 'Måndag', 'tis': 'Tisdag', 'ons': 'Onsdag', 'tor': 'Torsdag', 'fre': 'Fredag', 'lor': 'Lördag', 'son': 'Söndag'}


def tillamplighet(v):
    rv = v['rackvidd']['typ']
    fysisk = bool(v.get('adress')) or any(k['typ'] == 'plats' for k in v['kontaktvagar'])
    if v['fiktiv']:
        return 'förbjuden', 'fiktiv verksamhet: ingen verklig profil, inga citationer, inga omdömesförfrågningar'
    if rv in ('lokal', 'regional'):
        return 'tillämplig', 'lokal eller regional räckvidd' + (' med fysisk närvaro' if fysisk else ' som serviceområdesverksamhet (dold adress, serviceområden per ort)')
    return 'inte tillämplig', 'nationell eller gränsöverskridande räckvidd utan lokal förankring; lokala krav tvingas inte på icke-lokala uppdrag'


def datablad(v, beskrivning=None):
    n = vu.nap(v)
    status, skal = tillamplighet(v)
    lines = ['# Lokal synlighet — %s' % v['namn'], '', '**Tillämplighet:** %s — %s.' % (status, skal), '',
             '**Åtkomstväg:** profilen skapas, görs anspråk på och verifieras av en behörig människa (kundens Google-konto som primär ägare; kontoret som hanterare vid avtal). Verifiering (vykort, telefon, video) tar dagar till veckor: börja tidigt. Ingen API-skapad profil.', '']
    if v['fiktiv'] and v['rackvidd']['typ'] in ('lokal', 'regional'):
        lines += ['**LOKALT TESTUTKAST — får inte publiceras, användas för verklig profil, citation eller omdömesförfrågan.**', '', 'Följande är förberedda uppgifter för prov, inte aktivering eller verifierad extern integration.', '']
    elif status != 'tillämplig':
        lines += ['Inget datablad: se tillämpligheten ovan.']
        return '\n'.join(lines) + '\n'
    lines += ['## Verksamhetsuppgifter (exakt som på sajten och i alla kataloger)', '', '- Namn: %s (ingen nyckelordsstoppning i namnet: suspensionsrisk)' % v['namn'],
              '- Telefon: %s (visning) / %s (E.164); samma nummer som sajten, inget spårningsnummer' % (n['telefon_visning'] or 'saknas — får inte hittas på', n['telefon_e164'] or 'saknas'),
              '- Adress: %s' % (n['adress'] if n['adress_visas'] else 'DOLD (serviceområdesverksamhet) — ange serviceområden: ' + ', '.join(n['omrade'])),
              '- Serviceområde: ' + (', '.join(n['omrade']) or '(inget angivet)'), '- Webbplats: https://%s/ (länk med utm_source=google&utm_medium=organic&utm_campaign=gbp om mätverktyget läser UTM)' % ((v.get('webb') or {}).get('doman') or '<domän>'),
              '- Kategorier: primär = %s; sekundära bara genuint tillämpliga, aldrig aspirerande' % ((v.get('kategorier') or ['(ange primär kategori på svenska)'])[0]),
              '', '## Öppettider (samma som sajten; jour bara om bemannad)', '']
    lines += ['- %s: %s–%s' % (DAG[o['dag']], o['oppnar'], o['stanger']) for o in v.get('oppettider') or []] or ['- (inga angivna)']
    lines += ['', '## Tjänster', ''] + ['- ' + t for t in v.get('tjanster') or []]
    lines += ['', '## Beskrivning (högst 750 tecken; de första 250 bär budskapet; ur briefen, ingen nyckelordsstoppning)', '', (beskrivning or '(skrivs ur briefens §1 och §6)').strip()[:750],
              '', '## Bilder', '', '- logotyp, omslagsbild, personer, fordon/lokal, utfört arbete; verkliga foton med rättigheter (bild.md); genererade bilder aldrig som verkliga projekt eller personer',
              '', '## Citationer (samma NAP överallt; verifiera auto-poster, skapa inte)', '', '| Katalog | Adress | Not |', '|---|---|---|'] + ['| %s | %s | %s |' % k for k in KATALOGER]
    lines += ['', '## Omdömen', '', '- Direktlänk från profilen ("be om recensioner") till kunden för faktura, SMS eller QR; be i leveransögonblicket.', '- Svara på varje recension inom sju dagar; sakligt vid kritik; aldrig incitament eller urval (Googles policy och marknadsföringslagen).',
              '- Sajten visar riktigt aggregat och namngivna citat bara med tillstånd; betyg utan källa visas inte.',
              '', '## Uppföljning', '', '- Efter lansering: minst ett inlägg per månad; insikter (samtal, vägbeskrivningar, webbklick) månadsvis in i kunduppföljningen.', '- Kvartalsvis: sök företagsnamn + ort och telefonnumret i citattecken; rätta avvikande NAP vid källkatalogen.',
              '', '## Varningstecken', '', '- nyckelordsstoppat namn · virtuell kontorsadress · flera profiler för samma företag · kategoribyten fram och tillbaka · många recensioner samma dag']
    return '\n'.join(lines) + '\n'


def kontrollera(v, bygge):
    """NAP i sajtens JSON-LD mot verksamhetsuppgifterna (samma kontroll som seo_kontroll, samlad per sajt)."""
    root = Path(bygge)
    n = vu.nap(v); fynd = []; scheman = 0
    for f in sk.sidor(root):
        raw = f.read_text(encoding='utf-8', errors='replace')
        for block in sk.JSONLD.findall(raw):
            try:
                data = json.loads(block)
            except ValueError:
                continue
            for obj in (data if isinstance(data, list) else [data]):
                if isinstance(obj, dict) and (obj.get('address') or obj.get('telephone') or obj.get('@type') in ('LocalBusiness', 'Organization')):
                    scheman += 1
                    for t, x in sk.granska_schema(obj, v):
                        fynd.append({'sida': sk.url_for(root, f), 'typ': t, 'text': x})
                    tel_text = re.sub(r'<[^>]+>', ' ', raw)
                    if n['telefon_visning'] and re.sub(r'\D', '', n['telefon_visning']) not in re.sub(r'\D', '', tel_text):
                        fynd.append({'sida': sk.url_for(root, f), 'typ': 'telefonnumret saknas som synlig text', 'text': 'sidan bär schema men inte numret i läsbar text'})
    return {'schema': 1, 'verksamhet': v['namn'], 'tillamplighet': tillamplighet(v)[0], 'scheman': scheman, 'nap': n, 'fynd': fynd, 'niva': 'statisk lokal kontroll', 'kontaktberedskap': 'ofullständig' if not v.get('kontaktvagar') else 'uppgifter finns; faktisk leverans ej prövad', 'extern_aktivering': 'spärrad: fiktiv verksamhet' if v['fiktiv'] else 'ej prövad',
            'not': 'NAP ska vara identisk på sajten, i företagsprofilen och i katalogerna; profilens egna uppgifter läses av människa i business.google.com'}


def main(argv=None):
    p = argparse.ArgumentParser(prog='lokal_synlighet', description=__doc__.split('\n\n')[0])
    p.add_argument('kommando', choices=('datablad', 'kontrollera'))
    p.add_argument('--verksamhet', required=True); p.add_argument('--beskrivning'); p.add_argument('--bygge'); p.add_argument('--ut', required=True)
    a = p.parse_args(argv)
    try:
        v = vu.las(a.verksamhet)
        if a.kommando == 'datablad':
            Path(a.ut).write_text(datablad(v, Path(a.beskrivning).read_text(encoding='utf-8') if a.beskrivning else None), encoding='utf-8')
            print(json.dumps({'tillamplighet': tillamplighet(v)[0], 'ut': a.ut}, ensure_ascii=False))
        else:
            if not a.bygge or not Path(a.bygge).is_dir():
                raise vu.Vagrad(['kontrollera kräver --bygge KATALOG'])
            k = kontrollera(v, a.bygge)
            Path(a.ut).write_text(json.dumps(k, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
            print(json.dumps({'scheman': k['scheman'], 'fynd': len(k['fynd']), 'ut': a.ut}, ensure_ascii=False))
    except vu.Vagrad as e:
        print(json.dumps({'vagrad': e.args[0]}, ensure_ascii=False)); return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
