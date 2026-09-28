"""Små leverantörsadaptrar för testbar standardintegration, Python 3.9+.

Ingen schemaläggare, CRM eller betalningsmotor. Resend är begränsad till dess
syntetiska testmottagare; Stripe till testnycklar. HTTP följer aldrig redirects.
Injicerad transport märks alltid kontraktsprov. Se integrationer-standardvagar.md.
"""
import hashlib
import json
import os
import re
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


class Fel(Exception):
    def __init__(self, kod, status=400):
        super().__init__(kod)
        self.kod, self.status = kod, status


class JournalfelEfterAnrop(Fel):
    """Nätutfallet får inte döljas av ett efterföljande lagringsfel."""
    def __init__(self, *, accepted=None, original_error=None):
        super().__init__('journalfel_efter_accepterat_anrop' if accepted is not None
                         else 'journalfel_efter_anrop', 503)
        self.accepted = accepted
        self.original_error = original_error


def json_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(json_bytes(value)).hexdigest()


def text(value, name, limit=200):
    if not isinstance(value, str) or not value.strip() or len(value) > limit or any(ord(c) < 32 for c in value):
        raise Fel('ogiltig_' + name)
    return value


def privat_fil(path):
    original = Path(path).expanduser()
    if original.is_symlink():
        raise Fel('privat_fil_far_inte_vara_symlink')
    p = original.resolve()
    repo = Path(__file__).resolve().parents[1]
    if repo == p or repo in p.parents:
        raise Fel('privat_fil_maste_ligga_utanfor_repo')
    if p.is_symlink() or (p.exists() and p.stat().st_mode & 0o077):
        raise Fel('privat_fil_kraver_0600')
    return p


def las_nyckel(path):
    p = privat_fil(path)
    # Endast en rå nyckel. Inga env-filer, skal eller expanderade referenser.
    value = p.read_text().strip()
    text(value, 'nyckel', 512)
    return value


class IngenRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def http(method, url, headers, body):
    u = urllib.parse.urlsplit(url)
    if u.scheme != 'https' or u.netloc not in ('api.resend.com', 'api.stripe.com', 'api.cal.com') or u.username or u.fragment:
        raise Fel('otillaten_api_origin')
    # Tjänstens edge avvisar standard-UA Python-urllib (observerat error 1010).
    # En sann klientidentitet, samma TLS/auth/origin; inget browsermaskerande.
    req = urllib.request.Request(url, method=method,
                                 headers=dict(headers, **{'User-Agent': 'Nortropic-Integration-Probe/1.0'}), data=body)
    try:
        with urllib.request.build_opener(IngenRedirect()).open(req, timeout=15) as r:
            raw = r.read(262145)
            if len(raw) > 262144:
                raise Fel('for_stort_api_svar', 502)
            return r.status, json.loads(raw), dict(r.headers)
    except urllib.error.HTTPError as e:
        # Varken felbody, authhuvuden eller persondata går vidare till kvittot.
        return e.code, {}, {'Retry-After': e.headers.get('Retry-After', '')}
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        raise Fel('transportutfall_okant', 503) from None


class Journal:
    """Beständig idempotensbokföring. Kundens host behöver beständig disk/DB.

    Ingen automatisk retry. Okänt utfall får explicit återförsök med SAMMA nyckel
    och bytes inom 23 h, under leverantörernas dokumenterade 24 h-fönster.
    En lease skyddar parallella anrop. Processavbrott lämnar avsikt sparad.
    """
    def __init__(self, path, now=time.time):
        self.path = privat_fil(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(self.path), os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        self.now = now
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS operation '
                       '(id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, created REAL NOT NULL, '
                       'lease REAL NOT NULL, retry_at REAL NOT NULL, state TEXT NOT NULL, result TEXT)')

    def db(self):
        return sqlite3.connect(str(self.path), timeout=2)

    def begin(self, key, fingerprint, retry=False):
        text(key, 'idempotens', 500)
        now = self.now()
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT fingerprint,created,lease,retry_at,state,result FROM operation WHERE id=?', (key,)).fetchone()
            if row:
                if row[0] != fingerprint:
                    raise Fel('samma_nyckel_annat_innehall', 409)
                if row[4] == 'accepted':
                    return json.loads(row[5])
                if row[4] == 'rejected':
                    raise Fel('tidigare_avvisat_anrop', 409)
                if row[2] > now:
                    raise Fel('anrop_pagar', 409)
                if row[3] > now:
                    raise Fel('vanta_retry_after', 429)
                if now - row[1] >= 23 * 3600:
                    raise Fel('okant_utfall_kraver_manuell_avstamning', 409)
                if not retry:
                    raise Fel('okant_utfall_kraver_explicit_retry_med_samma_nyckel', 409)
                db.execute('UPDATE operation SET lease=?,state=? WHERE id=?', (now + 60, 'in_flight', key))
            else:
                db.execute('INSERT INTO operation VALUES (?,?,?,?,?,?,?)',
                           (key, fingerprint, now, now + 60, 0, 'in_flight', None))
        return None

    def finish(self, key, state, result=None, retry_after=0):
        with self.db() as db:
            db.execute('UPDATE operation SET lease=0,retry_at=?,state=?,result=? WHERE id=?',
                       (self.now() + retry_after, state, json.dumps(result), key))


class API:
    def __init__(self, key, journal, account, transport=None):
        self.key = text(key, 'nyckel', 512)
        self.account = text(account, 'konto', 100)
        self.journal, self.transport = journal, transport or http
        self.niva = 'kontraktsprov' if transport else 'leverantors_api'

    def post(self, origin, path, payload, key, validate, *, retry=False, form=False, extra=None):
        # Fingerprint omfattar konto, mål, exakt kropp och versionshuvuden.
        body = urllib.parse.urlencode(payload).encode() if form else json_bytes(payload)
        heads = {'Authorization': 'Bearer ' + self.key, 'Idempotency-Key': key,
                 'Content-Type': 'application/x-www-form-urlencoded' if form else 'application/json'}
        heads.update(extra or {})
        journal_key = origin + '/' + self.account + '/' + key
        fp = sha([self.account, origin, path, body.decode(), extra or {}, self.niva])
        previous = self.journal.begin(journal_key, fp, retry)
        if previous is not None:
            return dict(previous, duplicate=True)

        def record_failure(state, error, retry_after=0):
            try:
                self.journal.finish(journal_key, state, retry_after=retry_after)
            except (sqlite3.Error, OSError):
                # Avsikten från begin finns kvar. Inget nytt anrop görs och inget
                # leverantörsutfall uppfinns om även felbokföringen misslyckas.
                raise JournalfelEfterAnrop(original_error=error.kod) from None
            raise error

        try:
            code, result, response_headers = self.transport('POST', origin + path, heads, body)
        except Fel as e:
            record_failure('unknown', e)
        except Exception:
            record_failure('unknown', Fel('transportutfall_okant', 503))
        if not 200 <= code < 300:
            transient = code in (408, 409, 429) or code >= 500
            delay = response_headers.get('Retry-After', response_headers.get('retry-after', '0'))
            delay = min(int(delay), 86400) if str(delay).isdigit() else (60 if code == 429 else 0)
            record_failure('unknown' if transient else 'rejected',
                           Fel('api_avvisat_' + str(code), 503 if transient else 502), delay)
        try:
            safe_result = dict(validate(result), niva=self.niva, duplicate=False)
        except Fel as e:
            record_failure('unknown', e)
        except Exception:
            record_failure('unknown', Fel('ogiltigt_api_svar', 502))
        try:
            self.journal.finish(journal_key, 'accepted', safe_result)
        except (sqlite3.Error, OSError):
            # Ett validerat accept-ID är känt även om journalens commit faller.
            # Bevara det för kvitto/GET; skriv inte över läget med "unknown".
            raise JournalfelEfterAnrop(accepted=safe_result) from None
        return safe_result

    def get(self, url, extra=None):
        headers = {'Authorization': 'Bearer ' + self.key}
        headers.update(extra or {})
        try:
            code, body, _ = self.transport('GET', url, headers, None)
        except Exception:
            raise Fel('aterlasning_misslyckades', 503) from None
        if code != 200 or not isinstance(body, dict):
            raise Fel('aterlasning_avvisad', 502)
        return body


class ResendTest(API):
    """Inga mänskliga mottagare, inga kunduppgifter, ingen leverans till person."""
    def send(self, key, recipient='delivered@resend.dev', retry=False, reference=None):
        if not re.fullmatch(r'(delivered|bounced|complained)(\+[a-zA-Z0-9_-]{1,60})?@resend\.dev', recipient):
            raise Fel('endast_resend_syntetisk_testmottagare')
        text(key, 'idempotens', 120)
        payload = {'from': 'Nortropic systemprov <onboarding@resend.dev>', 'to': [recipient],
                   'subject': 'Syntetiskt integrationsprov ' + key,
                   'text': 'Endast ett syntetiskt integrationsprov. Inga kunduppgifter eller kundatgarder.'}
        if reference is not None:
            if not re.fullmatch(r'[a-f0-9]{64}', reference):
                raise Fel('provreferens_maste_vara_sha256')
            payload['text'] += ' Lokal provreferens: ' + reference
        def validate(body):
            if not isinstance(body, dict) or not re.fullmatch(r'[a-f0-9-]{36}', str(body.get('id', ''))):
                raise Fel('resend_svar_saknar_id', 502)
            return {'provider_id': body['id'], 'status': 'provider_accepted', 'recipient': recipient,
                    'received_by_person': False}
        return self.post('https://api.resend.com', '/emails', payload, key, validate, retry=retry)

    def readback(self, receipt):
        id_ = receipt.get('provider_id', '')
        if not isinstance(id_, str) or not re.fullmatch(r'[a-f0-9-]{36}', id_):
            raise Fel('ogiltigt_resend_id')
        recipient = receipt.get('recipient')
        if not isinstance(recipient, str) or not re.fullmatch(r'(delivered|bounced|complained)(\+[a-zA-Z0-9_-]{1,60})?@resend\.dev', recipient):
            raise Fel('endast_resend_syntetisk_testmottagare')
        body = self.get('https://api.resend.com/emails/' + id_)
        if body.get('id') != id_ or body.get('to') != [receipt['recipient']] or 'onboarding@resend.dev' not in body.get('from', ''):
            raise Fel('resend_aterlasning_fel_identitet', 502)
        event = body.get('last_event')
        status = {'delivered': 'delivered_test', 'bounced': 'bounced_test',
                  'complained': 'complained_test', 'failed': 'failed_test'}.get(event, 'provider_accepted')
        return dict(receipt, status=status, observed_event=event, received_by_person=False)


class StripeTest(API):
    def __init__(self, key, journal, account, version, transport=None):
        if not key.startswith('sk_test_'):
            raise Fel('stripe_kraver_testnyckel')
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}(\.[a-z]+)?', version):
            raise Fel('explicit_stripe_api_version_kravs')
        super().__init__(key, journal, account, transport)
        self.headers = {'Stripe-Version': version}

    def checkout(self, key, price, success_url, cancel_url, retry=False):
        if not re.fullmatch(r'price_[a-zA-Z0-9]+', price):
            raise Fel('befintligt_testpris_kravs')
        for url in (success_url, cancel_url):
            u = urllib.parse.urlsplit(url)
            if u.scheme != 'https' or not u.hostname or u.username or u.fragment:
                raise Fel('checkout_returlank_kraver_https')
        if urllib.parse.urlsplit(success_url).netloc != urllib.parse.urlsplit(cancel_url).netloc:
            raise Fel('checkout_returlankar_olika_origin')
        price_object = self.get('https://api.stripe.com/v1/prices/' + price, self.headers)
        if (price_object.get('id') != price or price_object.get('livemode') is not False
                or price_object.get('active') is not True or price_object.get('type') != 'one_time'
                or not isinstance(price_object.get('unit_amount'), int) or price_object['unit_amount'] <= 0):
            raise Fel('stripe_pris_ar_inte_aktivt_engangstestpris', 502)
        payload = {'mode': 'payment', 'line_items[0][price]': price, 'line_items[0][quantity]': 1,
                   'success_url': success_url, 'cancel_url': cancel_url, 'client_reference_id': key}
        def validate(body):
            if not isinstance(body, dict) or body.get('livemode') is not False or not re.fullmatch(r'cs_test_[a-zA-Z0-9]+', str(body.get('id', ''))):
                raise Fel('stripe_svar_ar_inte_testsession', 502)
            u = urllib.parse.urlsplit(body.get('url', ''))
            if u.scheme != 'https' or u.netloc != 'checkout.stripe.com' or u.username:
                raise Fel('stripe_svar_saknar_hostad_checkout', 502)
            return {'provider_id': body['id'], 'url': body['url'], 'status': 'checkout_created',
                    'paid': False, 'reference': key, 'livemode': False}
        return self.post('https://api.stripe.com', '/v1/checkout/sessions', payload, key, validate,
                         retry=retry, form=True, extra=self.headers)

    def readback(self, receipt):
        id_ = receipt.get('provider_id', '')
        if not isinstance(id_, str) or not re.fullmatch(r'cs_test_[a-zA-Z0-9]+', id_):
            raise Fel('ogiltig_testsession')
        text(receipt.get('reference'), 'idempotens', 500)
        body = self.get('https://api.stripe.com/v1/checkout/sessions/' + id_, self.headers)
        if body.get('id') != id_ or body.get('livemode') is not False or body.get('client_reference_id') != receipt['reference'] or body.get('mode') != 'payment':
            raise Fel('stripe_aterlasning_fel_identitet', 502)
        return dict(receipt, status=body.get('status'), payment_status=body.get('payment_status'),
                    paid=body.get('payment_status') == 'paid', funds_are_real=False)


def cal_readback(key, uid, version, transport=None):
    """Återläs leverantörsbokning. UID behandlas som hemlighet, skrivs inte i kvitto.

    Standardbokning/ombokning/avbokning görs i Cal:s egen UI. Ingen egen lager-
    eller platshållningsmodell. Sittplats-/gruppbokning kräver eget behovsprov.
    """
    if not re.fullmatch(r'[a-zA-Z0-9_-]{4,100}', uid) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', version):
        raise Fel('ogiltig_cal_bindning')
    body = API(key, None, 'cal', transport).get('https://api.cal.com/v2/bookings/' + uid,
                                             {'cal-api-version': version})
    data = body.get('data', {})
    if body.get('status') != 'success' or data.get('uid') != uid:
        raise Fel('cal_aterlasning_fel_identitet', 502)
    return {'provider': 'cal', 'uid_sha256': hashlib.sha256(uid.encode()).hexdigest(),
            'status': data.get('status'), 'start': data.get('start'), 'end': data.get('end'),
            'niva': 'kontraktsprov' if transport else 'leverantors_api',
            'confirmation_delivered': None, 'calendar_written': None}
