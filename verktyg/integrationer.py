#!/usr/bin/env python3
"""Ordinarie integrationsväg: val, körbara exempel, prov och befintliga kanaler.

Exempel: python3 -B verktyg/integrationer.py plan --val exempel/integrationer/VAL.json --ut /privat/fall/integrationer
All kontoåtkomst är explicit. Ingen kontoanskaffning, aktivering eller schemakörning.
"""
import argparse
import datetime
import hashlib
import html
import importlib
import json
import os
import platform
import sqlite3
import sys
import urllib.parse
from pathlib import Path
from integrationer_adapter import Fel, Journal, JournalfelEfterAnrop, ResendTest, StripeTest, cal_readback, las_nyckel, text, privat_fil
from integrationer_mottagning import Inkorg


KANALER = {'seo': 'seo_kontroll', 'gsc': 'sokkonsol', 'gbp': 'lokal_synlighet',
           'annonser': 'annonsberedning', 'matning': 'uppfoljning'}
HOSTS = {'cal': 'cal.com', 'tidycal': 'tidycal.com', 'tally': 'tally.so',
         'stripe-payment-link': 'buy.stripe.com'}


def skriv_json(path, data):
    p = privat_fil(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    # Befintliga kvitton skrivs aldrig över.
    fd = os.open(str(p), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')


def lank(provider, url):
    if provider not in tuple(HOSTS) + ('simplybook',):
        raise Fel('okand_standardvag')
    u = urllib.parse.urlsplit(text(url, 'leverantorslank', 1000))
    if u.scheme != 'https' or u.username or u.password or u.port not in (None, 443) or u.fragment:
        raise Fel('leverantorslank_kraver_https_utan_hemligheter')
    host = u.hostname or ''
    valid = host == HOSTS.get(provider) if provider != 'simplybook' else host.endswith('.simplybook.me') and host != '.simplybook.me'
    if not valid or u.query:
        raise Fel('fel_leverantorsvard_eller_query')
    return url


def plan(value):
    if value.get('schema') != 'digitala-integrationsval/1' or not isinstance(value.get('val'), list):
        raise Fel('integrationsval_schema_saknas')
    result = []
    ids = set()
    for row in value['val']:
        id_ = text(row.get('id'), 'val_id', 80)
        if id_ in ids:
            raise Fel('dubbelt_val_id')
        ids.add(id_)
        for k in ('behov', 'kalla', 'motivering', 'ansvarig', 'reservvag'):
            text(row.get(k), k, 1000)
        provider = row.get('leverantor')
        url = lank(provider, row.get('url'))
        if row.get('niva') != 'leverantorsvy':
            raise Fel('planen_genererar_endast_lank_inte_apiintegration')
        label = text(row.get('lanktext'), 'lanktext', 100)
        result.append(dict(row, html='<a href="' + html.escape(url, quote=True) + '">' + html.escape(label) + '</a>',
                           leveransstatus='lank_beredd_inte_leverantorsprovad',
                           prov=['besok_i_ratt_tjanst', 'ratt_innehall_och_tidszon', 'bekraftelse',
                                 'ombokning_avbokning' if provider in ('cal', 'tidycal', 'simplybook') else 'mottagning_och_fel']))
    return {'schema': 'digitala-integrationsplan/1', 'val': result, 'externa_anrop': 0,
            'kunddrift': value.get('kunddrift'), 'kanalverktyg': KANALER,
            'bokning_betalning_sammankopplad': False,
            'not': 'En betalningslänk reserverar ingen bokning. Använd bokningstjänstens egen betalningskoppling när behovet kräver atomärt förlopp.'}


def bindning():
    here = Path(__file__).parent
    return {'tid': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'python': platform.python_version(),
            'kod_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in sorted(here.glob('integrationer*.py'))}}


def las_acceptkvitto(path, account, command, level, version=None):
    """Läs äldre/nya kvitton utan att migrera eller återsända handlingen."""
    raw = privat_fil(path).read_bytes()
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError):
        raise Fel('ogiltigt_acceptkvitto') from None
    commands = ('resend-test', 'resend-aterlas') if command == 'resend-aterlas' else ('stripe-checkout-test', 'stripe-aterlas-test')
    if (not isinstance(value, dict) or value.get('schema') not in
            ('digitala-integrationsprov/1', 'digitala-integrationsprov/2')
            or value.get('kontoetikett') != account or value.get('kommando') not in commands
            or value.get('niva') != level or not isinstance(value.get('accepterat'), dict)
            or value['accepterat'].get('niva') != level):
        raise Fel('acceptkvitto_fel_konto_kommando_eller_niva')
    if version and value.get('api_version') not in (None, version):
        raise Fel('acceptkvitto_fel_api_version')
    # /1 saknade explicit api_version. Det äldre beviset skrivs inte om och
    # tilldelas ingen efterhandskonstruerad versionsbindning.
    return value['accepterat'], hashlib.sha256(raw).hexdigest()


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == 'kanal':
        if len(argv) < 2 or argv[1] not in KANALER:
            raise Fel('valj_kanal_' + '_'.join(KANALER))
        # Samma verktyg och spärrar, ingen parallell adapterimplementation.
        return importlib.import_module(KANALER[argv[1]]).main(argv[2:])
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    q = sub.add_parser('plan'); q.add_argument('--val', required=True); q.add_argument('--ut', required=True)
    q = sub.add_parser('crm-export'); q.add_argument('--inkorg', required=True); q.add_argument('--ut', required=True)
    q = sub.add_parser('resend-test')
    q.add_argument('--mottagare', default='delivered@resend.dev')
    q.add_argument('--aterlas', action='store_true')
    q.add_argument('--inkorg'); q.add_argument('--lead-key'); q.add_argument('--ansvarig')
    q = sub.add_parser('stripe-checkout-test')
    q.add_argument('--pris', required=True); q.add_argument('--version', required=True)
    q.add_argument('--success-url', required=True); q.add_argument('--cancel-url', required=True)
    q = sub.add_parser('cal-aterlas')
    q.add_argument('--uid-fil', required=True); q.add_argument('--version', required=True)
    q = sub.add_parser('resend-aterlas'); q.add_argument('--kvitto', required=True)
    q = sub.add_parser('stripe-aterlas-test'); q.add_argument('--kvitto', required=True)
    q.add_argument('--version', required=True)
    for name in ('resend-test', 'stripe-checkout-test', 'cal-aterlas', 'resend-aterlas', 'stripe-aterlas-test'):
        q = sub.choices[name]
        q.add_argument('--nyckel-fil', required=True); q.add_argument('--konto', required=True)
        q.add_argument('--ut', required=True)
        if name in ('resend-test', 'stripe-checkout-test'):
            q.add_argument('--journal', required=True); q.add_argument('--idempotens', required=True)
            q.add_argument('--retry-okant', action='store_true')
    a = p.parse_args(argv)
    if a.command == 'plan':
        result = plan(json.loads(Path(a.val).read_text()))
        out = Path(a.ut)
        skriv_json(out / 'INTEGRATIONSPLAN.json', dict(result, bindning=bindning()))
        content = '<!doctype html><html lang="sv"><meta charset="utf-8"><title>Berett integrationsval</title><h1>Berett integrationsval</h1><p>Exempel att integrera; leverantörsprovet återstår.</p>'
        content += ''.join('<section><h2>' + html.escape(row['behov']) + '</h2><p>' + row['html'] + '</p><p>' + html.escape(row['reservvag']) + '</p></section>' for row in result['val'])
        target = privat_fil(out / 'lankar.html')
        fd = os.open(str(target), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'w') as f:
            f.write(content + '</html>\n')
        return 0
    if a.command == 'crm-export':
        result = Inkorg(a.inkorg).export_crm()
        target = privat_fil(a.ut)
        fd = os.open(str(target), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'w') as f:
            f.write(result)
        return 0
    # Före första nätanropet: kvittoplats får inte finnas, nyckelmetadata privat.
    if privat_fil(a.ut).exists():
        raise Fel('kvittot_finns_redan')
    result = {'schema': 'digitala-integrationsprov/2', 'bindning': bindning(), 'kommando': a.command,
              'kontoetikett': a.konto, 'niva': 'leverantors_api', 'anrop_genomfort': False,
              'utfall_status': None,
              'livekunddrift_verifierad': False, 'received_by_person': False}
    if hasattr(a, 'version'):
        result['api_version'] = a.version
    code = 0
    try:
        key = las_nyckel(a.nyckel_fil)
        if a.command == 'cal-aterlas':
            result['resultat'] = cal_readback(key, las_nyckel(a.uid_fil), a.version)
        elif a.command in ('resend-aterlas', 'stripe-aterlas-test'):
            api = (ResendTest(key, None, a.konto) if a.command == 'resend-aterlas'
                   else StripeTest(key, None, a.konto, a.version))
            result['niva'] = api.niva
            receipt, source_hash = las_acceptkvitto(a.kvitto, a.konto, a.command, api.niva,
                                                   getattr(a, 'version', None))
            result['accepterat'] = receipt
            result['kallkvitto_sha256'] = source_hash
            result['resultat'] = api.readback(receipt)
            result['journal_avstamd'] = False
        elif a.command == 'resend-test':
            api = ResendTest(key, Journal(a.journal), a.konto)
            result['niva'] = api.niva
            fields = [a.inkorg, a.lead_key, a.ansvarig]
            if any(fields) and not all(fields):
                raise Fel('inkorg_lead_key_och_ansvarig_kravs_tillsammans')
            lead = Inkorg(a.inkorg).lead_ref(a.lead_key, a.ansvarig) if all(fields) else None
            result['mottagning'] = lead
            receipt = api.send(a.idempotens, a.mottagare, retry=a.retry_okant,
                               reference=lead['reference'] if lead else None)
            result['accepterat'] = receipt
            result['anrop_genomfort'] = True
            result['resultat'] = receipt
            result['resultat'] = api.readback(receipt) if a.aterlas else receipt
        else:
            api = StripeTest(key, Journal(a.journal), a.konto, a.version)
            result['niva'] = api.niva
            receipt = api.checkout(a.idempotens, a.pris, a.success_url, a.cancel_url, a.retry_okant)
            result['accepterat'] = receipt
            result['anrop_genomfort'] = True
            result['resultat'] = receipt
            result['resultat'] = api.readback(receipt)
        result['anrop_genomfort'] = True
    except JournalfelEfterAnrop as e:
        result['fel'] = e.kod
        result['journal_avstamd'] = False
        code = 1
        if e.accepted is not None:
            result['accepterat'] = e.accepted
            result['resultat'] = e.accepted
            result['anrop_genomfort'] = True
            result['nasta_handling'] = 'aterlas_acceptkvitto_innan_journalavstamning_ingen_ny_post'
            if a.command == 'stripe-checkout-test' or getattr(a, 'aterlas', False):
                try:
                    result['resultat'] = api.readback(e.accepted)
                except Fel as read_error:
                    result['aterlasningsfel'] = read_error.kod
        else:
            result['ursprungligt_fel'] = e.original_error
            result['utfall_okant'] = not e.original_error.startswith('api_avvisat_')
    except Fel as e:
        result['fel'] = e.kod
        code = 1
    except sqlite3.Error:
        result['fel'] = 'journal_eller_mottagning_otillganglig'
        code = 1
    finally:
        outcome = result.get('resultat', {})
        result['utfall_status'] = outcome.get('payment_status', outcome.get('status'))
        skriv_json(a.ut, result)
    print(json.dumps({'kvitto': a.ut, 'anrop_genomfort': result['anrop_genomfort'],
                      'utfall_status': result['utfall_status'], 'niva': result['niva'],
                      'fel': result.get('fel')}))
    return code


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (Fel, OSError, ValueError) as e:
        print('Vägrat: ' + (e.kod if isinstance(e, Fel) else type(e).__name__), file=sys.stderr)
        sys.exit(1)
