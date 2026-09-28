"""Bildkontrakt genom faktiskt renderat Runtime-schema; syntetiska data, ingen produktdom."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kor_profil
import kritikbevis as kb
import ladda_steg
from test_kritikbevis import bildfixture

ROT = Path(__file__).resolve().parent.parent


class Bildschema(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.k = self.root / 'kund'
        self.d = bildfixture(self.k)
        for role, name in [('kandidat', 'mobil'), ('referens', 'annan'), ('dagens', 'fore')]:
            row = copy.deepcopy(self.d['bilder'][0])
            row.update(roll=role, fil=name+'.png', plats={'kandidat':'VYER', 'referens':'REFERENSER', 'dagens':'DAGENS'}[role]+'/'+name+'.png',
                       kalla='syntetisk '+name, tid='2026-09-28T01:00:00Z', vy='1x1 '+name, tacker=[])
            (self.k / row['fil']).write_bytes((self.k / 'kandidat.png').read_bytes())
            self.d['bilder'].append(row)
        (self.k / kb.BILDFIL).write_text(json.dumps(self.d, ensure_ascii=False))
        (self.k / 'PROJECT-BRIEF.md').write_text('syntetisk brief')

    def tearDown(self):
        self.tmp.cleanup()

    def schema(self, mall='renderingslasning'):
        text = (ROT / ('kritik/SCHEMA-'+mall+'.json')).read_text()
        return json.loads(kor_profil.bind_bildschema(text, self.d))

    def comparison(self, old, candidate='VYER/kandidat.png'):
        row = next(b for b in self.d['bilder'] if b['plats'] == old)
        key = 'dagensbild' if row['roll'] == 'dagens' else 'referensbild'
        return {'kandidatbild':candidate, key:old, **{k:row[k] for k in ('kalla', 'tid', 'vy')},
                'drag':'syntetiskt drag', 'observation':'syntetiskt prov', 'konsekvens':'ingen produktdom', 'beslut_och_skal':'pröva kontraktet'}

    def answer(self):
        binding = kb.bindning(self.d, 'a'*64)
        answer = {'kriterieversion':kb.VERSION, 'bedomningsbindning':binding, 'verdict':'approved',
                  'blocking_findings':[], 'improvements':[], 'could_not_review':[],
                  'questions':{f'q{i}':'syntetiskt' for i in range(1,7)}, 'best':[], 'worst':[], 'summary':'syntetiskt',
                  'seen_files':[b['plats'] for b in self.d['bilder']],
                  'referensjamforelser':[self.comparison('REFERENSER/referens.png')],
                  'dagensjamforelser':([self.comparison('DAGENS/fore.png')] if any(b['roll']=='dagens' for b in self.d['bilder']) else [])}
        receipt = {'parameters':{'executor':'claude'}, 'images':{'complete':True,
                   'delivered_or_opened':answer['seen_files'], 'how':'opened with Read (from the stream)'}}
        return answer, binding, receipt

    def native(self, schema, values):
        # Samma aktiva, hashverifierade Runtime-dialekt som profilkommandot, utan modellstart.
        root = kor_profil.runtime_root()
        release = kor_profil.aktiv_release(root)
        probe = '''import json,sys
from runtime.web_critique import check_schema,validate
p=json.load(sys.stdin);check_schema(p['schema']);result=[]
for value in p['values']:
 try: validate(value,p['schema']);result.append(True)
 except ValueError: result.append(False)
print(json.dumps(result))
'''
        done = subprocess.run([release['python'], '-B', '-c', probe], input=json.dumps({'schema':schema, 'values':values}),
                              text=True, capture_output=True, cwd=release['kod'], env=kor_profil.miljo(root), timeout=30)
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(done.stdout)

    def test_enum_nar_faktiska_runtime_schemafilen_i_bada_mallarna(self):
        r = ladda_steg.ladda(ROT, 'kritik', self.root/'laddning', kund=self.k)
        files = self.root/'files.json'
        note = self.root/'extra.txt'; note.write_text('syntetiskt kompletterande underlag')
        files.write_text(json.dumps([{'kalla':str(note),'plats':'TEXT/extra.txt','vad':'kompletterande provtext'}]))
        fall = self.root/'fall'; fall.mkdir()
        for mall in ('renderingslasning', 'designkritik-komp'):
            original = kor_profil.laddad_fil(r, 'kritik/SCHEMA-'+mall+'.json')
            a = SimpleNamespace(mall=mall, parameter=['NUMMER=1','ANTAL=1','VAD=prov','KUND=prov','KOMP=A','AXEL=prov','KOMPNAMN=prov','VAD_KOMPEN_VISAR=syntetiskt'],
                                filer=str(files), fall=str(fall), etikett=mall, torr=False, utforare='claude', modell='prov', tid=10)
            argv, extra = kor_profil.bygg_kritik(a, {'python':'python'}, None, r, 'a'*64)
            raw = Path(argv[argv.index('--schema')+1]).read_bytes()
            schema = json.loads(raw)
            self.assertEqual(extra['schema_sha256'], hashlib.sha256(raw).hexdigest())
            manifest = json.loads(Path(argv[argv.index('--underlag')+1]).read_text())
            expected = json.loads(kor_profil.bind_sedda_filer(json.dumps(self.schema(mall)), manifest['filer']))
            self.assertEqual(schema, expected)
            places = sorted({f['plats'] for f in manifest['filer']} | {'FILES.md','AGENTS.md'})
            self.assertEqual(schema['properties']['seen_files']['items']['enum'], places)
            self.assertIn('UNDERLAG/BEDOMNINGSBINDNING.json', places)
            self.assertIn('TEXT/extra.txt', places)
            # Pröva även seen_files i den faktiskt skrivna schemafilen, i BÅDA mallarna.
            node = schema['properties']['seen_files']
            small = {'type':'object','additionalProperties':False,'required':['seen_files'],'properties':{'seen_files':node}}
            values = [{'seen_files':places}, {'seen_files':[]},
                      {'seen_files':['VYER/kandidat.png (öppnad med Read)']},
                      {'seen_files':['TEXT/pahittad.txt']},
                      {'seen_files':['VYER/kandidat.png och VYER/mobil.png']},
                      {'seen_files':['KUND/PROJECT-BRIEF.md (rad 1–10)']}]
            self.assertEqual(self.native(small, values), [True,True,False,False,False,False])
            self.assertEqual(kor_profil.laddad_fil(r, 'kritik/SCHEMA-'+mall+'.json'), original)
            # Båda använder den aktiva dialekten; inga villkorliga nyckelord smygs in.
            self.assertEqual(self.native({'type':'object','additionalProperties':False,'required':['r'],
                                         'properties':{'r':schema['properties']['referensjamforelser']}},
                                        [{'r':[self.comparison('REFERENSER/referens.png')]}]), [True])

    def test_exakta_separata_par_godtas_prosa_roll_och_uppdiktat_vagras(self):
        answer, binding, receipt = self.answer()
        answer['referensjamforelser'].append(self.comparison('REFERENSER/annan.png', 'VYER/mobil.png'))
        self.assertEqual(kb.dom(answer, binding, self.d, receipt), 'ok')
        variants = [answer]
        for array, key, bad in [
            ('referensjamforelser','kandidatbild','VYER/kandidat.png och VYER/mobil.png'),
            ('referensjamforelser','referensbild','REFERENSER/referens.png (1x1)'),
            ('dagensjamforelser','dagensbild','DAGENS/fore.png (källa och tid)'),
            ('referensjamforelser','kandidatbild','REFERENSER/referens.png'),
            ('referensjamforelser','referensbild','DAGENS/fore.png'),
            ('dagensjamforelser','dagensbild','REFERENSER/referens.png'),
            ('referensjamforelser','kalla','uppdiktad'),
            ('referensjamforelser','tid','ny tid'),
            ('referensjamforelser','vy','sammanfogad vy')]:
            changed = copy.deepcopy(answer); changed[array][0][key] = bad
            self.assertNotEqual(kb.dom(changed, binding, self.d, receipt), 'ok')
            variants.append(changed)
        self.assertEqual(self.native(self.schema(), variants), [True]+[False]*9)

    def test_giltiga_metadata_fran_fel_bild_stoppas_fortsatt_av_dom(self):
        answer, binding, receipt = self.answer()
        answer['referensjamforelser'][0]['kalla'] = 'syntetisk annan'
        # Enum är INTE ett tuplebevis: befintlig semantisk kontroll krävs fortfarande.
        self.assertEqual(self.native(self.schema(), [answer]), [True])
        self.assertIn('proveniens', kb.dom(answer, binding, self.d, receipt))

    def test_utan_dagens_bara_tom_lista_utan_tom_enum(self):
        self.d['bilder'] = [b for b in self.d['bilder'] if b['roll'] != 'dagens']
        answer, _, _ = self.answer()
        bad = copy.deepcopy(answer)
        bad['dagensjamforelser'] = [{'kandidatbild':'VYER/kandidat.png','dagensbild':'DAGENS/pahittad.png',
                                   **{k:'saknas' for k in ('kalla','tid','vy','drag','observation','konsekvens','beslut_och_skal')}}]
        self.assertEqual(self.schema()['properties']['dagensjamforelser']['maxItems'], 0)
        self.assertEqual(self.native(self.schema(), [answer, bad]), [True, False])

    def test_83_bilder_approved_och_read_laker_inte_sammansatt_bildfalt(self):
        for i in range(83-len(self.d['bilder'])):
            row = copy.deepcopy(self.d['bilder'][0]); row['plats'] = f'VYER/extra-{i}.png'
            self.d['bilder'].append(row)
        answer, binding, receipt = self.answer()
        self.assertEqual(len(receipt['images']['delivered_or_opened']), 83)
        self.assertEqual(kb.dom(answer, binding, self.d, receipt), 'ok')
        answer['referensjamforelser'][0]['kandidatbild'] = 'VYER/kandidat.png och VYER/mobil.png (/första vy)'
        self.assertEqual(kb.dom(answer, binding, self.d, receipt), 'ogiltig jämförelse: bild saknas i bundet manifest')
        self.assertEqual(self.native(self.schema(), [answer]), [False])

    def test_seen_enum_bevisar_inte_bildlasning(self):
        answer, binding, receipt = self.answer()
        schema = json.loads(kor_profil.bind_sedda_filer(json.dumps(self.schema()),
                            [{'plats':b['plats']} for b in self.d['bilder']]))
        self.assertEqual(self.native(schema, [answer]), [True])
        receipt['images']['delivered_or_opened'] = []
        self.assertIn('Runtime saknar belagd', kb.dom(answer, binding, self.d, receipt))

    def test_seen_schema_ryms_inte_eller_saknas_vagras(self):
        schema = self.schema()
        with self.assertRaisesRegex(kor_profil.Vagrad, 'ryms inte'):
            kor_profil.bind_sedda_filer(json.dumps(schema), [{'plats':'TEXT/'+'a'*201+'.txt'}])
        del schema['properties']['seen_files']
        with self.assertRaisesRegex(kor_profil.Vagrad, 'saknar seen_files'):
            kor_profil.bind_sedda_filer(json.dumps(schema), [])

    def test_trasig_mall_eller_overskriden_langd_vagras_fore_start(self):
        schema = json.loads((ROT/'kritik/SCHEMA-renderingslasning.json').read_text())
        del schema['properties']['referensjamforelser']['items']['properties']['referensbild']
        with self.assertRaises(kor_profil.Vagrad):
            kor_profil.bind_bildschema(json.dumps(schema), self.d)
        self.d['bilder'][1]['kalla'] = 'x'*2001
        with self.assertRaisesRegex(kor_profil.Vagrad, 'ryms inte'):
            self.schema()


if __name__ == '__main__':
    unittest.main()
