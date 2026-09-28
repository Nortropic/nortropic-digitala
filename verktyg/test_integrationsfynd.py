"""Riktade beteendeprov efter separat kodgranskning; ingen nätåtkomst."""
import contextlib
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import integrationer as cli
from integrationer_adapter import Journal, ResendTest
import test_fortsatt as tf


class Integrationsutfall(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.key = self.root/'key'; self.key.write_text('synthetic-not-a-real-key'); self.key.chmod(0o600)
        self.args = ['resend-test','--nyckel-fil',str(self.key),'--konto','synthetic',
                     '--journal',str(self.root/'journal.sqlite'),'--idempotens','synthetic-1',
                     '--aterlas','--ut',str(self.root/'receipt.json')]

    def test_bounced_readback_reports_outcome_without_generic_success(self):
        def transport(method, url, headers, body):
            if method == 'POST': return 200, {'id':'12345678-1234-1234-1234-123456789abc'}, {}
            return 200, {'id':'12345678-1234-1234-1234-123456789abc','to':['delivered@resend.dev'],
                         'from':'Nortropic systemprov <onboarding@resend.dev>','last_event':'bounced'}, {}
        def factory(key, journal, account): return ResendTest(key, journal, account, transport)
        out=io.StringIO()
        with patch.object(cli,'ResendTest',factory),contextlib.redirect_stdout(out):
            self.assertEqual(cli.main(self.args),0)
        summary=json.loads(out.getvalue()); receipt=json.loads((self.root/'receipt.json').read_text())
        for d in [summary,receipt]:
            self.assertTrue(d['anrop_genomfort']);self.assertEqual(d['utfall_status'],'bounced_test');self.assertNotIn('klart',d)
        self.assertFalse(receipt['livekunddrift_verifierad'])

    def test_actual_locked_journal_is_named_and_makes_no_provider_call(self):
        Journal(self.root/'journal.sqlite')
        lock=sqlite3.connect(self.root/'journal.sqlite');lock.execute('BEGIN EXCLUSIVE')
        out=io.StringIO()
        try:
            with patch('integrationer_adapter.http') as network,contextlib.redirect_stdout(out):
                self.assertEqual(cli.main(self.args),1);network.assert_not_called()
        finally: lock.rollback();lock.close()
        receipt=json.loads((self.root/'receipt.json').read_text())
        self.assertFalse(receipt['anrop_genomfort']);self.assertIsNone(receipt['utfall_status'])
        self.assertEqual(receipt['fel'],'journal_eller_mottagning_otillganglig')


class Integrationsval(unittest.TestCase):
    def test_changed_customer_choice_reopens_brief_and_build_with_history(self):
        fixture=tf.Vagen();fixture.setUp();self.addCleanup(fixture.tearDown)
        tf.bestallning(fixture.k)
        tf.kor('--kund',str(fixture.k),'--fall',fixture.f);fixture.klar('uppstart')
        fixture.fram_till('beredning','intervju','research')
        _,started=tf.kor('--fall',fixture.f);self.assertEqual(started['nasta'],'brief')
        choice=fixture.k/'INTEGRATIONSVAL.json';choice.write_text(json.dumps({'schema':'digitala-integrationsval/1','val':[]}))
        fixture.klar('brief');fixture.fram_till('koncept')
        _,built=tf.kor('--fall',fixture.f);self.assertEqual(built['nasta'],'bygge')
        loading=json.loads((Path(built['arbetsyta'])/'LADDNING.json').read_text())
        row=next(x for x in loading['underlag'] if x['fil']=='INTEGRATIONSVAL.json')
        self.assertEqual(row['status'],'laddad');self.assertEqual((Path(built['arbetsyta'])/row['plats']).read_bytes(),choice.read_bytes())
        choice.write_text(json.dumps({'schema':'digitala-integrationsval/1','val':[],'motivering':'Ändrat faktiskt kundval'}))
        _,now=tf.kor('--fall',fixture.f);self.assertEqual(now['nasta'],'brief')
        import fortsatt
        state=fortsatt.las(fixture.f)
        self.assertNotEqual(state['steg']['bygge']['status'],'påbörjat')
        self.assertTrue(state['steg']['brief']['historik'])
        self.assertIn('INTEGRATIONSVAL.json',state['steg']['brief']['historik'][-1]['skal'])


if __name__=='__main__':unittest.main()
