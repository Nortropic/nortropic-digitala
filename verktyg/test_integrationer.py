import base64
import hashlib
import hmac
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch

import integrationer as cli
from integrationer_adapter import Fel, Journal, ResendTest, StripeTest, cal_readback, http, json_bytes, privat_fil
from integrationer_mottagning import Inkorg, webhook, las_json


class Integrationer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.clock = [1000000.]
        self.journal = Journal(self.root / 'journal.sqlite', now=lambda: self.clock[0])
        self.inbox = Inkorg(self.root / 'inbox.sqlite')
        self.calls = []

    def resend_transport(self, method, url, headers, body):
        self.calls.append((method, url, headers, body))
        if method == 'POST':
            return 200, {'id': '12345678-1234-1234-1234-123456789abc'}, {}
        return 200, {'id': '12345678-1234-1234-1234-123456789abc', 'to': ['delivered@resend.dev'],
                     'from': 'Nortropic systemprov <onboarding@resend.dev>', 'last_event': 'delivered'}, {}

    def api(self, transport=None):
        return ResendTest('not-a-real-key', self.journal, 'eget-prov', transport or self.resend_transport)

    def test_resend_acceptance_is_not_delivery_and_duplicate_persists(self):
        receipt = self.api().send('id1')
        self.assertEqual(receipt['status'], 'provider_accepted')
        fresh = ResendTest('not-a-real-key', Journal(self.journal.path), 'eget-prov', self.resend_transport)
        self.assertTrue(fresh.send('id1')['duplicate'])
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(fresh.readback(receipt)['status'], 'delivered_test')
        self.assertFalse(fresh.readback(receipt)['received_by_person'])
        self.assertEqual(receipt['niva'], 'kontraktsprov')

    def test_no_human_email_or_changed_idempotency(self):
        for recipient in ['someone@example.com', 'delivered@resend.dev.evil', 'delivered\n@resend.dev']:
            with self.assertRaises(Fel):
                self.api().send('a', recipient)
        self.api().send('a')
        with self.assertRaisesRegex(Fel, 'samma_nyckel'):
            self.api().send('a', 'bounced@resend.dev')
        self.assertEqual(len(self.calls), 1)

    def test_lost_ack_needs_explicit_retry_same_bytes(self):
        accepted = []
        def transport(method, url, headers, body):
            accepted.append((headers['Idempotency-Key'], body))
            if len(accepted) == 1:
                raise TimeoutError('provider accepted but response lost')
            return self.resend_transport(method, url, headers, body)
        api = self.api(transport)
        with self.assertRaisesRegex(Fel, 'transportutfall_okant'):
            api.send('lost')
        with self.assertRaisesRegex(Fel, 'explicit_retry'):
            api.send('lost')
        result = api.send('lost', retry=True)
        self.assertEqual(result['status'], 'provider_accepted')
        self.assertEqual(accepted[0], accepted[1])

    def test_old_unknown_never_reposted(self):
        def lost(*args):
            raise TimeoutError()
        api = self.api(lost)
        with self.assertRaises(Fel):
            api.send('late')
        self.clock[0] += 23 * 3600
        with self.assertRaisesRegex(Fel, 'manuell_avstamning'):
            api.send('late', retry=True)

    def test_lease_blocks_concurrent_send(self):
        self.journal.begin('lease', 'fp')
        with self.assertRaisesRegex(Fel, 'pagar'):
            self.journal.begin('lease', 'fp', retry=True)

    def test_rate_limit_retry_after_and_rejection_no_success(self):
        def rate(*args):
            return 429, {'secret': 'do-not-preserve'}, {'Retry-After': '20'}
        api = self.api(rate)
        with self.assertRaisesRegex(Fel, '429'):
            api.send('rate')
        with self.assertRaisesRegex(Fel, 'retry_after'):
            api.send('rate', retry=True)
        self.clock[0] += 21
        self.assertEqual(self.api().send('rate', retry=True)['status'], 'provider_accepted')

    def test_malformed_success_remains_unknown(self):
        api = self.api(lambda *args: (200, {'ok': True}, {}))
        with self.assertRaisesRegex(Fel, 'saknar_id'):
            api.send('bad')
        with self.assertRaisesRegex(Fel, 'explicit_retry'):
            api.send('bad')

    def test_readback_identity_must_match(self):
        receipt = self.api().send('read')
        with self.assertRaisesRegex(Fel, 'fel_identitet'):
            self.api(lambda *a: (200, {'id': receipt['provider_id'], 'to': ['wrong@example.invalid']}, {})).readback(receipt)

    def test_http_origin_guard_and_no_redirect_handler(self):
        for url in ['http://api.resend.com/emails', 'https://api.resend.com.evil/emails',
                    'https://secret@api.resend.com/emails', 'https://api.resend.com:444/emails']:
            with self.assertRaisesRegex(Fel, 'origin'):
                http('POST', url, {}, b'{}')
        from integrationer_adapter import IngenRedirect
        self.assertIsNone(IngenRedirect().redirect_request(None, None, 302, None, None, 'https://evil.invalid'))

    def test_stripe_hosted_checkout_contract_and_unpaid_complete(self):
        calls = []
        def transport(method, url, headers, body):
            calls.append((method, url, headers, body))
            if '/prices/' in url:
                return 200, {'id': 'price_test1', 'livemode': False, 'active': True, 'type': 'one_time', 'unit_amount': 5000}, {}
            if method == 'POST':
                return 200, {'id': 'cs_test_abc', 'livemode': False, 'url': 'https://checkout.stripe.com/c/pay/cs_test_abc'}, {}
            return 200, {'id': 'cs_test_abc', 'livemode': False, 'mode': 'payment', 'client_reference_id': 'test-order',
                         'status': 'complete', 'payment_status': 'unpaid'}, {}
        api = StripeTest('sk_test_fixture', self.journal, 'synthetic', '2025-08-27.basil', transport)
        r = api.checkout('test-order', 'price_test1', 'https://example.invalid/thanks', 'https://example.invalid/cancel')
        self.assertFalse(r['paid'])
        self.assertFalse(api.readback(r)['paid'])
        self.assertIn(b'line_items%5B0%5D%5Bprice%5D=price_test1', calls[1][3])
        self.assertEqual(calls[1][2]['Idempotency-Key'], 'test-order')

    def test_stripe_live_key_and_live_price_denied(self):
        with self.assertRaises(Fel):
            StripeTest('sk_live_notreal', self.journal, 'x', '2025-08-27.basil')
        api = StripeTest('sk_test_notreal', self.journal, 'x', '2025-08-27.basil', lambda *a: (200, {'id': 'price_1', 'livemode': True}, {}))
        with self.assertRaisesRegex(Fel, 'testpris'):
            api.checkout('x', 'price_1', 'https://example.invalid/ok', 'https://example.invalid/cancel')

    def test_swish_sek_fore_post_och_betalsatt_aterlast(self):
        calls = []; currency = ['eur']; paid = [True]
        def transport(method, url, headers, body):
            calls.append((method, url, body))
            if '/prices/' in url:
                return 200, {'id': 'price_test1', 'livemode': False, 'active': True, 'type': 'one_time', 'unit_amount': 5000, 'currency': currency[0]}, {}
            if method == 'POST':
                return 200, {'id': 'cs_test_abc', 'livemode': False, 'url': 'https://checkout.stripe.com/c/pay/cs_test_abc'}, {}
            if '/payment_intents/' in url:
                return 200, {'id': 'pi_abc', 'livemode': False, 'status': 'succeeded', 'latest_charge': {
                    'id': 'ch_abc', 'payment_intent': 'pi_abc', 'livemode': False, 'paid': True,
                    'payment_method_details': {'type': 'swish'}}}, {}
            return 200, {'id': 'cs_test_abc', 'livemode': False, 'mode': 'payment', 'client_reference_id': 'swish-test',
                         'status': 'complete' if paid[0] else 'open', 'payment_status': 'paid' if paid[0] else 'unpaid',
                         'payment_method_types': ['card', 'swish'], 'payment_intent': 'pi_abc'}, {}
        api = StripeTest('sk_test_fixture', self.journal, 'synthetic', '2025-08-27.basil', transport)
        with self.assertRaisesRegex(Fel, 'swish_kraver_sek'):
            api.checkout('swish-test', 'price_test1', 'https://example.invalid/ok', 'https://example.invalid/cancel', payment_method='swish')
        self.assertEqual([x[0] for x in calls], ['GET'])
        currency[0] = 'sek'
        receipt = api.checkout('swish-test', 'price_test1', 'https://example.invalid/ok', 'https://example.invalid/cancel', payment_method='swish')
        self.assertIn(b'payment_method_types%5B0%5D=swish', calls[-1][2])
        r = api.readback(receipt)
        self.assertEqual(r['payment_method_types'], ['card', 'swish']); self.assertEqual(r['payment_method_used'], 'swish')
        self.assertTrue(r['paid']); self.assertEqual(r['payment_method_observation'], 'MATT')
        paid[0] = False; before = len(calls); r = api.readback(receipt)
        self.assertFalse(r['paid']); self.assertIsNone(r['payment_method_used']); self.assertEqual(len(calls), before + 1)

    def test_swish_belopp_och_fel_livemode_i_betalsattsbevis_vagras(self):
        calls = []
        def transport(method, url, headers, body):
            calls.append(method)
            if '/prices/' in url:
                return 200, {'id': 'price_test1', 'livemode': False, 'active': True, 'type': 'one_time', 'unit_amount': 200, 'currency': 'sek'}, {}
            if '/payment_intents/' in url:
                return 200, {'id': 'pi_abc', 'livemode': True}, {}
            return 200, {'id': 'cs_test_abc', 'livemode': False, 'mode': 'payment', 'client_reference_id': 'x', 'payment_status': 'paid', 'payment_intent': 'pi_abc'}, {}
        api = StripeTest('sk_test_fixture', self.journal, 'synthetic', '2025-08-27.basil', transport)
        with self.assertRaisesRegex(Fel, 'swish_belopp'):
            api.checkout('x', 'price_test1', 'https://example.invalid/ok', 'https://example.invalid/cancel', payment_method='swish')
        with self.assertRaisesRegex(Fel, 'fel_identitet'):
            api.readback({'provider_id': 'cs_test_abc', 'reference': 'x'})
        self.assertEqual(set(calls), {'GET'})

    def test_cal_readback_redacts_capability_uid(self):
        r = cal_readback('key', 'private-booking-uid', '2024-08-13', lambda *a: (200, {'status': 'success', 'data': {'uid': 'private-booking-uid', 'status': 'accepted', 'start': 'x', 'end': 'y'}}, {}))
        self.assertNotIn('private-booking-uid', json.dumps(r))
        self.assertIsNone(r['calendar_written'])

    def signed(self, provider, event, config, timestamp=1000000):
        raw = json_bytes(event)
        signature = hmac.new(config['secret'].encode(), raw, hashlib.sha256)
        headers = {'x-cal-webhook-version': '2021-10-20'}
        if provider == 'stripe':
            signature = hmac.new(config['secret'].encode(), str(timestamp).encode() + b'.' + raw, hashlib.sha256)
            headers['stripe-signature'] = 't=' + str(timestamp) + ',v1=' + signature.hexdigest()
        else:
            headers['x-cal-signature-256' if provider == 'cal' else 'tally-signature'] = signature.hexdigest() if provider == 'cal' else base64.b64encode(signature.digest()).decode()
        return raw, headers

    def test_stripe_signed_event_duplicate_out_of_order_not_current_state(self):
        config = {'secret': 'only-local-test-secret', 'api_version': '2025-08-27.basil', 'reference_prefix': 'test-'}
        event = {'id': 'evt_1', 'type': 'checkout.session.completed', 'created': 1000000, 'livemode': False,
                 'api_version': config['api_version'], 'data': {'object': {'object': 'checkout.session', 'id': 'cs_test_1', 'livemode': False, 'client_reference_id': 'test-a', 'payment_status': 'unpaid'}}}
        raw, heads = self.signed('stripe', event, config)
        value = webhook('stripe', raw, heads, config, now=1000000)
        self.assertFalse(value['paid_test_observation'])
        self.assertFalse(self.inbox.receive(value)['duplicate'])
        self.assertTrue(self.inbox.receive(value)['duplicate'])
        with self.assertRaisesRegex(Fel, 'andrat_innehall'):
            self.inbox.receive(dict(value, payment_status='paid'))
        self.assertFalse(value['latest_status_verified'])
        self.assertFalse(value['fulfilment_performed'])

    def test_stripe_forgery_stale_live_and_wrong_scope(self):
        cfg = {'secret': 'only-local-test-secret', 'api_version': 'v', 'reference_prefix': 'test-'}
        ev = {'id': 'evt', 'type': 'checkout.session.completed', 'livemode': True}
        raw, heads = self.signed('stripe', ev, cfg)
        with self.assertRaisesRegex(Fel, 'scope'):
            webhook('stripe', raw, heads, cfg, now=1000000)
        with self.assertRaisesRegex(Fel, 'gammal'):
            webhook('stripe', raw, heads, cfg, now=1000301)
        with self.assertRaisesRegex(Fel, 'signatur'):
            webhook('stripe', raw + b' ', heads, cfg, now=1000000)

    def test_cal_signed_lifecycle_version_scope_and_seats_not_inferred(self):
        cfg = {'secret': 'only-local-test-secret', 'event_type_id': 123, 'version': '2021-10-20'}
        for kind in ['BOOKING_CREATED', 'BOOKING_RESCHEDULED', 'BOOKING_CANCELLED']:
            ev = {'triggerEvent': kind, 'createdAt': '2026-09-28T10:00:00Z',
                  'payload': {'uid': 'secret-booking-uid', 'eventTypeId': 123, 'status': 'ACCEPTED', 'seatsPerTimeSlot': 6}}
            raw, heads = self.signed('cal', ev, cfg)
            value = webhook('cal', raw, heads, cfg)
            self.assertFalse(value['seat_or_resource_capacity_verified'])
            self.assertNotIn('secret-booking-uid', json.dumps(value))
            self.inbox.receive(value)
            with self.assertRaisesRegex(Fel, 'version'):
                webhook('cal', raw, dict(heads, **{'x-cal-webhook-version': '2026-07-27'}), cfg)
            with self.assertRaisesRegex(Fel, 'scope'):
                webhook('cal', raw, heads, dict(cfg, event_type_id=456))

    def tally(self):
        cfg = {'secret': 'only-local-test-secret', 'form_id': 'form1', 'owner': 'Alex', 'follow_up': 'Nästa arbetsdag',
               'fields': {'name': 'q_name', 'email': 'q_email', 'message': 'q_msg'}}
        event = {'eventId': 'evt1', 'eventType': 'FORM_RESPONSE', 'createdAt': '2026-09-28T10:00:00Z',
                 'data': {'formId': 'form1', 'submissionId': 'sub1', 'submissionPdfUrl': 'https://secret.invalid/token',
                          'fields': [{'key': 'q_name', 'value': '=formula'}, {'key': 'q_email', 'value': 'test@example.invalid'},
                                     {'key': 'q_msg', 'value': 'Syntetiskt prov'}]}}
        return cfg, event

    def test_tally_validated_mapping_dedup_and_crm_export(self):
        cfg, event = self.tally()
        raw, heads = self.signed('tally', event, cfg)
        value = webhook('tally', raw, heads, cfg)
        self.assertNotIn('secret.invalid', json.dumps(value))
        self.assertFalse(self.inbox.receive(value)['duplicate'])
        self.assertTrue(self.inbox.receive(dict(value, id='new-delivery'))['duplicate'])
        exported = self.inbox.export_crm()
        self.assertIn("'=formula", exported)
        self.assertIn('Alex', exported)
        self.assertEqual(len(exported.splitlines()), 2)

    def test_tally_wrong_form_signature_and_invalid_field(self):
        cfg, ev = self.tally()
        raw, heads = self.signed('tally', ev, cfg)
        with self.assertRaisesRegex(Fel, 'scope'):
            webhook('tally', raw, heads, dict(cfg, form_id='other'))
        with self.assertRaisesRegex(Fel, 'signatur'):
            webhook('tally', raw + b' ', heads, cfg)
        ev['data']['fields'][1]['value'] = 'not-email'
        raw, heads = self.signed('tally', ev, cfg)
        with self.assertRaisesRegex(Fel, 'epost'):
            webhook('tally', raw, heads, cfg)

    def test_json_null_duplicate_and_nonfinite_refused(self):
        for raw in (b'null', b'{"a":1,"a":2}', b'{"a":NaN}', b'{'):
            with self.assertRaises(Fel):
                las_json(raw)

    def test_private_paths_and_no_overwrite(self):
        private = self.root / 'p'
        private.write_text('x'); private.chmod(0o644)
        with self.assertRaises(Fel):
            privat_fil(private)
        private.chmod(0o600)
        symlink = self.root / 'link'; symlink.symlink_to(private)
        with self.assertRaises(Fel):
            privat_fil(symlink)
        cli.skriv_json(self.root / 'out.json', {'a': 1})
        with self.assertRaises(FileExistsError):
            cli.skriv_json(self.root / 'out.json', {'a': 2})

    def test_notification_is_bound_to_saved_form_and_correct_owner(self):
        with self.assertRaisesRegex(Fel, 'saknas'):
            self.inbox.lead_ref('new', 'Alex')
        self.inbox.lead('new', {'name': 'Demo', 'email': 'test@example.invalid', 'message': 'Prov'}, 'Alex', 'Nästa arbetsdag')
        with self.assertRaisesRegex(Fel, 'saknas'):
            self.inbox.lead_ref('new', 'Other')
        receipt = self.inbox.lead_ref('new', 'Alex')
        self.api().send('bound', reference=receipt['reference'])
        self.assertNotIn(b'test@example.invalid', self.calls[0][3])
        self.assertIn(receipt['reference'].encode(), self.calls[0][3])
        with self.assertRaisesRegex(Fel, 'samma_nyckel'):
            self.api().send('bound', reference='a' * 64)

    def test_signed_but_malformed_snapshot_returns_validation_error(self):
        cfg = {'secret': 'only-local-test-secret', 'api_version': 'v', 'reference_prefix': 'test-'}
        event = {'id': 'evt_1', 'type': 'checkout.session.completed', 'livemode': False, 'data': []}
        raw, heads = self.signed('stripe', event, cfg)
        with self.assertRaisesRegex(Fel, 'snapshot_saknas'):
            webhook('stripe', raw, heads, cfg, now=1000000)

    def test_plan_url_escaping_and_provider_scope(self):
        value = json.loads((Path(__file__).parents[1] / 'exempel/integrationer/VAL.json').read_text())
        value['val'][0]['lanktext'] = '<script>bad</script>'
        p = cli.plan(value)
        self.assertIn('&lt;script&gt;', p['val'][0]['html'])
        self.assertFalse(p['bokning_betalning_sammankopplad'])
        self.assertEqual(p['externa_anrop'], 0)
        for url in ['https://cal.com.evil/a', 'https://cal.com/a?token=secret', 'javascript:alert(1)']:
            value['val'][0]['url'] = url
            with self.assertRaises(Fel):
                cli.plan(value)

    def test_existing_channel_tool_is_called(self):
        with patch('uppfoljning.main', return_value=0) as tool:
            self.assertEqual(cli.main(['kanal', 'matning', 'utm', '--url', 'https://example.invalid']), 0)
            tool.assert_called_once_with(['utm', '--url', 'https://example.invalid'])

    def test_actual_local_http_form_errors_retry_and_storage(self):
        spec = importlib.util.spec_from_file_location('integrations_example', Path(__file__).parents[1] / 'exempel/integrationer/server.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        server = ThreadingHTTPServer(('127.0.0.1', 0), module.handler(self.inbox, 'Alex', 'Nästa arbetsdag'))
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        self.addCleanup(server.server_close); self.addCleanup(server.shutdown)
        base = 'http://127.0.0.1:' + str(server.server_port)
        def post(raw, origin=base, key='http-id'):
            req = urllib.request.Request(base + '/lead', raw, headers={'Content-Type': 'application/json', 'Origin': origin, 'Idempotency-Key': key})
            try:
                with urllib.request.urlopen(req) as response:
                    return response.status, json.load(response)
            except urllib.error.HTTPError as error:
                return error.code, json.load(error)
        data = {'name': 'Demo', 'email': 'demo@example.invalid', 'message': 'Eget prov'}
        self.assertEqual(post(b'null')[0], 400)
        self.assertEqual(post(json_bytes(data), 'https://evil.invalid')[0], 403)
        self.assertEqual(post(json_bytes(dict(data, email='bad')))[0], 400)
        code, body = post(json_bytes(data)); self.assertEqual(code, 200); self.assertFalse(body['received_by_person'])
        self.assertTrue(post(json_bytes(data))[1]['duplicate'])
        self.assertEqual(post(json_bytes(dict(data, message='changed')))[0], 409)
        # Verklig SQLite-låsning -> server 503; inga mockade HTTP-svar.
        lock = sqlite3.connect(str(self.inbox.path)); lock.execute('BEGIN EXCLUSIVE')
        try:
            self.assertEqual(post(json_bytes(data), key='new-id')[0], 503)
        finally:
            lock.rollback(); lock.close()
        self.assertEqual(post(json_bytes(data), key='new-id')[0], 200)


if __name__ == '__main__':
    unittest.main()
