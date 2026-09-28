"""Signerad mottagning och liten beständig inkorg, inte CRM/checkoutmotor.

Inga externa sidoeffekter. Händelser är observationer, inte ordnad aktuell status.
Kundens app kan använda samma funktion med sin beständiga lagringsadapter.
"""
import base64
import csv
import hashlib
import hmac
import io
import json
import os
import re
import sqlite3
import time
from integrationer_adapter import Fel, json_bytes, privat_fil, sha, text


MAX_BODY = 65536


def las_json(raw):
    if not isinstance(raw, bytes) or len(raw) > MAX_BODY:
        raise Fel('for_stor_body', 413)
    def pairs(items):
        obj = {}
        for key, value in items:
            if key in obj:
                raise ValueError('duplicate')
            obj[key] = value
        return obj
    try:
        data = json.loads(raw, object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError):
        raise Fel('ogiltig_json') from None
    if not isinstance(data, dict):
        raise Fel('json_objekt_kravs')
    return data


def jamfor(actual, expected):
    if not isinstance(actual, str) or not hmac.compare_digest(actual.encode(), expected.encode()):
        raise Fel('fel_webhooksignatur', 401)


def webhook(provider, raw, headers, config, now=None):
    """Verifiera innan data används; avgränsa konto/form/eventtyp i konfiguration.

    Tally: HMAC på inkommande JSON-bytes, som leverantörens JSON.stringify-payload.
    Värden serialiseras aldrig om med Pythons annorlunda talformat.
    Cal: endast pinnat 2021-10-20 standardpayload, ej egna mallar/sittplatsinferens.
    Stripe: snapshot Checkout-event i testläge, egen kontodestination (ej Connect).
    """
    headers = {k.lower(): v for k, v in headers.items()}
    secret = config.get('secret', '')
    if not isinstance(secret, str) or len(secret) < 16:
        raise Fel('webhookhemlighet_saknas')
    if len(raw) > MAX_BODY:
        raise Fel('for_stor_body', 413)
    if provider == 'stripe':
        parts = headers.get('stripe-signature', '').split(',')
        timestamps = [p[2:] for p in parts if p.startswith('t=')]
        signatures = [p[3:] for p in parts if p.startswith('v1=')]
        if len(timestamps) != 1 or not timestamps[0].isdigit():
            raise Fel('ogiltig_stripe_signatur', 401)
        timestamp = timestamps[0]
        if abs((time.time() if now is None else now) - int(timestamp)) > 300:
            raise Fel('stripe_signatur_for_gammal', 401)
        expected = hmac.new(secret.encode(), timestamp.encode() + b'.' + raw, hashlib.sha256).hexdigest()
        if not any(hmac.compare_digest(s, expected) for s in signatures):
            raise Fel('fel_webhooksignatur', 401)
    elif provider in ('cal', 'tally'):
        digest = hmac.new(secret.encode(), raw, hashlib.sha256)
        expected = digest.hexdigest() if provider == 'cal' else base64.b64encode(digest.digest()).decode()
        jamfor(headers.get('x-cal-signature-256' if provider == 'cal' else 'tally-signature'), expected)
    else:
        raise Fel('webhookleverantor_stods_inte')
    event = las_json(raw)
    if provider == 'stripe':
        supported = ('checkout.session.completed', 'checkout.session.async_payment_succeeded',
                     'checkout.session.async_payment_failed', 'checkout.session.expired')
        if event.get('livemode') is not False or event.get('account') or event.get('type') not in supported:
            raise Fel('stripe_scope_stods_inte')
        envelope = event.get('data')
        if not isinstance(envelope, dict) or not isinstance(envelope.get('object'), dict):
            raise Fel('stripe_snapshot_saknas')
        data = envelope['object']
        if data.get('object') != 'checkout.session' or data.get('livemode') is not False or not str(data.get('id', '')).startswith('cs_test_'):
            raise Fel('stripe_testcheckout_saknas')
        if event.get('api_version') != config.get('api_version') or not config.get('api_version'):
            raise Fel('stripe_webhookversion_stammer_inte')
        ref = data.get('client_reference_id')
        if not isinstance(ref, str) or not ref.startswith(config.get('reference_prefix') or '\x00'):
            raise Fel('stripe_referens_utanfor_scope')
        return {'provider': provider, 'id': text(event.get('id'), 'event_id'),
                'scope': config['reference_prefix'], 'type': event['type'], 'object_id': data['id'],
                'observed_at': event.get('created'), 'payment_status': data.get('payment_status'),
                'paid_test_observation': data.get('payment_status') == 'paid',
                'latest_status_verified': False, 'fulfilment_performed': False}
    if provider == 'cal':
        if headers.get('x-cal-webhook-version') != '2021-10-20' or config.get('version') != '2021-10-20':
            raise Fel('cal_webhookversion_stammer_inte')
        data = event.get('payload', {})
        if event.get('triggerEvent') not in ('BOOKING_CREATED', 'BOOKING_RESCHEDULED', 'BOOKING_CANCELLED', 'BOOKING_REQUESTED', 'BOOKING_PAID'):
            raise Fel('cal_event_stods_inte')
        if not isinstance(data, dict) or not isinstance(config.get('event_type_id'), int) or data.get('eventTypeId') != config['event_type_id']:
            raise Fel('cal_eventtyp_utanfor_scope')
        uid = text(data.get('uid'), 'booking_uid')
        created = text(event.get('createdAt'), 'created_at')
        # UID kan ge åtkomst till bokningen: spara bara hash, inga cancel-länkar.
        return {'provider': provider, 'id': sha([event['triggerEvent'], created, data]),
                'scope': str(config['event_type_id']), 'type': event['triggerEvent'],
                'object_id': hashlib.sha256(uid.encode()).hexdigest(), 'observed_at': created,
                'status_observation': data.get('status'), 'start': data.get('startTime'),
                'end': data.get('endTime'), 'latest_status_verified': False,
                'seat_or_resource_capacity_verified': False}
    data = event.get('data', {})
    if event.get('eventType') != 'FORM_RESPONSE' or not isinstance(data, dict) or data.get('formId') != config.get('form_id') or not config.get('form_id'):
        raise Fel('tally_form_utanfor_scope')
    fields = data.get('fields')
    if not isinstance(fields, list) or len(fields) > 100:
        raise Fel('tally_falt_saknas')
    values = {}
    for field in fields:
        if not isinstance(field, dict) or field.get('key') in values:
            raise Fel('tally_falt_ogiltigt')
        values[field.get('key')] = field.get('value')
    mapping = config.get('fields', {})
    lead = validera_lead({name: values.get(mapping.get(name)) for name in ('name', 'email', 'message')})
    return {'provider': provider, 'id': text(event.get('eventId'), 'event_id'), 'scope': config['form_id'],
            'type': 'FORM_RESPONSE', 'object_id': text(data.get('submissionId'), 'submission_id'),
            'observed_at': event.get('createdAt'), 'lead': lead,
            'owner': text(config.get('owner'), 'ansvarig'),
            'follow_up': text(config.get('follow_up'), 'uppfoljning'), 'received_by_person': False}


def validera_lead(data):
    if not isinstance(data, dict) or set(data) != {'name', 'email', 'message'}:
        raise Fel('formularfalt_stammer_inte')
    name = text(data.get('name'), 'namn', 100)
    email = text(data.get('email'), 'epost', 254)
    if not re.fullmatch(r'[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+', email):
        raise Fel('ogiltig_epost')
    message = data.get('message')
    if not isinstance(message, str) or not message.strip() or len(message) > 4000 or '\x00' in message:
        raise Fel('ogiltigt_meddelande')
    return {'name': name, 'email': email, 'message': message}


class Inkorg:
    """Ett atomärt inbox-insert. Ingen remote CRM-synk eller e-post antas."""
    def __init__(self, path):
        self.path = privat_fil(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(self.path), os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS inbox (id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, body TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS form_submission (id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL)')

    def db(self):
        return sqlite3.connect(str(self.path), timeout=2)

    def receive(self, event):
        id_ = event['provider'] + ':' + event['scope'] + ':' + event['id']
        fingerprint = sha(event)
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            old = db.execute('SELECT fingerprint FROM inbox WHERE id=?', (id_,)).fetchone()
            if old:
                if old[0] != fingerprint:
                    raise Fel('event_id_med_andrat_innehall', 409)
                return {'status': 'stored', 'duplicate': True, 'received_by_person': False}
            # En Tally-submission kan levereras med nytt event-id; inte nytt lead.
            if event['provider'] == 'tally':
                sid = event['scope'] + ':' + event['object_id']
                sfp = sha([event['lead'], event['owner'], event['follow_up']])
                previous = db.execute('SELECT fingerprint FROM form_submission WHERE id=?', (sid,)).fetchone()
                if previous:
                    if previous[0] != sfp:
                        raise Fel('submission_med_andrat_innehall', 409)
                    return {'status': 'stored', 'duplicate': True, 'received_by_person': False}
                db.execute('INSERT INTO form_submission VALUES (?,?)', (sid, sfp))
            db.execute('INSERT INTO inbox VALUES (?,?,?)', (id_, fingerprint, json_bytes(event).decode()))
        return {'status': 'stored', 'duplicate': False, 'received_by_person': False}

    def lead(self, key, data, owner, follow_up):
        text(key, 'idempotens', 120)
        return self.receive({'provider': 'local_form', 'scope': text(owner, 'ansvarig'), 'id': key,
                             'lead': validera_lead(data), 'owner': owner,
                             'follow_up': text(follow_up, 'uppfoljning'), 'received_by_person': False})

    def export_crm(self):
        # CSV är en importfil, inte bevis på mottagning i kundens CRM.
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['source_id', 'name', 'email', 'message', 'owner', 'follow_up', 'status'])
        with self.db() as db:
            for id_, body in db.execute('SELECT id,body FROM inbox ORDER BY id'):
                event = json.loads(body)
                if 'lead' not in event:
                    continue
                vals = [id_, event['lead']['name'], event['lead']['email'], event['lead']['message'],
                        event['owner'], event['follow_up'], 'mottagen_inte_hanterad']
                # Förhindra kalkylbladsformler i vanlig CSV-import.
                writer.writerow(["'" + x if x.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')) else x for x in vals])
        return output.getvalue()

    def lead_ref(self, key, owner):
        """Bind separat testnotifiering till faktiskt lagrat formulär, utan persondata."""
        id_ = 'local_form:' + text(owner, 'ansvarig') + ':' + text(key, 'idempotens', 120)
        with self.db() as db:
            row = db.execute('SELECT fingerprint FROM inbox WHERE id=?', (id_,)).fetchone()
        if not row:
            raise Fel('sparad_forfragan_saknas', 404)
        return {'record_sha256': row[0], 'reference': hashlib.sha256(id_.encode()).hexdigest(),
                'stored': True, 'received_by_person': False}
