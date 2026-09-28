"""Journalfel efter nätutfall och GET från bevarade kvitton; ingen leverantörstrafik."""
import contextlib
import hashlib
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import integrationer as cli
from integrationer_adapter import Fel, Journal, JournalfelEfterAnrop, ResendTest, StripeTest


ID = '12345678-1234-1234-1234-123456789abc'


class Aterhamtning(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.key = self.root / 'key'
        self.key.write_text('synthetic-not-a-real-key')
        self.key.chmod(0o600)
        self.db = self.root / 'journal.sqlite'
        self.calls = []

    def transport(self, method, url, headers, body):
        self.calls.append(method)
        if method == 'POST':
            return 200, {'id': ID}, {}
        return 200, {'id': ID, 'to': ['delivered@resend.dev'],
                     'from': 'Nortropic systemprov <onboarding@resend.dev>', 'last_event': 'delivered'}, {}

    def args(self, command='resend-test', out='receipt.json'):
        args = [command, '--nyckel-fil', str(self.key), '--konto', 'synthetic', '--ut', str(self.root / out)]
        if command == 'resend-test':
            args += ['--journal', str(self.db), '--idempotens', 'synthetic-1', '--aterlas']
        else:
            args += ['--kvitto', str(self.root / 'receipt.json')]
        return args

    def factory(self, key, journal, account):
        return ResendTest(key, journal, account, self.transport)

    def test_actual_commit_lock_preserves_acceptance_and_fresh_get_without_post(self):
        Journal(self.db)
        lock = sqlite3.connect(self.db)
        self.addCleanup(lock.close)
        base_transport = self.transport
        def transport(method, *args):
            result = base_transport(method, *args)
            if method == 'POST':
                lock.execute('BEGIN EXCLUSIVE')
            return result
        def factory(key, journal, account):
            return ResendTest(key, journal, account, transport)
        with patch.object(cli, 'ResendTest', factory), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(self.args()), 1)
        lock.rollback()
        original = (self.root / 'receipt.json').read_bytes()
        receipt = json.loads(original)
        self.assertEqual(receipt['schema'], 'digitala-integrationsprov/2')
        self.assertEqual(receipt['fel'], 'journalfel_efter_accepterat_anrop')
        self.assertEqual(receipt['accepterat']['provider_id'], ID)
        self.assertTrue(receipt['anrop_genomfort'])
        self.assertEqual(receipt['utfall_status'], 'delivered_test')
        self.assertFalse(receipt['journal_avstamd'])
        self.assertEqual(self.calls, ['POST', 'GET'])
        with sqlite3.connect(self.db) as db:
            self.assertEqual(db.execute('SELECT state FROM operation').fetchone()[0], 'in_flight')
        with self.assertRaisesRegex(Fel, 'anrop_pagar'):
            self.factory('synthetic', Journal(self.db), 'synthetic').send('synthetic-1', retry=True)
        # Ny CLI-körning behöver varken åtkomlig journal eller nytt POST-anrop.
        with patch.object(cli, 'ResendTest', self.factory), patch.object(cli, 'Journal', side_effect=AssertionError('no journal in GET')):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(self.args('resend-aterlas', 'readback.json')), 0)
        readback = json.loads((self.root / 'readback.json').read_text())
        self.assertEqual(self.calls, ['POST', 'GET', 'GET'])
        self.assertEqual(readback['utfall_status'], 'delivered_test')
        self.assertEqual(readback['kallkvitto_sha256'], hashlib.sha256(original).hexdigest())
        self.assertFalse(readback['journal_avstamd'])
        self.assertEqual((self.root / 'receipt.json').read_bytes(), original)

    def test_acceptance_and_journal_error_survive_failed_readback(self):
        def transport(method, *args):
            if method == 'GET':
                self.calls.append(method)
                raise TimeoutError()
            return self.transport(method, *args)
        def factory(key, journal, account):
            return ResendTest(key, journal, account, transport)
        with patch.object(Journal, 'finish', side_effect=sqlite3.OperationalError('synthetic')):
            with patch.object(cli, 'ResendTest', factory), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(self.args()), 1)
        receipt = json.loads((self.root / 'receipt.json').read_text())
        self.assertEqual(receipt['fel'], 'journalfel_efter_accepterat_anrop')
        self.assertEqual(receipt['aterlasningsfel'], 'aterlasning_misslyckades')
        self.assertEqual(receipt['accepterat']['provider_id'], ID)
        self.assertEqual(receipt['utfall_status'], 'provider_accepted')
        self.assertTrue(receipt['anrop_genomfort'])
        self.assertEqual(self.calls, ['POST', 'GET'])

    def test_transport_unknown_and_second_journal_failure_remain_distinct(self):
        api = ResendTest('synthetic', Journal(self.db), 'synthetic', lambda *args: (_ for _ in ()).throw(TimeoutError()))
        with patch.object(Journal, 'finish', side_effect=sqlite3.OperationalError('synthetic')):
            with self.assertRaises(JournalfelEfterAnrop) as error:
                api.send('lost')
        self.assertIsNone(error.exception.accepted)
        self.assertEqual(error.exception.original_error, 'transportutfall_okant')
        with self.assertRaisesRegex(Fel, 'anrop_pagar'):
            api.send('lost', retry=True)

    def test_old_schema_is_read_without_rewriting_or_claiming_old_success_flag(self):
        legacy = {'schema': 'digitala-integrationsprov/1', 'kommando': 'resend-test',
                  'kontoetikett': 'synthetic', 'niva': 'kontraktsprov', 'klart': False,
                  'accepterat': {'provider_id': ID, 'recipient': 'delivered@resend.dev', 'niva': 'kontraktsprov'}}
        path = self.root / 'receipt.json'
        path.write_text(json.dumps(legacy)); path.chmod(0o600)
        original = path.read_bytes()
        with patch.object(cli, 'ResendTest', self.factory), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(self.args('resend-aterlas', 'readback.json')), 0)
        self.assertEqual(self.calls, ['GET'])
        self.assertEqual(path.read_bytes(), original)
        self.assertNotIn('klart', json.loads((self.root / 'readback.json').read_text()))

    def test_wrong_receipt_binding_and_malformed_identity_reject_before_network(self):
        good = {'schema': 'digitala-integrationsprov/2', 'kommando': 'resend-test',
                'kontoetikett': 'synthetic', 'niva': 'kontraktsprov',
                'accepterat': {'provider_id': ID, 'recipient': 'delivered@resend.dev', 'niva': 'kontraktsprov'}}
        changes = [{'kontoetikett': 'other'}, {'kommando': 'stripe-checkout-test'}, {'schema': 'unknown'},
                   {'niva': 'leverantors_api'}, {'accepterat': dict(good['accepterat'], provider_id=5)},
                   {'accepterat': dict(good['accepterat'], recipient='human@example.invalid')}]
        for i, change in enumerate(changes):
            with self.subTest(change=change):
                path = self.root / 'receipt.json'
                path.write_text(json.dumps(dict(good, **change))); path.chmod(0o600)
                with patch.object(cli, 'ResendTest', self.factory), contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(cli.main(self.args('resend-aterlas', 'bad%d.json' % i)), 1)
        self.assertEqual(self.calls, [])

    def test_stripe_acceptance_failure_can_readback_unpaid_without_new_session(self):
        self.key.write_text('sk_test_synthetic')
        def transport(method, url, headers, body):
            self.calls.append(method)
            if '/prices/' in url:
                return 200, {'id': 'price_test1', 'livemode': False, 'active': True, 'type': 'one_time', 'unit_amount': 5000}, {}
            if method == 'POST':
                return 200, {'id': 'cs_test_abc', 'livemode': False, 'url': 'https://checkout.stripe.com/c/pay/cs_test_abc'}, {}
            return 200, {'id': 'cs_test_abc', 'livemode': False, 'mode': 'payment', 'client_reference_id': 'synthetic-1',
                         'status': 'complete', 'payment_status': 'unpaid'}, {}
        def factory(key, journal, account, version):
            return StripeTest(key, journal, account, version, transport)
        args = self.args()
        args[0] = 'stripe-checkout-test'; args.remove('--aterlas')
        args += ['--pris', 'price_test1', '--version', '2025-08-27.basil',
                 '--success-url', 'https://example.invalid/ok', '--cancel-url', 'https://example.invalid/cancel']
        with patch.object(cli, 'StripeTest', factory), patch.object(Journal, 'finish', side_effect=sqlite3.OperationalError('synthetic')):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(args), 1)
        receipt = json.loads((self.root / 'receipt.json').read_text())
        self.assertEqual(receipt['fel'], 'journalfel_efter_accepterat_anrop')
        self.assertEqual(receipt['utfall_status'], 'unpaid')
        self.assertFalse(receipt['resultat']['paid'])
        args = self.args('stripe-aterlas-test', 'readback.json') + ['--version', '2025-08-27.basil']
        with patch.object(cli, 'StripeTest', factory), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(args), 0)
        self.assertEqual(self.calls, ['GET', 'POST', 'GET', 'GET'])
        args[args.index('--version') + 1] = '2024-01-01'
        args[args.index('--ut') + 1] = str(self.root / 'bad-version.json')
        with patch.object(cli, 'StripeTest', factory), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(args), 1)
        self.assertEqual(self.calls, ['GET', 'POST', 'GET', 'GET'])


if __name__ == '__main__':
    unittest.main()
