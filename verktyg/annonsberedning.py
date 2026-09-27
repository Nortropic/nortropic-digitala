#!/usr/bin/env python3
"""Annonsberedning (Google Ads och Meta Ads): bygger kampanjstruktur som utkast eller pausade objekt ur en kanalplan,
med validering av textlängder, landningssidornas överensstämmelse, kampanjmärkning (UTM), konverteringsdefinitioner
och budgetvillkor. Startar aldrig annonsering: status är alltid PAUSED, och en live-överföring kräver egen åtkomst
(Google Ads API: utvecklartoken + OAuth + kund-id; Meta Marketing API: åtkomsttoken + annonskonto), som är ett namngivet
externt beroende — inte en mock. Resultatläsning: `rapport` läser en export (CSV/JSON) från plattformen.

    python3 -B verktyg/annonsberedning.py bygg --kanalplan KANALPLAN.json --verksamhet VERKSAMHET.json [--bygge DIR] --ut KATALOG
    python3 -B verktyg/annonsberedning.py rapport --export FIL.csv|.json --ut RAPPORT.json
"""
import argparse
import csv
import json
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verksamhetsuppgifter as vu  # noqa: E402

GRANSER = {'google': {'rubrik': 30, 'beskrivning': 90, 'min_rubriker': 3, 'min_beskrivningar': 2},
           'meta': {'primar_text': 125, 'rubrik': 40, 'beskrivning': 30}}
MATCHTYPER = ('EXACT', 'PHRASE', 'BROAD')
MAL = ('leads', 'samtal', 'bokningar', 'kop', 'besok_i_butik', 'kannedom', 'trafik')


class Vagrad(Exception):
    pass


def utm(url, kalla, medium, kampanj, innehall=None):
    p = urllib.parse.urlsplit(url)
    q = dict(urllib.parse.parse_qsl(p.query))
    q.update({'utm_source': kalla, 'utm_medium': medium, 'utm_campaign': re.sub(r'[^a-z0-9_-]+', '-', kampanj.lower()).strip('-')})
    if innehall:
        q['utm_content'] = re.sub(r'[^a-z0-9_-]+', '-', innehall.lower()).strip('-')
    return urllib.parse.urlunsplit((p.scheme, p.netloc, p.path, urllib.parse.urlencode(q), p.fragment))


def landningssida_finns(bygge, url):
    if not bygge:
        return None
    path = urllib.parse.urlsplit(url).path.lstrip('/')
    root = Path(bygge)
    for c in (root / path, root / path / 'index.html', root / (path.rstrip('/') + '.html'), root / (path.rstrip('/') + '/index.html')):
        if c.is_file():
            return c
    return False


def budskap_pa_sidan(fil, budskap):
    text = re.sub(r'<[^>]+>', ' ', fil.read_text(encoding='utf-8', errors='replace')).lower()
    ord_ = [w for w in re.findall(r'[a-zåäöé0-9]{4,}', budskap.lower())]
    traff = [w for w in ord_ if w in text]
    return len(traff), len(ord_)


def validera_plan(kp, v):
    fel = []
    for f in ('mal', 'malgrupp', 'budskap', 'kampanjer', 'konverteringar', 'budget'):
        if f not in kp:
            fel.append('kanalplanen saknar ' + f)
    if fel:
        raise Vagrad(fel)
    if kp['mal'] not in MAL:
        fel.append('mal ska vara en av ' + ', '.join(MAL))
    if not isinstance(kp['konverteringar'], list) or not kp['konverteringar']:
        fel.append('konverteringar: minst en definition {namn, handelse, varde?}')
    b = kp['budget']
    if not isinstance(b, dict) or b.get('valuta') != 'SEK' or not isinstance(b.get('dag_max'), (int, float)) or b['dag_max'] <= 0:
        fel.append('budget ska vara {valuta: SEK, dag_max: > 0, villkor: text}; villkoret ska namnge mandatet som tillåter spendering')
    if not (isinstance(b, dict) and str(b.get('villkor', '')).strip()):
        fel.append('budget.villkor saknas (utan uttryckligt mandat startas ingen annonsering)')
    for i, k in enumerate(kp['kampanjer']):
        if k.get('kanal') not in ('google', 'meta'):
            fel.append('kampanjer[%d].kanal ska vara google eller meta' % i)
        if not k.get('landningssida', '').startswith('https://'):
            fel.append('kampanjer[%d].landningssida ska vara absolut https' % i)
    if fel:
        raise Vagrad(fel)


def google_objekt(k, kp, v, bygge, fynd):
    g = GRANSER['google']
    rubriker = k.get('rubriker') or []; beskr = k.get('beskrivningar') or []
    for r in rubriker:
        if len(r) > g['rubrik']:
            fynd.append('google %s: rubrik över %d tecken: %r' % (k['namn'], g['rubrik'], r))
    for b in beskr:
        if len(b) > g['beskrivning']:
            fynd.append('google %s: beskrivning över %d tecken: %r' % (k['namn'], g['beskrivning'], b))
    if len(rubriker) < g['min_rubriker'] or len(beskr) < g['min_beskrivningar']:
        fynd.append('google %s: minst %d rubriker och %d beskrivningar' % (k['namn'], g['min_rubriker'], g['min_beskrivningar']))
    sokord = []
    for s in k.get('sokord') or []:
        mt = (s.get('match') or 'PHRASE').upper()
        if mt not in MATCHTYPER:
            fynd.append('google %s: okänd matchtyp %s' % (k['namn'], mt))
        sokord.append({'keyword': {'text': s['text'], 'match_type': mt}, 'status': 'ENABLED'})
    url = utm(k['landningssida'], 'google', 'cpc', k['namn'])
    return {'campaign': {'name': k['namn'], 'status': 'PAUSED', 'advertising_channel_type': 'SEARCH', 'campaign_budget': {'amount_micros': int(kp['budget']['dag_max'] * 1_000_000), 'delivery_method': 'STANDARD', 'currency': 'SEK'},
                         'geo_targets': k.get('geografi') or (v.get('rackvidd') or {}).get('orter') or [], 'languages': ['sv']},
            'ad_groups': [{'name': k['namn'] + ' — grupp 1', 'status': 'PAUSED', 'keywords': sokord, 'negative_keywords': [{'text': n, 'match_type': 'PHRASE'} for n in k.get('negativa') or []],
                           'ads': [{'type': 'RESPONSIVE_SEARCH_AD', 'status': 'PAUSED', 'headlines': [{'text': r} for r in rubriker], 'descriptions': [{'text': b} for b in beskr], 'final_urls': [url]}]}],
            'conversion_actions': [{'name': c['namn'], 'category': c.get('kategori', 'LEAD'), 'value': c.get('varde'), 'counting': 'ONE_PER_CLICK'} for c in kp['konverteringar']],
            'not': 'utkast; överföring till Google Ads API (customers.campaigns mutate m.fl.) kräver utvecklartoken, OAuth och kund-id; status förblir PAUSED tills mandat att spendera finns'}


def meta_objekt(k, kp, v, bygge, fynd):
    g = GRANSER['meta']
    pt = k.get('primar_text', ''); ru = k.get('rubrik', ''); be = k.get('beskrivning', '')
    if len(pt) > g['primar_text']:
        fynd.append('meta %s: primär text över %d tecken (visas avkortad)' % (k['namn'], g['primar_text']))
    if len(ru) > g['rubrik']:
        fynd.append('meta %s: rubrik över %d tecken' % (k['namn'], g['rubrik']))
    if len(be) > g['beskrivning']:
        fynd.append('meta %s: beskrivning över %d tecken' % (k['namn'], g['beskrivning']))
    if not k.get('bilder'):
        fynd.append('meta %s: inga kreativa tillgångar angivna (bild eller video med rättigheter)' % k['namn'])
    url = utm(k['landningssida'], 'meta', 'paid-social', k['namn'])
    mal_till_objective = {'leads': 'OUTCOME_LEADS', 'samtal': 'OUTCOME_LEADS', 'bokningar': 'OUTCOME_LEADS', 'kop': 'OUTCOME_SALES', 'besok_i_butik': 'OUTCOME_TRAFFIC', 'kannedom': 'OUTCOME_AWARENESS', 'trafik': 'OUTCOME_TRAFFIC'}
    return {'campaign': {'name': k['namn'], 'status': 'PAUSED', 'objective': mal_till_objective[kp['mal']], 'special_ad_categories': k.get('sarskilda_kategorier') or []},
            'adset': {'name': k['namn'] + ' — annonsgrupp 1', 'status': 'PAUSED', 'daily_budget': int(kp['budget']['dag_max'] * 100), 'currency': 'SEK',
                      'targeting': {'geo_locations': k.get('geografi') or (v.get('rackvidd') or {}).get('orter') or [], 'age_min': k.get('alder_min', 18), 'age_max': k.get('alder_max', 65), 'interests': k.get('intressen') or []},
                      'optimization_goal': 'LEAD_GENERATION' if kp['mal'] in ('leads', 'samtal', 'bokningar') else 'LINK_CLICKS'},
            'ad': {'name': k['namn'] + ' — annons 1', 'status': 'PAUSED', 'creative': {'primary_text': pt, 'headline': ru, 'description': be, 'link': url, 'call_to_action': k.get('handling', 'LEARN_MORE'), 'images': k.get('bilder') or []}},
            'not': 'utkast; överföring till Meta Marketing API (act_<konto>/campaigns, adsets, ads) kräver åtkomsttoken och annonskonto; status förblir PAUSED tills mandat att spendera finns'}


def bygg(kp, v, bygge=None):
    validera_plan(kp, v)
    fynd = []
    ut = {'schema': 1, 'verksamhet': v['namn'], 'fiktiv': v['fiktiv'], 'mal': kp['mal'], 'malgrupp': kp['malgrupp'], 'budskap': kp['budskap'],
          'konverteringar': kp['konverteringar'], 'budget': kp['budget'], 'sparning': {'utm': 'utm_source/utm_medium/utm_campaign per kampanj; konverteringar mäts på sajten (uppfoljning.md)'},
          'google': [], 'meta': [], 'landningssidor': [], 'fynd': fynd, 'live': False,
          'not': 'utkast/pausade objekt; ingen annonsering startas och ingen budget spenderas utan uttryckligt mandat (ordern avsnitt 4); en fiktiv verksamhet får inga verkliga kampanjer'}
    for k in kp['kampanjer']:
        fil = landningssida_finns(bygge, k['landningssida'])
        rad = {'kampanj': k['namn'], 'landningssida': k['landningssida'], 'finns_i_bygget': None if fil is None else bool(fil)}
        if fil:
            traff, antal = budskap_pa_sidan(fil, k.get('budskap') or kp['budskap'])
            rad['budskap_overensstammelse'] = '%d/%d ord' % (traff, antal)
            if antal and traff / antal < 0.5:
                fynd.append('%s: landningssidan bär inte annonsens budskap (%d/%d ord); annons och sida ska säga samma sak' % (k['namn'], traff, antal))
        elif fil is False:
            fynd.append('%s: landningssidan finns inte i bygget: %s' % (k['namn'], k['landningssida']))
        ut['landningssidor'].append(rad)
        (ut['google'] if k['kanal'] == 'google' else ut['meta']).append(google_objekt(k, kp, v, bygge, fynd) if k['kanal'] == 'google' else meta_objekt(k, kp, v, bygge, fynd))
    return ut


def beredning_md(ut):
    lines = ['# Annonsberedning — %s (mål: %s)' % (ut['verksamhet'], ut['mal']), '', '**Status:** utkast, pausade objekt. Ingen spendering. Budgetvillkor: %s (dag max %s %s).' % (ut['budget'].get('villkor'), ut['budget'].get('dag_max'), ut['budget'].get('valuta')), '',
             '## Målgrupp', ut['malgrupp'], '', '## Budskap', ut['budskap'], '', '## Konverteringar']
    lines += ['- %s (%s)' % (c['namn'], c.get('handelse', '')) for c in ut['konverteringar']]
    lines += ['', '## Landningssidor']
    lines += ['- %s → %s: finns %s; budskap %s' % (r['kampanj'], r['landningssida'], r['finns_i_bygget'], r.get('budskap_overensstammelse', 'ej prövat')) for r in ut['landningssidor']]
    lines += ['', '## Google Ads (%d kampanjer, PAUSED)' % len(ut['google'])]
    for g in ut['google']:
        lines.append('- %s: %d sökord, %d rubriker, %d beskrivningar' % (g['campaign']['name'], len(g['ad_groups'][0]['keywords']), len(g['ad_groups'][0]['ads'][0]['headlines']), len(g['ad_groups'][0]['ads'][0]['descriptions'])))
    lines += ['', '## Meta Ads (%d kampanjer, PAUSED)' % len(ut['meta'])]
    for m in ut['meta']:
        lines.append('- %s: %s, dagbudget %s öre' % (m['campaign']['name'], m['campaign']['objective'], m['adset']['daily_budget']))
    lines += ['', '## Fynd att åtgärda före överföring'] + (['- ' + f for f in ut['fynd']] or ['- inga']) + ['', ut['not']]
    return '\n'.join(lines) + '\n'


def rapport(export):
    """Resultatläsning ur plattformsexport: affärsnytta (konverteringar) skilt från proxyvärden (klick, visningar)."""
    p = Path(export)
    rows = json.loads(p.read_text(encoding='utf-8')) if p.suffix == '.json' else list(csv.DictReader(p.open(encoding='utf-8-sig')))
    per = {}
    for r in rows:
        namn = r.get('campaign') or r.get('Campaign') or r.get('campaign_name') or r.get('Kampanj') or '(okänd)'
        d = per.setdefault(namn, {'kostnad': 0.0, 'klick': 0, 'visningar': 0, 'konverteringar': 0.0})
        def num(*keys):
            for k in keys:
                if k in r and str(r[k]).strip():
                    return float(str(r[k]).replace(',', '.').replace(' ', ''))
            return 0.0
        d['kostnad'] += num('cost', 'Cost', 'spend', 'Kostnad'); d['klick'] += int(num('clicks', 'Clicks', 'Klick')); d['visningar'] += int(num('impressions', 'Impressions', 'Visningar')); d['konverteringar'] += num('conversions', 'Conversions', 'results', 'Konverteringar')
    for d in per.values():
        d['kostnad_per_konvertering'] = round(d['kostnad'] / d['konverteringar'], 2) if d['konverteringar'] else None
    return {'schema': 1, 'kampanjer': per, 'affarsnytta': 'konverteringar och kostnad per konvertering', 'proxy': 'klick, visningar, ctr',
            'not': 'plattformens konverteringar är plattformens attribution; verklig affärsnytta (offerter, bokningar) läses i uppföljningens lead-kedja'}


def main(argv=None):
    p = argparse.ArgumentParser(prog='annonsberedning', description=__doc__.split('\n\n')[0])
    p.add_argument('kommando', choices=('bygg', 'rapport'))
    p.add_argument('--kanalplan'); p.add_argument('--verksamhet'); p.add_argument('--bygge'); p.add_argument('--export'); p.add_argument('--ut', required=True)
    a = p.parse_args(argv)
    try:
        if a.kommando == 'bygg':
            if not (a.kanalplan and a.verksamhet):
                raise Vagrad(['bygg kräver --kanalplan och --verksamhet'])
            v = vu.las(a.verksamhet)
            kp = json.loads(Path(a.kanalplan).read_text(encoding='utf-8'))
            ut = bygg(kp, v, a.bygge)
            d = Path(a.ut); d.mkdir(parents=True, exist_ok=True)
            (d / 'google-ads.json').write_text(json.dumps(ut['google'], ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
            (d / 'meta-ads.json').write_text(json.dumps(ut['meta'], ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
            (d / 'BEREDNING.json').write_text(json.dumps(ut, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
            (d / 'BEREDNING.md').write_text(beredning_md(ut), encoding='utf-8')
            print(json.dumps({'google': len(ut['google']), 'meta': len(ut['meta']), 'fynd': len(ut['fynd']), 'ut': str(d)}, ensure_ascii=False))
        else:
            if not a.export:
                raise Vagrad(['rapport kräver --export'])
            r = rapport(a.export)
            Path(a.ut).write_text(json.dumps(r, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
            print(json.dumps({'kampanjer': len(r['kampanjer']), 'ut': a.ut}))
    except (Vagrad, vu.Vagrad) as e:
        print(json.dumps({'vagrad': e.args[0]}, ensure_ascii=False))
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
