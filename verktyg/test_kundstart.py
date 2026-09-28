import contextlib
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import intervju as iv  # noqa: E402
import kundstart as ks  # noqa: E402
from test_verksamhetsuppgifter import exempel  # noqa: E402


def paket(revision=7, testdialog=True):
    """Ett syntetiskt exportpaket i formen kundstart-export/1 (samma form som tjänsten ger)."""
    return {
        'schema': 'kundstart-export/1', 'exporterad': '2026-09-27T15:00:00Z',
        'arende': {'id': 'ar_test12345678', 'kund': {'slug': 'kund', 'namn': 'Testfirma'}, 'kanal': 'Kundstart-länk (TESTDIALOG)', 'testdialog': testdialog, 'skapad': '2026-09-27T14:00:00Z', 'revision': revision, 'inlamningar': [{'tid': '2026-09-27T14:50:00Z', 'revision': revision, 'svar': 2, 'material': 1}]},
        'bank': {'sha256': 'x', 'git_rev': 'y'}, 'ai': {'lage': 'regelstyrd', 'anrop': 0},
        'fakta_forifyllda': [],
        'omgangar': [
            {'nr': 1, 'skapad': '2026-09-27T14:01:00Z', 'fragor': [{'id': 'A1', 'omrade': 'A', 'nyckel': 'verksamhetsmal', 'text': 'Vad vill ni att webbplatsen ska förändra?', 'paverkar': 'mål', 'utlost_av': None, 'valjare': 'ai', 'banktext': 'Vad vill ni att webbplatsen ska förändra för verksamheten det närmaste året? Ge gärna ett konkret exempel på ett bra utfall.'}],
             'svar': [{'fraga_id': 'A1', 'nyckel': 'verksamhetsmal', 'omrade': 'A', 'text': 'Vi vill att kunder ska boka tid direkt på hemsidan.', 'typ': 'text', 'mottaget': '2026-09-27T14:02:00Z', 'revision': 3, 'idempotens': 'k1'}], 'svar_md': '### A1\nVi vill att kunder ska boka tid direkt på hemsidan.\n'},
            {'nr': 2, 'skapad': '2026-09-27T14:03:00Z', 'fragor': [{'id': 'BOK1', 'omrade': 'C', 'nyckel': 'bokning_tjanster', 'text': 'Vilka tjänster ska kunna bokas?', 'paverkar': 'bokning', 'utlost_av': 'A1: "boka tid"', 'valjare': 'regelstyrd'}],
             'svar': [{'fraga_id': 'BOK1', 'nyckel': 'bokning_tjanster', 'omrade': 'C', 'text': 'Vet inte', 'typ': 'vet_inte', 'mottaget': '2026-09-27T14:04:00Z', 'revision': 5, 'idempotens': 'k2'}], 'svar_md': '### BOK1\nVet inte\n'},
        ],
        'svar': [], 'rattelser': [{'nyckel': 'erbjudande', 'varde': 'Trädgårdsskötsel och snöröjning', 'mottaget': '2026-09-27T14:10:00Z', 'revision': 6, 'idempotens': 'k3', 'tidigare': {'varde': 'Trädgårdsskötsel', 'kalla': 'VERKSAMHET.json tjanster', 'typ': 'forifylld'}}],
        'fakta_ai': [{'nyckel': 'verksamhetsmal', 'varde': 'Fler bokningar via webben', 'status': 'tolkning', 'kalla': 'kundstart AI rev 3 (openai/gpt-5-mini)', 'omrade': 'A', 'datum': '2026-09-27'}],
        'rattelser_fakta': [{'nyckel': 'erbjudande', 'varde': 'Trädgårdsskötsel och snöröjning', 'status': 'kunden uppger', 'kalla': 'kundstart rättelse rev 6', 'omrade': 'A', 'datum': '2026-09-27', 'tidigare': {'varde': 'Trädgårdsskötsel', 'kalla': 'VERKSAMHET.json tjanster', 'typ': 'forifylld'}}],
        'material': [{'id': 'm_abc123456789', 'typ': 'fil', 'filnamn': 'logotyp.png', 'mime': 'image/png', 'storlek': 3, 'sha256': hashlib.sha256(b'png').hexdigest(), 'mottaget': '2026-09-27T14:20:00Z', 'revision': 4, 'hamta': 'http://kundstart.test/api/intern/arenden/ar_test12345678/material/m_1'},
                     {'id': 'm_2', 'typ': 'lank', 'url': 'https://exempel.test', 'mottaget': '2026-09-27T14:21:00Z', 'revision': 4}],
        'foljdregler_utlosta': [{'regel': 'bokning', 'fraga_id': 'A1', 'traff': 'boka tid', 'tid': '2026-09-27T14:02:00Z'}], 'handelser': [],
    }


class Kundstart(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.k = Path(self.tmp.name) / 'kund'; self.k.mkdir()
        (self.k / 'VERKSAMHET.json').write_text(json.dumps(exempel(fiktiv=True)))
        # nyckelfilen får inte ligga i /tmp, /etc eller /var/folders (Runtime D034); proven lägger den under hemkatalogen
        self.hem = tempfile.TemporaryDirectory(dir=Path.home(), prefix='.kundstart-prov-')
        self.nyckel = Path(self.hem.name) / 'nyckel.secret'; self.nyckel.write_text('x' * 40); os.chmod(self.nyckel, 0o600)
        os.environ['KUNDSTART_HEMLIGHETER'] = str(Path(self.hem.name) / 'hemligheter')
        import subprocess as _sp  # arbetsträdets läge före provet: 'inget skrivs i repot' jämförs mot detta, inte mot ett tomt träd
        self.smuts_fore = sorted(r for r in _sp.run(['git', '-C', str(HERE.parent), 'status', '--porcelain', '--', 'verktyg', 'kunskap', 'kunder'], capture_output=True, text=True).stdout.splitlines() if 'test_kundstart' not in r and 'kundstart.py' not in r)
        self.anrop = []
        self.svar_pa = {}
        def fejk(bas, nyckel, metod, vag, kropp=None, bypass=None, rå=False):
            self.anrop.append((metod, vag, kropp))
            if rå:
                return b'png'
            return self.svar_pa[(metod, vag.split('?')[0])]
        self._orig = ks.anrop; ks.anrop = fejk

    def tearDown(self):
        ks.anrop = self._orig; self.tmp.cleanup(); self.hem.cleanup(); os.environ.pop('KUNDSTART_HEMLIGHETER', None)

    def kor(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = ks.main(list(args) + ['--bas-url', 'http://kundstart.test', '--nyckel-fil', str(self.nyckel)])
        return code, json.loads(out.getvalue())

    def test_fel_tjanst_vagras_fore_anrop_och_import(self):
        ks.spara_kundstart(self.k, {'schema': 1, 'arende_id': 'ar_test12345678',
                                 'bas_url': 'http://kundstart.test', 'hamtat': [], 'lank_hash': 'a'*64})
        before = (self.k/'KUNDSTART.json').read_bytes()
        for command in ('hamta', 'status', 'lank', 'aterkalla'):
            with self.subTest(command=command), contextlib.redirect_stdout(io.StringIO()) as out:
                code = ks.main([command, '--kund', str(self.k), '--bas-url', 'http://annan.test',
                                '--nyckel-fil', str(self.nyckel)])
            self.assertEqual(code, 2)
            self.assertIn('bas-url', json.loads(out.getvalue())['vagrad'])
            self.assertEqual(self.anrop, [])
            self.assertFalse(iv.stig(self.k).exists())
            self.assertEqual((self.k/'KUNDSTART.json').read_bytes(), before)
        with self.assertRaisesRegex(ks.Vagrad, 'bas-url'):
            ks.hamta(self.k, 'http://annan.test', 'x', None, False, paket=paket())
        ks.bunden(ks.las_kundstart(self.k), 'http://kundstart.test/')

    def test_skapa_skickar_kanda_fakta_med_lasbar_kalla_och_skriver_lanken_0600(self):
        self.svar_pa[('POST', '/api/intern/arenden')] = {'ok': True, 'arende_id': 'ar_test12345678', 'lank': 'http://kundstart.test/start#HEMLIG', 'lank_hash': 'a' * 64, 'utgar': '2026-10-27T00:00:00Z', 'ai': 'regelstyrd'}
        code, r = self.kor('skapa', '--kund', str(self.k), '--namn', 'Testfirma', '--testdialog')
        self.assertEqual(code, 0, r); self.assertEqual(r['arende_id'], 'ar_test12345678'); self.assertNotIn('HEMLIG', json.dumps(r))
        kropp = self.anrop[0][2]
        self.assertTrue(kropp['testdialog']); self.assertEqual(kropp['kund']['namn'], 'Testfirma')
        self.assertTrue(any(f['nyckel'] == 'erbjudande' for f in kropp['fakta']), 'VERKSAMHET.json:s tjänster skickas som kända uppgifter')
        self.assertTrue(all(f['kalla'] == 'det vi redan hade antecknat om er' for f in kropp['fakta']), 'källan är läsbar och sann för kunden')
        lank = Path(os.environ['KUNDSTART_HEMLIGHETER']) / 'kund' / 'KUNDSTART-LANK.secret'
        self.assertEqual(oct(lank.stat().st_mode & 0o777), '0o600'); self.assertIn('HEMLIG', lank.read_text())
        self.assertFalse((self.k / 'KUNDSTART-LANK.secret').exists(), 'länken (en behörighet) ligger inte i kundmappen')
        code2, r2 = self.kor('skapa', '--kund', str(self.k), '--namn', 'Testfirma', '--testdialog')
        self.assertEqual(code2, 0); self.assertIn('finns redan', r2['meddelande']); self.assertEqual(len(self.anrop), 1)

    def test_hamta_for_in_svar_ordagrant_fakta_med_status_och_avgor_bara_tolkningar(self):
        self.svar_pa[('POST', '/api/intern/arenden')] = {'ok': True, 'arende_id': 'ar_test12345678', 'lank': 'http://kundstart.test/start#HEMLIG', 'lank_hash': 'a' * 64, 'utgar': '2026-10-27T00:00:00Z', 'ai': 'regelstyrd'}
        self.kor('skapa', '--kund', str(self.k), '--namn', 'Testfirma', '--testdialog')
        self.svar_pa[('GET', '/api/intern/arenden/ar_test12345678/export')] = paket()
        code, r = self.kor('hamta', '--kund', str(self.k), '--material')
        self.assertEqual(code, 0, r)
        s = iv.las(str(self.k))
        self.assertTrue(s['testdialog']); self.assertEqual(s['kanal'], 'Kundstart-länk (TESTDIALOG)')
        self.assertEqual([o.get('kundstart_omgang') for o in s['omgangar']], [1, 2])
        a1 = next(x for x in s['svar'] if x['fraga_id'] == 'A1')
        self.assertEqual(a1['text'], 'Vi vill att kunder ska boka tid direkt på hemsidan.', 'kundens ord oförändrade')
        self.assertEqual(a1['kalla'], 'kundstart'); self.assertEqual(a1['mottaget'], '2026-09-27T14:02:00Z')
        self.assertTrue(next(x for x in s['svar'] if x['fraga_id'] == 'BOK1').get('vet_inte'))
        self.assertTrue(any(u['regel'] == 'bokning' for u in s['foljdregler_utlosta']), 'intervju.py räknar om följdreglerna själv')
        tolk = [f for f in s['fakta'] if f['status'] == 'tolkning']
        self.assertEqual(len(tolk), 1); self.assertIn('kundstart AI', tolk[0]['kalla'])
        # rättelsen mot VERKSAMHET-faktat (kunden uppger) blir en motsägelse som INTE avgörs automatiskt
        erb = [f for f in s['fakta'] if f['nyckel'] == 'erbjudande']
        self.assertEqual(len(erb), 2)
        mot = [m for m in s['motsagelser'] if m['nyckel'] == 'erbjudande']
        self.assertEqual(len(mot), 1); self.assertEqual(mot[0]['lage'], 'oavgjord', 'kund mot kund avgörs av utföraren, inte tyst')
        self.assertTrue((self.k / 'KUNDSTART' / 'export-rev7.json').is_file())
        fil = self.k / 'KUNDSTART' / 'material' / 'm_abc123456789-logotyp.png'
        self.assertEqual(fil.read_bytes(), b'png')
        code2, r2 = self.kor('hamta', '--kund', str(self.k))
        self.assertEqual(code2, 0); self.assertIn('inget nytt', r2['meddelande'], 'samma revision hämtas inte om')
        self.assertEqual(len(iv.las(str(self.k))['svar']), 2)
        import subprocess
        smuts = subprocess.run(['git', '-C', str(HERE.parent), 'status', '--porcelain', '--', 'verktyg', 'kunskap', 'kunder'], capture_output=True, text=True).stdout
        self.assertEqual(sorted(r for r in smuts.splitlines() if 'test_kundstart' not in r and 'kundstart.py' not in r), self.smuts_fore, 'inget skrivs i repot (jämfört med trädet före provet: ett smutsigt arbetsträd är inte provets fel)')

    def dialogpaket(self, revision=7, bokning='onskat', citat_ok=True):
        p = paket(revision=revision)
        p['kunduppgifter'] = [
            {'id': 'U7_1', 'nyckel': 'verksamhetsmal', 'rubrik': 'Mål', 'avsnitt': 'mal', 'varde': 'boka tid direkt på hemsidan', 'citat': 'boka tid direkt på hemsidan', 'kalla_typ': 'svar', 'kalla_id': 'A1', 'kalla_revision': 3, 'revision': revision, 'omrade': 'A', 'status': 'kunden uppger'},
            {'id': 'U7_2', 'nyckel': 'gruppkapacitet', 'rubrik': 'Grupp', 'avsnitt': 'verksamhet', 'varde': 'hela Norrbotten' if not citat_ok else 'hemsidan', 'citat': 'hela Norrbotten' if not citat_ok else 'hemsidan', 'kalla_typ': 'svar', 'kalla_id': 'A1', 'kalla_revision': 3, 'revision': revision, 'omrade': 'A', 'status': 'kunden uppger'},
        ]
        p['tillval'] = [
            {'id': 'bokning', 'namn': 'Bokning och kalender', 'kundval': bokning, 'kalla': 'kontroll', 'revision': revision, 'historik': [{'kundval': bokning, 'revision': revision}], 'rekommendation': None, 'digitala': None, 'kontroll': None},
            {'id': 'doman', 'namn': 'Egen domän', 'kundval': 'har_system', 'system': 'testfirma.se', 'kalla': 'samtal', 'fraga_id': 'A1', 'citat': 'boka tid', 'revision': 5, 'historik': [{'kundval': 'har_system', 'revision': 5}],
             'kontroll': {'doman': 'testfirma.se', 'tid': '2026-09-28T18:00:00Z', 'registrerad': True, 'kalla_registrering': 'dns', 'dns_leverantor': 'Loopia', 'epost': {'finns': True, 'leverantor': 'Loopia'}, 'webb': {'finns': False, 'varden': None}, 'registrar': None, 'anmarkningar': []}},
            {'id': 'foretagsprofil', 'namn': 'Google-företagsprofil', 'kundval': None, 'revision': 0, 'historik': [], 'rekommendation': {'text': 'Lokala kunder hittar er via kartan.', 'giltig': True}},
        ]
        p['research'] = [{'id': 'R7_1', 'fraga': 'Hur tar liknande verksamheter emot bokningar?', 'varfor': 'Val av bokningsnivå', 'status': 'bestalld'}]
        return p

    def test_tillval_doman_och_citerade_kunduppgifter_foljer_med_till_intaget(self):
        self.svar_pa[('POST', '/api/intern/arenden')] = {'ok': True, 'arende_id': 'ar_test12345678', 'lank': 'http://kundstart.test/start#HEMLIG', 'lank_hash': 'a' * 64, 'utgar': '2026-10-27T00:00:00Z', 'ai': 'claude-cli'}
        self.kor('skapa', '--kund', str(self.k), '--namn', 'Testfirma', '--testdialog')
        p = self.dialogpaket(citat_ok=False)
        self.svar_pa[('GET', '/api/intern/arenden/ar_test12345678/export')] = p
        code, r = self.kor('hamta', '--kund', str(self.k))
        self.assertEqual(code, 0, r)
        s = iv.las(str(self.k))
        rad = lambda n: [f for f in s['fakta'] if f['nyckel'] == n]
        self.assertEqual(rad('tillval_bokning')[0]['status'], 'kunden uppger')
        self.assertIn('Kunden vill ha: Bokning och kalender', rad('tillval_bokning')[0]['varde'])
        self.assertIn('kundstart tillval bokning rev 7 (kontroll)', rad('tillval_bokning')[0]['kalla'])
        self.assertIn('testfirma.se', rad('tillval_doman')[0]['varde']); self.assertIn('kundens ord: "boka tid"', rad('tillval_doman')[0]['varde'])
        self.assertEqual(rad('doman_kontroll')[0]['status'], 'observerat', 'domänkontrollen är en observation, inte kundens ord')
        self.assertIn('e-post på domänen (Loopia)', rad('doman_kontroll')[0]['varde'])
        self.assertEqual(rad('tillval_foretagsprofil'), [], 'en rekommendation blir aldrig kundens val')
        mal = [f for f in rad('verksamhetsmal') if f.get('kalla', '').startswith('kundstart citat')]
        self.assertEqual(len(mal), 1); self.assertEqual(mal[0]['kalla'], 'kundstart citat A1 rev 3')
        self.assertEqual(rad('gruppkapacitet'), [], 'citat som inte står i exportens svar registreras inte')
        self.assertIn('kunduppgift utan ordagrant stöd', r['meddelande'])
        utdrag = ks.intagsutdrag(iv.las(str(self.k)), p)
        for text in ('Kundens tillval (Kundstart', 'Kunden har redan: Egen domän (testfirma.se)', 'Agentens rekommendationer i samtalet (hypoteser', 'Lokala kunder hittar er via kartan', 'Domänkontroll (observerat', 'Beställd avgränsad research från samtalet (inte påbörjad)', 'R7_1: Hur tar liknande'):
            self.assertIn(text, utdrag)
        self.assertNotIn('hela Norrbotten', utdrag, 'obelagd kunduppgift visas inte som kundens ord')

    def test_andrat_tillval_ersatter_det_aldre_synligt_och_upprepas_inte(self):
        self.svar_pa[('POST', '/api/intern/arenden')] = {'ok': True, 'arende_id': 'ar_test12345678', 'lank': 'http://kundstart.test/start#HEMLIG', 'lank_hash': 'a' * 64, 'utgar': '2026-10-27T00:00:00Z', 'ai': 'claude-cli'}
        self.kor('skapa', '--kund', str(self.k), '--namn', 'Testfirma', '--testdialog')
        self.svar_pa[('GET', '/api/intern/arenden/ar_test12345678/export')] = self.dialogpaket(revision=7, bokning='onskat')
        self.assertEqual(self.kor('hamta', '--kund', str(self.k))[0], 0)
        self.svar_pa[('GET', '/api/intern/arenden/ar_test12345678/export')] = self.dialogpaket(revision=9, bokning='inte_nu')
        code, r = self.kor('hamta', '--kund', str(self.k))
        self.assertEqual(code, 0, r)
        s = iv.las(str(self.k))
        mot = [m for m in s['motsagelser'] if m['nyckel'] == 'tillval_bokning']
        self.assertEqual(len(mot), 1); self.assertEqual(mot[0]['lage'], 'avgjord')
        self.assertIn('Inte nu enligt kunden', mot[0]['galler']); self.assertIn('aktuella besked', mot[0]['skal'])
        self.assertIn('Inte nu enligt kunden', iv.aktuella_uppgifter(s)['tillval_bokning']['varde'])
        # En ny revision med samma tillvalsläge (kumulativ export): importen körs på riktigt men dubblerar inte raden.
        p10 = self.dialogpaket(revision=10, bokning='inte_nu')
        for t in p10['tillval']:
            if t['id'] == 'bokning':
                t['revision'] = 9
        self.svar_pa[('GET', '/api/intern/arenden/ar_test12345678/export')] = p10
        code, r = self.kor('hamta', '--kund', str(self.k))
        self.assertEqual(code, 0, r); self.assertNotIn('inget nytt', str(r['meddelande']))
        self.assertEqual(len([f for f in iv.las(str(self.k))['fakta'] if f['nyckel'] == 'tillval_bokning']), 2, 'kumulativ omhämtning dubblerar inte')

    def test_kundens_senare_rattelse_avgor_motsagelsen_mot_ett_aldre_citat(self):
        self.svar_pa[('POST', '/api/intern/arenden')] = {'ok': True, 'arende_id': 'ar_test12345678', 'lank': 'http://kundstart.test/start#HEMLIG', 'lank_hash': 'a' * 64, 'utgar': '2026-10-27T00:00:00Z', 'ai': 'gateway'}
        self.kor('skapa', '--kund', str(self.k), '--namn', 'Testfirma', '--testdialog')
        p = self.dialogpaket(revision=9)
        p['rattelser'] = [{'nyckel': 'verksamhetsmal', 'varde': 'Kunderna ska boka själva dygnet runt', 'mottaget': '2026-09-28T19:00:00Z', 'revision': 9, 'idempotens': 'r9'}]
        p['rattelser_fakta'] = [{'nyckel': 'verksamhetsmal', 'varde': 'Kunderna ska boka själva dygnet runt', 'status': 'kunden uppger', 'kalla': 'kundstart rättelse rev 9', 'omrade': 'A', 'datum': '2026-09-28', 'tidigare': 'boka tid direkt på hemsidan'}]
        self.svar_pa[('GET', '/api/intern/arenden/ar_test12345678/export')] = p
        code, r = self.kor('hamta', '--kund', str(self.k))
        self.assertEqual(code, 0, r)
        s = iv.las(str(self.k))
        mot = [m for m in s['motsagelser'] if m['nyckel'] == 'verksamhetsmal']
        self.assertEqual(len(mot), 1); self.assertEqual(mot[0]['lage'], 'avgjord')
        self.assertEqual(mot[0]['galler'], 'Kunderna ska boka själva dygnet runt'); self.assertIn('kundstart rättelse rev 9', mot[0]['skal'])
        self.assertEqual(iv.aktuella_uppgifter(s)['verksamhetsmal']['varde'], 'Kunderna ska boka själva dygnet runt')

    def test_rattelse_som_inte_kan_beleggas_i_exporten_avgor_ingenting(self):
        # Granskningsfynd 2: revisionen läses ur exportens validerade fält, aldrig ur källtexten.
        self.svar_pa[('POST', '/api/intern/arenden')] = {'ok': True, 'arende_id': 'ar_test12345678', 'lank': 'http://kundstart.test/start#HEMLIG', 'lank_hash': 'a' * 64, 'utgar': '2026-10-27T00:00:00Z', 'ai': 'gateway'}
        self.kor('skapa', '--kund', str(self.k), '--namn', 'Testfirma', '--testdialog')
        p = self.dialogpaket(revision=9)
        p['rattelser_fakta'] = [{'nyckel': 'verksamhetsmal', 'varde': 'Påhittad rättelse', 'status': 'kunden uppger', 'kalla': 'kundstart rättelse rev 999', 'omrade': 'A', 'datum': '2026-09-28'}]
        self.svar_pa[('GET', '/api/intern/arenden/ar_test12345678/export')] = p
        code, r = self.kor('hamta', '--kund', str(self.k))
        self.assertEqual(code, 0, r)
        s = iv.las(str(self.k))
        mot = [m for m in s['motsagelser'] if m['nyckel'] == 'verksamhetsmal']
        self.assertTrue(mot, 'raden registreras som tidigare och möter kundens citat')
        self.assertEqual({m['lage'] for m in mot}, {'oavgjord'}, 'ett besked utan belägg i exportens rattelser-lista avgör ingenting, hur hög revisionen i källtexten än är')
        # Samma påhittade revision genom ett citats källid vägras redan av valideringen (se prov om atomär vägran).

    def test_felformad_export_vagras_atomart_fore_skrivning(self):
        # Granskningsfynd 1 och 2: domänkontrollens fält, citatets källid och reserverade nycklar prövas innan något skrivs.
        self.svar_pa[('POST', '/api/intern/arenden')] = {'ok': True, 'arende_id': 'ar_test12345678', 'lank': 'http://kundstart.test/start#HEMLIG', 'lank_hash': 'a' * 64, 'utgar': '2026-10-27T00:00:00Z', 'ai': 'gateway'}
        self.kor('skapa', '--kund', str(self.k), '--namn', 'Testfirma', '--testdialog')
        def trasig_kontroll(p): p['tillval'][1]['kontroll']['registrerad'] = []
        def trasigt_kallid(p): p['kunduppgifter'][0]['kalla_id'] = 'A1 rev 999'
        def reserverad_rattelse(p): p['rattelser_fakta'].append({'nyckel': 'tillval_bokning', 'varde': 'x', 'status': 'kunden uppger', 'kalla': 'kundstart tillval bokning rev 0 (kontroll)', 'omrade': 'D', 'datum': '2026-09-28'})
        def reserverad_uppgift(p): p['kunduppgifter'][0]['nyckel'] = 'doman_kontroll'
        def radbrytning_i_id(p): p['tillval'][0]['id'] = 'bokning\n'
        for andra in (trasig_kontroll, trasigt_kallid, reserverad_rattelse, reserverad_uppgift, radbrytning_i_id):
            p = self.dialogpaket(revision=9); andra(p)
            self.svar_pa[('GET', '/api/intern/arenden/ar_test12345678/export')] = p
            code, r = self.kor('hamta', '--kund', str(self.k))
            self.assertEqual(code, 2, andra.__name__)
            self.assertIn('fel form', r['vagrad'], andra.__name__)
            self.assertFalse(iv.stig(str(self.k)).is_file(), andra.__name__ + ': inget skrivet i kundmappen')

    def test_tillvalets_aktuella_lage_vinner_oberoende_av_ordning(self):
        self.svar_pa[('POST', '/api/intern/arenden')] = {'ok': True, 'arende_id': 'ar_test12345678', 'lank': 'http://kundstart.test/start#HEMLIG', 'lank_hash': 'a' * 64, 'utgar': '2026-10-27T00:00:00Z', 'ai': 'gateway'}
        self.kor('skapa', '--kund', str(self.k), '--namn', 'Testfirma', '--testdialog')
        self.svar_pa[('GET', '/api/intern/arenden/ar_test12345678/export')] = self.dialogpaket(revision=7, bokning='inte_nu')
        self.assertEqual(self.kor('hamta', '--kund', str(self.k))[0], 0)
        self.svar_pa[('GET', '/api/intern/arenden/ar_test12345678/export')] = self.dialogpaket(revision=9, bokning='onskat')
        self.assertEqual(self.kor('hamta', '--kund', str(self.k))[0], 0)
        s = iv.las(str(self.k))
        self.assertIn('Kunden vill ha: Bokning och kalender', iv.aktuella_uppgifter(s)['tillval_bokning']['varde'], 'exportens aktuella läge gäller')

    def test_tillvalsstatus_skickar_digitalas_status_utan_kundtext(self):
        self.svar_pa[('POST', '/api/intern/arenden')] = {'ok': True, 'arende_id': 'ar_test12345678', 'lank': 'http://kundstart.test/start#HEMLIG', 'lank_hash': 'a' * 64, 'utgar': '2026-10-27T00:00:00Z', 'ai': 'claude-cli'}
        self.kor('skapa', '--kund', str(self.k), '--namn', 'Testfirma', '--testdialog')
        self.svar_pa[('POST', '/api/intern/arenden/ar_test12345678/tillval')] = {'ok': True}
        code, r = self.kor('tillvalsstatus', '--kund', str(self.k), '--utforare', 'digitala/prov', '--tillval', 'bokning', '--status', 'inkluderat', '--kalla', 'INTEGRATIONSVAL.json kundtillval')
        self.assertEqual(code, 0, r)
        metod, vag, kropp = self.anrop[-1]
        self.assertEqual((metod, vag), ('POST', '/api/intern/arenden/ar_test12345678/tillval'))
        self.assertEqual((kropp['tillval'], kropp['status'], kropp['utforare']), ('bokning', 'inkluderat', 'digitala/prov'))
        self.assertTrue(kropp['idempotens'].startswith('TS'))
        self.assertEqual(set(kropp), {'tillval', 'status', 'not', 'kalla', 'utforare', 'idempotens'}, 'ingen kundtext skickas')
        self.kor('tillvalsstatus', '--kund', str(self.k), '--utforare', 'digitala/prov', '--tillval', 'bokning', '--status', 'inkluderat', '--kalla', 'INTEGRATIONSVAL.json kundtillval')
        self.assertEqual(self.anrop[-1][2]['idempotens'], kropp['idempotens'], 'samma besked ger samma idempotensnyckel')
        self.assertEqual(self.kor('tillvalsstatus', '--kund', str(self.k), '--utforare', 'digitala/prov', '--tillval', 'bokning', '--status', 'aktiverat', '--kalla', 'x')[0], 2)

    def test_sen_tolkning_mot_aldre_revision_ateruppstar_inte_over_kundens_rattelse(self):
        self.svar_pa[('POST', '/api/intern/arenden')] = {'ok': True, 'arende_id': 'ar_test12345678', 'lank': 'http://kundstart.test/start#HEMLIG', 'lank_hash': 'a' * 64, 'utgar': '2026-10-27T00:00:00Z', 'ai': 'regelstyrd'}
        self.kor('skapa', '--kund', str(self.k), '--namn', 'Testfirma', '--testdialog')
        p = paket(); p['rattelser'] = []
        p['fakta_ai'] = [{'nyckel': 'ton', 'varde': 'Varm och personlig', 'status': 'tolkning', 'kalla': 'kundstart AI rev 3 (m)', 'omrade': 'E', 'datum': '2026-09-27'}]
        p['rattelser_fakta'] = [{'nyckel': 'ton', 'varde': 'Saklig och rak', 'status': 'kunden uppger', 'kalla': 'kundstart rättelse rev 6', 'omrade': 'E', 'datum': '2026-09-27', 'tidigare': {'varde': 'Varm och personlig', 'kalla': 'kundstart AI rev 3 (m)', 'typ': 'ai'}}]
        self.svar_pa[('GET', '/api/intern/arenden/ar_test12345678/export')] = p
        self.kor('hamta', '--kund', str(self.k))
        # kumulativ omhämtning med högre revision: tjänsten skickar samma (ersatta) tolkning igen, plus en ny tolkning skriven mot rev 4 (< 6)
        p2 = paket(revision=12); p2['rattelser'] = []
        p2['fakta_ai'] = list(p['fakta_ai']) + [{'nyckel': 'ton', 'varde': 'Personlig ton', 'status': 'tolkning', 'kalla': 'kundstart AI rev 4 (m)', 'omrade': 'E', 'datum': '2026-09-27'}]
        p2['rattelser_fakta'] = p['rattelser_fakta']
        self.svar_pa[('GET', '/api/intern/arenden/ar_test12345678/export')] = p2
        code, r = self.kor('hamta', '--kund', str(self.k))
        self.assertEqual(code, 0, r); self.assertIn('FÖRKASTADE TOLKNINGAR', r['meddelande'])
        s = iv.las(str(self.k))
        ton = [f for f in s['fakta'] if f['nyckel'] == 'ton']
        self.assertEqual([(f['varde'], f['status'], bool(f.get('ersatt'))) for f in ton], [('Saklig och rak', 'kunden uppger', False)], 'kundens ord står kvar, ingen tolkning återuppstår')
        # härledd utdata levererar kundens ord, inte tolkningen
        self.assertIn('Saklig och rak', iv.research_md(s)); self.assertFalse(any(f['status']=='tolkning' for f in ton))
        # en rättelse i paketets rattelser-lista med annat värde än speglingen redovisas
        p3 = paket(revision=13); p3['fakta_ai'] = []
        p3['rattelser'] = [{'nyckel': 'erbjudande', 'varde': 'Annat värde', 'mottaget': 't', 'revision': 6, 'idempotens': 'k3', 'tidigare': {'varde': '', 'kalla': '', 'typ': 'ingen'}}]
        self.svar_pa[('GET', '/api/intern/arenden/ar_test12345678/export')] = p3
        code, r = self.kor('hamta', '--kund', str(self.k))
        self.assertEqual(code, 0, r); self.assertIn('utan spegling', r['meddelande'])

    def test_omhamtning_med_hogre_revision_ger_inga_dubbletter_och_andrat_svar_blir_kundens_uppgift(self):
        self.svar_pa[('POST', '/api/intern/arenden')] = {'ok': True, 'arende_id': 'ar_test12345678', 'lank': 'http://kundstart.test/start#HEMLIG', 'lank_hash': 'a' * 64, 'utgar': '2026-10-27T00:00:00Z', 'ai': 'regelstyrd'}
        self.kor('skapa', '--kund', str(self.k), '--namn', 'Testfirma', '--testdialog')
        self.svar_pa[('GET', '/api/intern/arenden/ar_test12345678/export')] = paket(revision=7)
        self.kor('hamta', '--kund', str(self.k))
        p2 = paket(revision=9)
        # samma omgångar och svar igen (idempotens), plus ett ändrat svar på A1 med radbrytningar och en rad som ser ut som en avgränsare
        p2['omgangar'][0]['svar'].append({'fraga_id': 'A1', 'nyckel': 'verksamhetsmal', 'omrade': 'A', 'text': 'Ändrat: vi vill främst få\n### A2\nfler samtal, inte bokningar.', 'typ': 'text', 'mottaget': '2026-09-27T14:30:00Z', 'revision': 8, 'idempotens': 'k9'})
        p2['fakta_ai'].append({'nyckel': 'verksamhetsmal', 'varde': 'Fler bokningar via webben', 'status': 'tolkning', 'kalla': 'kundstart AI rev 8 (openai/gpt-5-mini)', 'omrade': 'A', 'datum': '2026-09-27'})
        self.svar_pa[('GET', '/api/intern/arenden/ar_test12345678/export')] = p2
        code, r = self.kor('hamta', '--kund', str(self.k))
        self.assertEqual(code, 0, r); self.assertNotIn('EJ REGISTRERADE', r['meddelande'])
        s = iv.las(str(self.k))
        self.assertEqual(len(s['omgangar']), 2, 'inga dubbla omgångar')
        self.assertEqual(len([x for x in s['svar'] if x['fraga_id'] == 'A1']), 1, 'första svaret ligger kvar en gång')
        andrat = [f for f in s['fakta'] if f['nyckel'] == 'verksamhetsmal' and f['status'] == 'kunden uppger']
        self.assertEqual(len(andrat), 1); self.assertIn('### A2', andrat[0]['varde'], 'texten är ordagrant, avgränsaren skadar inget')
        tolkningar = [f for f in s['fakta'] if f['nyckel'] == 'verksamhetsmal' and f['status'] == 'tolkning']
        self.assertEqual(len(tolkningar), 1, 'likalydande tolkning dubbleras inte')
        self.assertTrue(tolkningar[0].get('ersatt'), 'kundens ändrade svar avgör motsägelsen mot vår tolkning')
        self.assertEqual([m['lage'] for m in s['motsagelser'] if m['nyckel'] == 'verksamhetsmal'], ['avgjord'])
        self.assertEqual(iv.las(str(self.k))['svar'][0]['kundstart_revision'], 3)

    def test_ingen_kundutsaga_forsvinner_sparlost(self):
        self.svar_pa[('POST', '/api/intern/arenden')] = {'ok': True, 'arende_id': 'ar_test12345678', 'lank': 'http://kundstart.test/start#HEMLIG', 'lank_hash': 'a' * 64, 'utgar': '2026-10-27T00:00:00Z', 'ai': 'regelstyrd'}
        self.kor('skapa', '--kund', str(self.k), '--namn', 'Testfirma', '--testdialog')
        p = paket()
        # ett svar bara i paketets svar-lista, en rättelse utan spegling, två svar på A1 i samma hämtning, en fråga tillagd senare
        p['svar'] = [{'fraga_id': 'H1', 'nyckel': 'ramar', 'omrade': 'H', 'text': 'Budget 40 000 kr', 'typ': 'text', 'mottaget': '2026-09-27T14:40:00Z', 'revision': 7, 'idempotens': 'k7'}]
        p['rattelser'].append({'nyckel': 'ton', 'varde': 'Rak', 'mottaget': '2026-09-27T14:41:00Z', 'revision': 7, 'idempotens': 'k8', 'tidigare': {'varde': '', 'kalla': '', 'typ': 'ingen'}})
        p['omgangar'][0]['svar'].append({'fraga_id': 'A1', 'nyckel': 'verksamhetsmal', 'omrade': 'A', 'text': 'Andra svaret på A1', 'typ': 'text', 'mottaget': '2026-09-27T14:05:00Z', 'revision': 6, 'idempotens': 'k6'})
        self.svar_pa[('GET', '/api/intern/arenden/ar_test12345678/export')] = p
        code, r = self.kor('hamta', '--kund', str(self.k))
        self.assertEqual(code, 0, r)
        self.assertIn('EJ REGISTRERADE', r['meddelande']); self.assertIn('H1', r['meddelande']); self.assertIn('ton', r['meddelande'])
        s = iv.las(str(self.k))
        a1 = [x for x in s['svar'] if x['fraga_id'] == 'A1']
        self.assertEqual(len(a1), 1); self.assertEqual(a1[0]['text'], 'Vi vill att kunder ska boka tid direkt på hemsidan.', 'första svaret ordagrant')
        self.assertTrue(any(f['nyckel'] == 'verksamhetsmal' and f['status'] == 'kunden uppger' and f['varde'] == 'Andra svaret på A1' for f in s['fakta']), 'andra svaret som kundens uppgift')
        d = ks.las_kundstart(str(self.k))
        self.assertEqual(len(d['hamtat'][-1]['ej_registrerade']), 2)
        # nästa hämtning: en fråga tillagd i omgång 2 med svar
        p2 = paket(revision=11); p2['svar'] = []
        p2['omgangar'][1]['fragor'].append({'id': 'BOK2', 'omrade': 'C', 'nyckel': 'bokning_tillganglighet', 'text': 'Vilka tider?', 'paverkar': 'bokning', 'utlost_av': 'A1', 'valjare': 'regelstyrd'})
        p2['omgangar'][1]['svar'].append({'fraga_id': 'BOK2', 'nyckel': 'bokning_tillganglighet', 'omrade': 'C', 'text': 'Vardagar 8–16', 'typ': 'text', 'mottaget': '2026-09-27T14:50:00Z', 'revision': 10, 'idempotens': 'k10'})
        self.svar_pa[('GET', '/api/intern/arenden/ar_test12345678/export')] = p2
        code, r = self.kor('hamta', '--kund', str(self.k))
        self.assertEqual(code, 0, r)
        s = iv.las(str(self.k))
        self.assertTrue(any(q['id'] == 'BOK2' for q in s['omgangar'][1]['fragor']), 'sent tillagd fråga förs in i sin omgång')
        self.assertTrue(any(x['fraga_id'] == 'BOK2' and x['text'] == 'Vardagar 8–16' and x.get('kalla') == 'kundstart' for x in s['svar']))
        self.assertEqual(len(s['omgangar']), 2)

    def test_kumulativ_omhamtning_dubblerar_inte_kundrader_nar_kallan_saneras(self):
        self.svar_pa[('POST', '/api/intern/arenden')] = {'ok': True, 'arende_id': 'ar_test12345678', 'lank': 'http://kundstart.test/start#HEMLIG', 'lank_hash': 'a' * 64, 'utgar': '2026-10-27T00:00:00Z', 'ai': 'regelstyrd'}
        self.kor('skapa', '--kund', str(self.k), '--namn', 'Testfirma', '--testdialog')
        p = paket(); p['fakta_ai'] = []
        p['rattelser_fakta'][0]['kalla'] = '  kundstart rättelse rev 6\n' + 'x' * 200  # styrtecken, blanksteg och överlängd saneras vid lagring
        p['rattelser'][0]['revision'] = 6
        self.svar_pa[('GET', '/api/intern/arenden/ar_test12345678/export')] = p
        self.kor('hamta', '--kund', str(self.k))
        p2 = paket(revision=12); p2['fakta_ai'] = []; p2['rattelser_fakta'] = p['rattelser_fakta']; p2['rattelser'] = p['rattelser']
        self.svar_pa[('GET', '/api/intern/arenden/ar_test12345678/export')] = p2
        code, r = self.kor('hamta', '--kund', str(self.k))
        self.assertEqual(code, 0, r)
        s = iv.las(str(self.k))
        self.assertEqual(len([f for f in s['fakta'] if f['nyckel'] == 'erbjudande' and f['status'] == 'kunden uppger' and str(f.get('kalla', '')).startswith('kundstart')]), 1, 'ingen dubbel kundrad')
        # ogiltiga kundrader och frågor i fel form redovisas, kastas inte tyst
        p3 = paket(revision=13); p3['fakta_ai'] = [{'nyckel': 'BAD KEY', 'varde': 'x', 'status': 'tolkning', 'kalla': 'k', 'omrade': 'A', 'datum': 'd'}]
        p3['rattelser_fakta'] = [{'nyckel': 'ton', 'varde': '', 'status': 'kunden uppger', 'kalla': 'kundstart rättelse rev 9', 'omrade': 'E', 'datum': 'd'}]; p3['rattelser'] = []
        p3['omgangar'][1]['fragor'].append({'id': 'BOK3', 'omrade': 'Q', 'nyckel': 'bokning_bekraftelse', 'text': 'x', 'paverkar': 'p', 'valjare': 'regelstyrd'})
        self.svar_pa[('GET', '/api/intern/arenden/ar_test12345678/export')] = p3
        code, r = self.kor('hamta', '--kund', str(self.k))
        self.assertEqual(code, 0, r)
        self.assertIn('FÖRKASTADE TOLKNINGAR', r['meddelande']); self.assertIn('kundrad i fel form', r['meddelande']); self.assertIn('BOK3', r['meddelande'])
        # en rättelse som träffar hemlighetsspärren stoppar inte verktyget med traceback
        p4 = paket(revision=14); p4['fakta_ai'] = []; p4['rattelser'] = []
        p4['rattelser_fakta'] = [{'nyckel': 'system', 'varde': 'password: hemligt123', 'status': 'kunden uppger', 'kalla': 'kundstart rättelse rev 10', 'omrade': 'D', 'datum': 'd'}]
        self.svar_pa[('GET', '/api/intern/arenden/ar_test12345678/export')] = p4
        code, r = self.kor('hamta', '--kund', str(self.k))
        self.assertEqual(code, 0, r); self.assertIn('vägrades av intervju.py', r['meddelande'])

    def test_paket_med_fel_form_vagras_i_verktygets_form(self):
        self.svar_pa[('POST', '/api/intern/arenden')] = {'ok': True, 'arende_id': 'ar_test12345678', 'lank': 'http://kundstart.test/start#HEMLIG', 'lank_hash': 'a' * 64, 'utgar': '2026-10-27T00:00:00Z', 'ai': 'regelstyrd'}
        self.kor('skapa', '--kund', str(self.k), '--namn', 'Testfirma', '--testdialog')
        p = paket(); del p['fakta_ai']
        self.svar_pa[('GET', '/api/intern/arenden/ar_test12345678/export')] = p
        code, r = self.kor('hamta', '--kund', str(self.k))
        self.assertEqual(code, 2); self.assertIn('fakta_ai', r['vagrad'])

    def test_defekta_exportformer_vagras_fore_kundfilsmutation(self):
        ks.spara_kundstart(self.k, {'arende_id': 'ar_test12345678', 'bas_url': 'http://kundstart.test', 'hamtat': []})
        # CLI tar ett nödvändigt importlås före transporten; jämför kunddata,
        # inte skapandet av den tomma låsfilen vid allra första användningen.
        with ks.konsumtionslas(self.k):
            pass
        def snapshot():
            return {str(p.relative_to(self.k)): p.read_bytes() for p in self.k.rglob('*') if p.is_file()}
        for existing in (False, True):
            if existing:
                ks.hamta(self.k, 'http://kundstart.test', 'synthetic', None, False, paket=paket())
            before = snapshot()
            bad = [None, [], dict(paket(), arende=[]), dict(paket(), omgangar={}),
                   dict(paket(), fakta_ai=[None]), dict(paket(), material=['not-an-object']),
                   dict(paket(), rattelser=[{'nyckel': 'ton', 'varde': []}]),
                   dict(paket(), tackning=None)]
            p = paket(); p['omgangar'][0]['nr'] = '1'; bad.append(p)
            p = paket(); p['omgangar'][0]['svar'] = [None]; bad.append(p)
            p = paket(); p['omgangar'][0]['svar'][0]['mottaget'] = None; bad.append(p)
            p = paket(); p['omgangar'][0]['svar'][0]['revision'] = True; bad.append(p)
            p = paket(); p['material'][0]['extraktion'] = {'text': ['wrong']}; bad.append(p)
            p = paket(); p['arende']['testdialog'] = 'false'; bad.append(p)
            for i, data in enumerate(bad):
                with self.subTest(existing=existing, shape=i):
                    self.svar_pa[('GET', '/api/intern/arenden/ar_test12345678/export')] = data
                    code, result = self.kor('hamta', '--kund', str(self.k))
                    self.assertEqual(code, 2, result)
                    self.assertIn('fel form', result['vagrad'])
                    self.assertEqual(snapshot(), before)

    def test_ny_export_metadata_samma_revision_bevarar_tidigare_exportbytes(self):
        ks.spara_kundstart(self.k, {'arende_id': 'ar_test12345678', 'bas_url': 'http://kundstart.test', 'hamtat': []})
        first = paket()
        ks.hamta(self.k, 'http://kundstart.test', 'synthetic', None, False, paket=first)
        old = self.k / 'KUNDSTART/export-rev7.json'; original = old.read_bytes()
        second = paket(); second['exporterad'] = '2026-09-28T00:00:00Z'
        ks.hamta(self.k, 'http://kundstart.test', 'synthetic', None, False, paket=second)
        self.assertEqual(old.read_bytes(), original)
        receipts = ks.las_kundstart(self.k)['hamtat']
        self.assertEqual(len(receipts), 2)
        self.assertNotEqual(receipts[0]['export_fil'], receipts[1]['export_fil'])
        self.assertEqual(ks._senast_importerade_paket(self.k), second)
        self.assertEqual(receipts[0]['export_sha256'], ks.json_sha(first))
        self.assertEqual(len(iv.las(self.k)['svar']), 2)

    def test_export_ar_data_inte_instruktion(self):
        self.svar_pa[('POST', '/api/intern/arenden')] = {'ok': True, 'arende_id': 'ar_test12345678', 'lank': 'http://kundstart.test/start#HEMLIG', 'lank_hash': 'a' * 64, 'utgar': '2026-10-27T00:00:00Z', 'ai': 'regelstyrd'}
        self.kor('skapa', '--kund', str(self.k), '--namn', 'Testfirma', '--testdialog')
        p = paket()
        p['material'] = [{'id': '../../x', 'typ': 'fil', 'filnamn': '../../../evil', 'mime': 'image/png', 'storlek': 3, 'sha256': hashlib.sha256(b'png').hexdigest(), 'mottaget': 't', 'revision': 4, 'hamta': '@annanvard.example/x'},
                         {'id': 'm_ok12345', 'typ': 'fil', 'filnamn': '../logotyp.png', 'mime': 'image/png', 'storlek': 3, 'sha256': hashlib.sha256(b'png').hexdigest(), 'mottaget': 't', 'revision': 4, 'hamta': 'http://kundstart.test@annanvard.example/x'}]
        p['omgangar'][0]['fragor'][0]['id'] = 'inte ett id'; p['omgangar'][0]['svar'][0]['fraga_id'] = 'inte ett id'
        self.svar_pa[('GET', '/api/intern/arenden/ar_test12345678/export')] = p
        code, r = self.kor('hamta', '--kund', str(self.k), '--material')
        self.assertEqual(code, 0, r)
        vagar = [v for (m, v, k) in self.anrop if m == 'GET' and '/material/' in v]
        self.assertEqual(vagar, ['/api/intern/arenden/ar_test12345678/material/m_ok12345'], 'hämtningsvägen byggs av verktyget, aldrig ur paketet')
        self.assertTrue((self.k / 'KUNDSTART' / 'material' / 'm_ok12345-.._logotyp.png').is_file() or any(p.name.startswith('m_ok12345-') for p in (self.k / 'KUNDSTART' / 'material').iterdir()))
        self.assertFalse((self.k.parent / 'evil').exists()); self.assertFalse((self.k / 'x').exists())
        s = iv.las(str(self.k))
        self.assertEqual([q['id'] for o in s['omgangar'] for q in o['fragor']], ['BOK1'], 'ogiltiga fråge-id tas inte in')

    def test_tolkning_som_motsags_av_rattelse_avgors_till_kunden_med_skal(self):
        self.svar_pa[('POST', '/api/intern/arenden')] = {'ok': True, 'arende_id': 'ar_test12345678', 'lank': 'http://kundstart.test/start#HEMLIG', 'lank_hash': 'a' * 64, 'utgar': '2026-10-27T00:00:00Z', 'ai': 'regelstyrd'}
        self.kor('skapa', '--kund', str(self.k), '--namn', 'Testfirma', '--testdialog')
        p = paket()
        p['fakta_ai'] = [{'nyckel': 'ton', 'varde': 'Varm och personlig', 'status': 'tolkning', 'kalla': 'kundstart AI rev 3 (m)', 'omrade': 'E', 'datum': '2026-09-27'}]
        p['rattelser_fakta'] = [{'nyckel': 'ton', 'varde': 'Saklig och rak', 'status': 'kunden uppger', 'kalla': 'kundstart rättelse rev 6', 'omrade': 'E', 'datum': '2026-09-27', 'tidigare': {'varde': 'Varm och personlig', 'kalla': 'kundstart AI rev 3 (m)', 'typ': 'ai'}}]
        p['rattelser'] = []
        self.svar_pa[('GET', '/api/intern/arenden/ar_test12345678/export')] = p
        code, r = self.kor('hamta', '--kund', str(self.k))
        self.assertEqual(code, 0, r)
        s = iv.las(str(self.k))
        self.assertFalse(any(f['nyckel']=='ton' and f['status']=='tolkning' for f in s['fakta']))
        self.assertEqual(next(f for f in s['fakta'] if f['nyckel']=='ton')['varde'], 'Saklig och rak')
        self.assertIn('FÖRKASTADE TOLKNINGAR', r['meddelande'])

    def test_vagrar_kundmapp_i_repot_och_nyckelfil_med_fel_rattighet(self):
        os.chmod(self.nyckel, 0o644)
        code, r = self.kor('status', '--kund', str(self.k))
        self.assertEqual(code, 2); self.assertIn('0600', r['vagrad'])
        os.chmod(self.nyckel, 0o600)
        code, r = self.kor('status', '--kund', str(HERE))
        self.assertEqual(code, 2); self.assertIn('repot', r['vagrad'])
        tmpnyckel = Path(self.tmp.name) / 'n.secret'; tmpnyckel.write_text('x' * 40); os.chmod(tmpnyckel, 0o600)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = ks.main(['status', '--kund', str(self.k), '--bas-url', 'http://kundstart.test', '--nyckel-fil', str(tmpnyckel)])
        self.assertEqual(code, 2); self.assertIn('/var/folders', json.loads(out.getvalue())['vagrad'])
        tmp2 = Path('/tmp') / ('kundstart-prov-%d.secret' % os.getpid()); tmp2.write_text('x' * 40); os.chmod(tmp2, 0o600)
        try:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = ks.main(['status', '--kund', str(self.k), '--bas-url', 'http://kundstart.test', '--nyckel-fil', str(tmp2)])
            self.assertEqual(code, 2); self.assertIn('/tmp', json.loads(out.getvalue())['vagrad'])
        finally:
            tmp2.unlink()


if __name__ == '__main__':
    unittest.main()
