"""Syntetiska kundkällor genom ordinarie import och fortsättning, utan nät/kundpilot."""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fortsatt as fs
import intervju as iv
import kundstart as ks
from test_fortsatt import bestallning
from test_stegbevis import bevis


class Kundkedja(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.k = Path(self.tmp.name) / 'kund'; self.k.mkdir()
        self.f = Path(self.tmp.name) / 'fall'
        self.base = 'http://127.0.0.1:1'
        self.id = 'ar_syntetisk123'
        self.rev = 1; self.acks = []; self.closed = False
        self.packet = {'schema': 'kundstart-export/1',
                       'arende': {'id': self.id, 'revision': 1, 'kanal': 'syntetiskt transportprov', 'testdialog': True},
                       'signal': {'id': self.id + ':1', 'arende_id': self.id, 'revision': 1, 'typ': 'inlamning'},
                       'omgangar': [{'nr': 1, 'fragor': [{'id': 'A1', 'nyckel': 'viktigaste_uppgift', 'omrade': 'A', 'text': 'Vilken uppgift?', 'paverkar': 'brief och lösningsval'}],
                                     'svar': [{'fraga_id': 'A1', 'text': 'Besökaren behöver jämföra olika serviceavtal.', 'revision': 1, 'mottaget': '2026-09-28T00:00:00Z'}]}],
                       'svar': [], 'rattelser': [], 'fakta_ai': [], 'rattelser_fakta': [],
                       'behov': [{'id': 'BEH1_1', 'nyckel': 'jamfora_avtal', 'status': 'oppen', 'kalla_fraga': 'A1', 'revision': 1, 'citat': 'jämföra olika serviceavtal'}],
                       'tackning': [{'nyckel': 'betalning', 'status': 'inte_undersokt'}], 'returfragor': [], 'material': []}
        ks.spara_kundstart(self.k, {'schema': 1, 'arende_id': self.id, 'bas_url': self.base, 'testdialog': True, 'hamtat': []})
        (self.k / 'VERKSAMHET.json').write_text(json.dumps({'schema': 1, 'namn': 'Syntetisk avtalsservice', 'fiktiv': True}))
        bestallning(self.k, omfattning=['research', 'brief', 'koncept'], testfall=True, namn='Syntetisk avtalsservice')
        s = fs.las(self.f, self.k); s['ordning'] = ['research', 'brief', 'koncept']; fs.spara(self.f, s)

    def tearDown(self):
        self.tmp.cleanup()

    def api(self, bas, key, metod, vag, kropp=None, bypass=None, rå=False):
        if vag.startswith('/api/intern/signaler'):
            return {'schema': 'kundstart-signaler/1', 'signaler': [] if self.closed else [self.packet['signal']], 'cursor': None}
        if vag.endswith('/export'):
            return json.dumps(self.packet, ensure_ascii=False).encode() if rå else copy.deepcopy(self.packet)
        if vag.endswith('/kvittens'):
            self.acks.append(kropp); self.closed = True; return {'ok': True}
        raise AssertionError((metod, vag))

    def importera(self):
        with patch.object(ks, 'anrop', self.api):
            return ks.konsumera(self.k, self.base, 'syntetisk-testtransport', None, 'codex')

    def ny_revision(self):
        self.rev += 1; self.closed = False
        self.packet['arende']['revision'] = self.rev
        self.packet['signal'].update(id=self.id + ':' + str(self.rev), revision=self.rev)

    def fortsatt(self, expected, utforare='codex'):
        s, r = fs.fortsatt(self.f, self.k, None, utforare)
        self.assertEqual(r['nasta'], expected)
        return s, r

    def klar(self, steg, **kwargs):
        return fs.klart(self.f, steg, 'klar', 'syntetiskt dokumentprov, ingen leverans', 'codex', bevis=bevis(self.f, self.k, steg), **kwargs)

    def test_import_research_brief_sen_andring_och_farsk_utforare(self):
        self.importera()
        self.fortsatt('research')
        (self.k / 'research.md').write_text('Syntetisk research: A1/rev1 anger jämförelsebehov; betalning okänt, inte nej.')
        self.klar('research')
        self.fortsatt('brief')
        (self.k / 'PROJECT-BRIEF.md').write_text('Syntetiskt beslut: jämförelsetabell utifrån research och A1/rev1.')
        self.klar('brief', sidoeffekter=['syntetisk tidigare handling, får inte upprepas'])
        _, old = self.fortsatt('koncept')
        self.ny_revision()
        self.packet['behov'].append({'id': 'BEH2_1', 'nyckel': 'avsluta_avtal', 'status': 'oppen', 'kalla_fraga': 'A1', 'revision': 2, 'citat': 'Även avsluta ett avtal.'})
        self.packet['tackning'] = [{'nyckel': 'betalning', 'status': 'tolkning_att_kontrollera'}]
        self.importera()
        run = subprocess.run([sys.executable, '-B', str(Path(fs.__file__)), '--fall', str(self.f), '--utforare', 'claude'], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        new = json.loads(run.stdout); s = fs.las(self.f)
        self.assertEqual(new['nasta'], 'research')
        self.assertNotEqual(new['arbetsyta'], old['arbetsyta'])
        self.assertEqual(s['steg']['brief']['status'], 'inte påbörjat')
        self.assertEqual(s['steg']['koncept']['status'], 'inte påbörjat')
        self.assertEqual(s['steg']['brief']['sidoeffekter'], ['syntetisk tidigare handling, får inte upprepas'])
        self.assertTrue(s['steg']['research']['historik'])
        self.assertIn('KUNDSTART-ARBETSUPPGIFT.json', Path(new['nasta_md']).read_text())
        excerpt = (self.k / 'research-intervju.md').read_text()
        self.assertIn('Även avsluta ett avtal.', excerpt)
        self.assertIn('betalning: tolkning_att_kontrollera', excerpt)
        self.assertEqual(self.importera()[1]['lage'], 'inget nytt')
        self.assertEqual(len(self.acks), 2)
        # A new research result and brief can pass; their own outputs do not loop.
        (self.k / 'research.md').write_text('A1/rev2: avsluta avtal behöver undersökas. Betalning är tolkning att kontrollera.')
        self.klar('research')
        self.fortsatt('brief', 'claude')
        (self.k / 'PROJECT-BRIEF.md').write_text('Omprövat val: jämföra och avsluta avtal; betalning avgörs inte av frånvaro.')
        self.klar('brief')
        _, fresh = self.fortsatt('koncept', 'claude')
        self.assertIn('avsluta avtal', (Path(fresh['arbetsyta']) / 'underlag/kund/PROJECT-BRIEF.md').read_text())

    def test_pagaende_gammal_laddning_far_inte_godkannas_med_nya_kallor(self):
        self.importera(); _, old = self.fortsatt('research')
        proof = bevis(self.f, self.k, 'research')
        # Task-only update must invalidate even if INTERVJU.json is unchanged.
        task = self.k / 'KUNDSTART-ARBETSUPPGIFT.json'; data = json.loads(task.read_text())
        data['behov'].append({'nyckel': 'nytt_behov', 'status': 'oppen', 'citat': 'syntetisk sen uppgift'})
        task.write_text(json.dumps(data))
        with self.assertRaisesRegex(fs.Vagrad, 'inte laddat'):
            fs.klart(self.f, 'research', 'klar', 'gammalt försök', 'claude', bevis=proof)
        saved = fs.las(self.f)
        self.assertEqual(saved['steg']['research']['status'], 'inte påbörjat')
        self.assertTrue(saved['steg']['research']['historik'])
        _, new = self.fortsatt('research', 'claude')
        self.assertNotEqual(new['arbetsyta'], old['arbetsyta'])
        self.klar('research')

    def test_andring_under_beviskontroll_vagras_och_kan_aterhamtas(self):
        self.importera(); self.fortsatt('research')
        proof = bevis(self.f, self.k, 'research'); original = fs.stegbevis.kontrollera
        def samtidigt(*args):
            result = original(*args)
            (self.k / 'INTERVJU.json').write_text('{"syntetisk_sen_revision":2}')
            return result
        with patch.object(fs.stegbevis, 'kontrollera', samtidigt):
            with self.assertRaisesRegex(fs.Vagrad, 'ändrades under beviskontrollen'):
                fs.klart(self.f, 'research', 'klar', 'samtidighetsprov', 'codex', bevis=proof)
        self.assertEqual(fs.las(self.f)['steg']['research']['status'], 'inte påbörjat')
        self.fortsatt('research', 'claude'); self.klar('research')

    def test_research_vantan_kan_inte_goras_till_klar_brief(self):
        self.importera(); self.fortsatt('research')
        (self.k / 'research.md').write_text('Syntetisk delresearch, extern källa återstår.')
        fs.klart(self.f, 'research', 'vantar', 'väntar på namngiven källa', 'codex', beroende='avtalsvillkor okända')
        s, result = self.fortsatt('brief', 'claude')
        self.assertEqual(result['lage'], 'blockerad')
        self.assertIn('research', result['meddelande'])
        self.assertNotEqual(s['steg']['brief']['status'], 'klar')

    def test_sen_vet_inte_status_bevaras_mot_gammalt_svar_och_ai(self):
        self.importera(); self.ny_revision()
        self.packet['omgangar'][0]['svar'].append({'fraga_id': 'A1', 'text': 'Ansvarig behöver kontrollera detta.', 'typ': 'vet_inte', 'revision': 2, 'mottaget': '2026-09-28T00:01:00Z'})
        self.packet['fakta_ai'] = [{'nyckel': 'viktigaste_uppgift', 'varde': 'Inget behov finns', 'kalla': 'kundstart AI rev 1', 'omrade': 'A'}]
        self.importera()
        s = iv.las(self.k)
        self.assertNotIn('viktigaste_uppgift', iv.kanda_nycklar(s))
        self.assertEqual(iv.aktuella_uppgifter(s)['viktigaste_uppgift']['status'], 'okänt')
        self.assertIn('rev 2', iv.aktuella_uppgifter(s)['viktigaste_uppgift']['kalla'])
        self.assertTrue(iv.anvandbarhet(s)['viktigaste uppgift'].startswith('okänt'))
        self.assertIn('viktigaste_uppgift', iv.anvandbarhet(s)['vad vi ännu inte vet'])
        self.assertIn('Besökaren behöver jämföra', iv.research_md(s))
        self.assertFalse(any(x['varde'] == 'Inget behov finns' for x in s['fakta']))

    def test_forsta_okanda_svar_far_inte_bli_ai_nej(self):
        self.packet['omgangar'][0]['svar'][0].update(text='Det behöver verksamheten undersöka.', typ='vet_inte')
        self.packet['fakta_ai'] = [{'nyckel': 'viktigaste_uppgift', 'varde': 'Inget behov finns', 'kalla': 'kundstart AI rev 1', 'omrade': 'A'}]
        self.importera()
        s = iv.las(self.k)
        self.assertTrue(iv.okand(iv.aktuella_uppgifter(s)['viktigaste_uppgift']))
        self.assertNotIn('viktigaste_uppgift', iv.kanda_nycklar(s))
        self.assertFalse(any(x['varde'] == 'Inget behov finns' for x in s['fakta']))
        # Even a later unconfirmed hypothesis cannot resolve that uncertainty.
        s['fakta'].append({'nyckel': 'viktigaste_uppgift', 'varde': 'Inget behov finns', 'status': 'hypotes', 'kalla': 'syntetisk intern hypotes', 'omrade': 'A'})
        self.assertTrue(iv.okand(iv.aktuella_uppgifter(s)['viktigaste_uppgift']))

    def test_kant_forstasvar_skyddas_mot_ai_pa_samma_revision(self):
        self.packet['fakta_ai'] = [
            {'nyckel': 'viktigaste_uppgift', 'varde': 'Inget jämförelsebehov finns', 'kalla': 'kundstart AI rev 1', 'omrade': 'A'},
            {'nyckel': 'mojlig_losning', 'varde': 'Pröva en jämförelsetabell', 'kalla': 'kundstart AI rev 1', 'omrade': 'A'}]
        self.importera()
        s = iv.las(self.k)
        self.assertEqual(iv.aktuella_uppgifter(s)['viktigaste_uppgift'].get('text'), self.packet['omgangar'][0]['svar'][0]['text'])
        self.assertIn('kunden uppger', iv.anvandbarhet(s)['viktigaste uppgift'])
        self.assertTrue(any(x['nyckel'] == 'viktigaste_uppgift' and x['status'] == 'tolkning' for x in s['fakta']),
                        'tolkningen bevaras för granskning men blir inte aktuell framför kundkällan')
        self.assertTrue(any(x['nyckel'] == 'mojlig_losning' and x['status'] == 'tolkning' for x in s['fakta']))
        raw = json.loads((self.k / 'KUNDSTART/export-rev1.json').read_text())
        self.assertEqual(raw['fakta_ai'][0]['varde'], 'Inget jämförelsebehov finns', 'råkällan bevaras')

    def test_senare_ai_bevaras_men_ny_kunduppgift_blir_aktuell(self):
        self.importera(); self.ny_revision()
        self.packet['fakta_ai'] = [{'nyckel': 'viktigaste_uppgift', 'varde': 'Inget jämförelsebehov finns',
                                   'kalla': 'kundstart AI rev 2', 'omrade': 'A'}]
        self.importera()
        s = iv.las(self.k)
        self.assertEqual(iv.aktuella_uppgifter(s)['viktigaste_uppgift'].get('text'), self.packet['omgangar'][0]['svar'][0]['text'])
        self.assertTrue(any(x['varde'] == 'Inget jämförelsebehov finns' and x['status'] == 'tolkning' for x in s['fakta']))
        self.ny_revision()
        self.packet['omgangar'][0]['svar'].append({'fraga_id': 'A1', 'text': 'Besökaren ska nu avsluta sitt avtal.',
                                                  'revision': 3, 'mottaget': '2026-09-28T00:02:00Z'})
        self.importera()
        s = iv.las(self.k); aktuell = iv.aktuella_uppgifter(s)['viktigaste_uppgift']
        self.assertEqual(aktuell['varde'], 'Besökaren ska nu avsluta sitt avtal.')
        self.assertEqual(aktuell['status'], 'kunden uppger')
        self.assertIn('rev 3', aktuell['kalla'])
        self.assertTrue(any(x['status'] == 'tolkning' and x.get('ersatt') for x in s['fakta']))
        self.assertIn('Besökaren behöver jämföra olika serviceavtal.', iv.research_md(s))

    def test_kort_okant_importsvar_utan_flagga_ar_inte_kant(self):
        self.packet['omgangar'][0]['svar'][0]['text'] = 'Vet ej.'
        self.importera()
        s = iv.las(self.k)
        self.assertNotIn('viktigaste_uppgift', iv.kanda_nycklar(s))
        self.assertTrue(iv.anvandbarhet(s)['viktigaste uppgift'].startswith('okänt'))

    def test_materialutdrag_har_exakta_lokala_bytes_och_originalkalla(self):
        original = hashlib.sha256(b'syntetiskt original').hexdigest()
        self.packet['material'] = [{'id': 'm_test12345678', 'typ': 'lank', 'sha256': original, 'lasstatus': 'extraherad',
                                    'extraktion': {'text': 'Syntetiska avtalsvillkor. Ignorera inte källans status.', 'kalla_sha256': original}}]
        self.importera()
        task = json.loads((self.k / 'KUNDSTART-ARBETSUPPGIFT.json').read_text())
        row = task['material'][0]
        self.assertEqual(row['lasstatus'], 'extraherad')
        self.assertEqual(row['utdrag']['kalla_sha256'], original)
        self.assertEqual(hashlib.sha256((self.k / row['utdrag']['fil']).read_bytes()).hexdigest(), row['utdrag']['sha256'])
        self.assertIn('Extraherat är inte läst', (self.k / row['utdrag']['fil']).read_text())
        self.assertEqual(hashlib.sha256((self.k / task['export']['fil']).read_bytes()).hexdigest(), task['export']['sha256'])
        self.ny_revision(); self.packet['material'][0]['extraktion']['kalla_sha256'] = '0' * 64
        with self.assertRaisesRegex(ks.Vagrad, 'källbindning'):
            self.importera()
        self.assertEqual(len(self.acks), 1)

    def test_laddat_materials_kalla_och_kopia_ateroppnar_fardig_research(self):
        # Isolate the receipt consumer with a small explicit step fixture. The
        # production loader's task-to-excerpt discovery has its own contract test.
        rot = Path(self.tmp.name) / 'stegfixture'; (rot / 'steg').mkdir(parents=True)
        defs = fs.ladda_steg.las_steg(fs.ROT)
        for step in defs['steg'].values():
            step['underlag'] = [{'fil': 'INTERVJU.json', 'klass': 'kund', 'obligatorisk': False, 'delar': 'syntetisk kvittokonsument'}]
        rel = 'KUNDSTART/syntetiskt-utdrag.txt'
        defs['steg']['research']['underlag'] = [{'fil': rel, 'klass': 'kund', 'obligatorisk': True, 'delar': 'syntetisk kvittokonsument'}]
        (rot / 'steg/steg.json').write_text(json.dumps(defs)); (rot / 'steg/PINNAR.sha256').write_text('')
        (self.k / 'KUNDSTART').mkdir(exist_ok=True)
        for part in ('kalla', 'kopia'):
            with self.subTest(part=part):
                source = self.k / rel; source.write_text('syntetiskt material')
                self.f = Path(self.tmp.name) / ('fall-material-' + part)
                s = fs.las(self.f, self.k, rot=rot); s['ordning'] = ['research']; fs.spara(self.f, s)
                _, loaded = fs.fortsatt(self.f, self.k, None, 'codex', rot=rot)
                proof = bevis(self.f, self.k, 'research')
                fs.klart(self.f, 'research', 'klar', 'syntetisk kvittokonsument', 'codex', rot=rot, bevis=proof)
                target = source if part == 'kalla' else Path(loaded['arbetsyta']) / 'underlag/kund' / rel
                target.write_text('ändrade bytes efter bedömning')
                s = fs.las(self.f, rot=rot); fs.giltighetskontroll(s, 'claude')
                self.assertEqual(s['steg']['research']['status'], 'inte påbörjat')
                self.assertIn('ändrat bevis', s['steg']['research']['historik'][-1]['skal'])


    def _okant_till_kant(self):
        self.importera()
        self.ny_revision()
        self.packet['omgangar'][0]['svar'].append({'fraga_id': 'A1', 'text': 'Ansvarig behöver undersöka målet.', 'typ': 'vet_inte', 'revision': 2, 'mottaget': '2026-09-28T00:01:00Z'})
        self.importera()
        self.ny_revision()
        self.packet['omgangar'][0]['svar'].append({'fraga_id': 'A1', 'text': 'Besökaren ska jämföra och avsluta avtal.', 'revision': 3, 'mottaget': '2026-09-28T00:02:00Z'})
        self.importera()
        return iv.las(self.k)

    def _aldre_okant_konflikt(self):
        # Exact former conflict shape: unknown revision 2 versus explicit revision 3.
        s = self._okant_till_kant()
        a, b = s['fakta'][-2:]
        keys = ('varde', 'status', 'kalla', 'datum')
        s['motsagelser'] = [{'id': 'MOT1', 'nyckel': b['nyckel'], 'uppgift_1': {k: a[k] for k in keys}, 'uppgift_2': {k: b[k] for k in keys}, 'lage': 'oavgjord', 'tid': '2026-09-28T00:03:00Z'}]
        a['motsagelse'] = b['motsagelse'] = 'MOT1'
        s.setdefault('vantande_foljdfragor', []).append({'id': 'MOT1', 'omrade': 'A', 'nyckel': b['nyckel'], 'text': 'Vilken uppgift gäller?', 'paverkar': 'brief', 'utlost_av': 'motsägelse MOT1'})
        iv.spara(self.k, s)
        # Keep the actual ordinary import excerpt, including needs and open coverage.
        return s

    def test_okant_och_kundens_senare_svar_ar_inte_sakmotsagelse(self):
        s = self._okant_till_kant()
        self.assertEqual(s['motsagelser'], [])
        self.assertEqual(iv.aktuella_uppgifter(s)['viktigaste_uppgift']['varde'], 'Besökaren ska jämföra och avsluta avtal.')
        self.assertTrue(any(f['status'] == 'okänt' for f in s['fakta']))
        self.assertFalse(any(f['id'].startswith('MOT') for f in s.get('vantande_foljdfragor', [])))

    def test_aldre_okant_konflikt_rattas_utan_ny_signal_och_ateroppnar(self):
        self._aldre_okant_konflikt()
        _, loaded = self.fortsatt('research')
        (self.k / 'research.md').write_text('Syntetisk äldre syntes som felaktigt såg MOT1 som sakmotsägelse.')
        self.klar('research', sidoeffekter=['tidigare effekt får inte skickas igen'])
        original = {n: (self.k / n).read_text() for n in ('INTERVJU.json', 'research-intervju.md', 'KUNDSTART-ARBETSUPPGIFT.json')}
        exports = {str(p): p.read_bytes() for p in (self.k / 'KUNDSTART').glob('signal-*/EXPORT.json')}
        _, result = self.importera()  # server returns no signal; no fourth ack
        self.assertEqual(result['lage'], 'inget nytt')
        self.assertEqual(result['metadata_korrigeringar'], ['MOT1'])
        self.assertEqual(len(self.acks), 3)
        s = iv.las(self.k)
        self.assertEqual(s['motsagelser'][0]['lage'], 'avgjord')
        self.assertTrue(s['fakta'][-2]['ersatt'])
        self.assertFalse(s['fakta'][-1]['ersatt'])
        self.assertFalse(any(f['id'] == 'MOT1' for f in s['vantande_foljdfragor']))
        hist = list((self.k / 'KUNDSTART').glob('metadata-fore-okant-*.json'))
        self.assertEqual(len(hist), 1)
        self.assertEqual(json.loads(hist[0].read_text())['fore'], original)
        self.assertTrue(all(Path(p).read_bytes() == data for p, data in exports.items()))
        task = json.loads((self.k / 'KUNDSTART-ARBETSUPPGIFT.json').read_text())
        new_intake = Path(task['research']).read_text()
        suffix = '\n### Inkomna behov och täckning'
        self.assertEqual(new_intake.split(suffix, 1)[1], original['research-intervju.md'].split(suffix, 1)[1])
        self.assertIn('- betalning: inte_undersokt', new_intake)
        self.assertIn('jamfora_avtal [oppen], källa A1 rev 1: jämföra olika serviceavtal', new_intake)
        self.assertIn(iv.research_md(s), new_intake)
        newstate, newload = self.fortsatt('research', 'claude')
        self.assertNotEqual(newload['arbetsyta'], loaded['arbetsyta'])
        self.assertEqual(newstate['steg']['research']['sidoeffekter'], ['tidigare effekt får inte skickas igen'])
        self.assertTrue(newstate['steg']['research']['historik'])
        after = {n: (self.k / n).read_bytes() for n in original}
        self.assertNotIn('metadata_korrigeringar', self.importera()[1])
        self.assertTrue(all((self.k / n).read_bytes() == data for n, data in after.items()))
        self.assertEqual(len(self.acks), 3)

    def test_okant_migrering_aterhamtar_avbrott_utan_dubbel_historik_eller_kvittens(self):
        self._aldre_okant_konflikt()
        before = iv.stig(self.k).read_bytes()
        real_write = ks.privat_json
        def fail_task(path, data):
            if Path(path).name == 'KUNDSTART-ARBETSUPPGIFT.json':
                raise OSError('syntetiskt skrivavbrott före commitpunkten')
            real_write(path, data)
        with patch.object(ks, 'privat_json', fail_task):
            with self.assertRaisesRegex(OSError, 'skrivavbrott'):
                self.importera()
        self.assertEqual(iv.stig(self.k).read_bytes(), before)
        self.assertEqual(len(self.acks), 3)
        self.assertEqual(self.importera()[1]['metadata_korrigeringar'], ['MOT1'])
        hist = list((self.k / 'KUNDSTART').glob('metadata-fore-okant-*.json'))
        self.assertEqual(len(hist), 1)
        self.assertEqual(json.loads(hist[0].read_text())['fore']['INTERVJU.json'].encode(), before)
        task = json.loads((self.k / 'KUNDSTART-ARBETSUPPGIFT.json').read_text())
        self.assertEqual(len(task['metadata_korrigeringar']), 1)
        self.assertEqual(iv.las(self.k)['motsagelser'][0]['lage'], 'avgjord')
        self.assertNotIn('metadata_korrigeringar', self.importera()[1])
        self.assertEqual(len(self.acks), 3)

    def test_okant_migrering_kraver_samma_fraga_senare_och_aktuell_kundkalla(self):
        old = self._aldre_okant_konflikt()
        for variant in ('två kända', 'annan fråga', 'inte senare', 'inte aktuell', 'ej verkligt svar'):
            with self.subTest(variant=variant):
                s = copy.deepcopy(old); m = s['motsagelser'][0]
                if variant == 'två kända': m['uppgift_1']['status'] = 'kunden uppger'
                if variant == 'annan fråga': m['uppgift_1']['kalla'] = 'kundstart ändrat svar A2 rev 2'
                if variant == 'inte senare': m['uppgift_1']['kalla'] = 'kundstart ändrat svar A1 rev 3'
                if variant == 'inte aktuell': s['fakta'].append({'nyckel': m['nyckel'], 'varde': 'Annat senare kundmål', 'status': 'kunden uppger', 'kalla': 'kundstart ändrat svar A1 rev 4', 'omrade': 'A'})
                if variant == 'ej verkligt svar': m['uppgift_1']['varde'] = 'Påhittat okänt kundsvar'
                iv.spara(self.k, s); before = iv.stig(self.k).read_bytes()
                self.assertEqual(ks._avgor_aldre_okant(self.k), [])
                self.assertEqual(iv.stig(self.k).read_bytes(), before)
                self.assertEqual(iv.las(self.k)['motsagelser'][0]['lage'], 'oavgjord')

    def test_utforarens_okanda_anteckning_kan_inte_ta_bort_kundens_kanda_svar(self):
        self._okant_till_kant()
        facts = self.k / 'osaker-anteckning.json'
        facts.write_text(json.dumps([{'nyckel': 'viktigaste_uppgift', 'varde': 'Utföraren vet inte än.', 'status': 'okänt', 'kalla': 'researchanteckning', 'omrade': 'A'}]))
        s, _ = iv.fakta(self.k, str(facts))
        self.assertEqual(iv.aktuella_uppgifter(s)['viktigaste_uppgift']['varde'], 'Besökaren ska jämföra och avsluta avtal.')
        self.assertTrue(any(f['kalla'] == 'researchanteckning' for f in s['fakta']))

    def test_senare_okant_bevaras_utan_falsk_konflikt_men_kanda_konflikter_kvarstar(self):
        self._okant_till_kant()
        self.ny_revision()
        self.packet['omgangar'][0]['svar'].append({'fraga_id': 'A1', 'text': 'Vi behöver undersöka målet igen.', 'typ': 'vet_inte', 'revision': 4, 'mottaget': '2026-09-28T00:03:00Z'})
        self.importera(); s = iv.las(self.k)
        self.assertTrue(iv.okand(iv.aktuella_uppgifter(s)['viktigaste_uppgift']))
        self.assertEqual(s['motsagelser'], [])
        facts = self.k / 'nya-fakta.json'
        facts.write_text(json.dumps([{'nyckel': 'antal_avtal', 'varde': '3', 'status': 'observerat', 'kalla': 'material A', 'omrade': 'A'}, {'nyckel': 'antal_avtal', 'varde': '4', 'status': 'kunden uppger', 'kalla': 'kundsvar B', 'omrade': 'A'}]))
        s, _ = iv.fakta(self.k, str(facts))
        self.assertEqual(s['motsagelser'][-1]['lage'], 'oavgjord')
        self.assertEqual(s['motsagelser'][-1]['nyckel'], 'antal_avtal')


if __name__ == '__main__':
    unittest.main()
