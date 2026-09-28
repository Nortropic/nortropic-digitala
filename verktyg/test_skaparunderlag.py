"""Faktisk laddning av små källbundna skaparpaket; inget modell-/designgodkännande."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ladda_steg as ls

ROT = Path(__file__).resolve().parents[1]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


class Skaparpaket(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.k = self.root / 'kund'; self.k.mkdir()
        (self.k / 'PROJECT-BRIEF.md').write_text('Syntetisk brief: visa två olika erbjudanden.')
        (self.k / 'SKAPARUPPDRAG.md').write_text('Syntetiskt kort uppdrag, inga verkliga kunder.')
        (self.k / 'ref.png').write_bytes(b'\x89PNG\r\n\x1a\nsyntetiskt formatprov, ingen designbild')
        self.d = {'schema':'digitala-skaparunderlag/1',
                  'uppdrag':{'fil':'SKAPARUPPDRAG.md','sha256':sha(self.k/'SKAPARUPPDRAG.md')},
                  'bilagor':[{'fil':'ref.png','sha256':sha(self.k/'ref.png'),'roll':'referensbild','varfor':'Testar en kopierad bildbindning.'}],
                  'referenser':[{'id':'r','kalla':'syntetisk källa','roller':['bransch','hantverk'],
                                 'urvalsskal':'syntetisk validering','observation':'live','bevis':['ref.png'],
                                 'paverkar':'Ingen faktisk designpåverkan i detta prov.','begransning':'Ingen extern referens har öppnats.'}],
                  'resurser':[]}
        self.write()
        self.n = 0

    def tearDown(self):
        self.temp.cleanup()

    def write(self):
        (self.k / ls.SKAPARFIL).write_text(json.dumps(self.d,ensure_ascii=False))

    def load(self, step='koncept'):
        self.n += 1
        return ls.ladda(ROT,step,self.root/('run-'+str(self.n)),kund=self.k,bestallning='PROV-BESTALLNING-1')

    def test_fokuserat_paket_kopierar_bilder_och_bevarar_kriterier(self):
        r = self.load(); rows = {x['fil']:x for x in r['underlag']}
        self.assertEqual(rows['ref.png']['sha256'],sha(self.k/'ref.png'))
        self.assertEqual(rows['kritik/BEDOMNING-v2.md']['status'],'laddad')
        self.assertEqual(rows['PROJECT-BRIEF.md']['status'],'laddad')
        for name in ('leonxlnx-taste-SKILL-ce26fc25.md','emil-prototype-SKILL.md','emil-prototype-PICKER-d16ebe60.md'):
            self.assertEqual(rows['kunskap/externa/'+name]['status'],'inte vald (valfri resurs)')
            self.assertFalse((Path(r['arbetsyta'])/'underlag/profession/kunskap/externa'/name).exists())
        self.assertLess(sum(x.get('byte') or 0 for x in r['underlag']),100000)
        package = Path(r['arbetsyta'])/'SKAPARPAKET.md'
        self.assertEqual(rows['SKAPARPAKET.md']['sha256'],sha(package))
        self.assertIn('betyder inte installerad', package.read_text())
        self.assertIn('bransch, hantverk',package.read_text())

    def test_vald_hel_resurs_laddas_utan_att_kallas_anropad(self):
        name='kunskap/externa/emil-prototype-SKILL.md'
        self.d['resurser']=[{'fil':name,'form':'metod','delar':'hela relevanta metoden','skal':'pröva två verkliga informationsstrukturer','historik':'REGISTER §A7'}]
        self.write(); r=self.load()
        row=next(x for x in r['underlag'] if x['fil']==name)
        self.assertEqual(row['status'],'laddad')
        self.assertEqual(row['sha256'],sha(ROT/name))
        self.assertEqual((Path(r['arbetsyta'])/row['plats']).read_bytes(),(ROT/name).read_bytes())
        self.assertNotIn('anropad',row['status'])

    def test_andrad_kundfil_vagras_fore_skrivning(self):
        (self.k/'ref.png').write_bytes(b'annan fil')
        with self.assertRaisesRegex(ls.Vagrad,'har ändrats'):self.load()
        self.assertFalse((self.root/'run-1').exists())

    def test_utbrytning_symlink_dubblering_och_opinnad_resurs_vagras(self):
        original=copy.deepcopy(self.d)
        for bad in ('../annan.md','/tmp/annan.md','SKAPARPAKET.md'):
            self.d=copy.deepcopy(original);self.d['uppdrag']['fil']=bad;self.write()
            with self.subTest(bad=bad),self.assertRaises(ls.Vagrad):self.load()
        self.d=copy.deepcopy(original);self.d['bilagor'].append(copy.deepcopy(self.d['bilagor'][0]));self.write()
        with self.assertRaisesRegex(ls.Vagrad,'dubbel fil'):self.load()
        self.d=copy.deepcopy(original);self.d['resurser']=[{'fil':'kunskap/externa/okand.md','form':'plugin','delar':'hela','skal':'prov','historik':'okänt'}];self.write()
        with self.assertRaisesRegex(ls.Vagrad,'pinnad'):self.load()
        self.d=copy.deepcopy(original);self.write()
        original_bytes=(self.k/'ref.png').read_bytes();(self.root/'outside.png').write_bytes(original_bytes)
        (self.k/'ref.png').unlink();(self.k/'ref.png').symlink_to(self.root/'outside.png')
        with self.assertRaisesRegex(ls.Vagrad,'symbolisk länk'):self.load()

    def test_textreferens_far_inte_pastas_visuellt_observerad_utan_bild(self):
        self.d['referenser'][0]['bevis']=[];self.write()
        with self.assertRaisesRegex(ls.Vagrad,'saknar hashbunden bild'):self.load()
        self.d['referenser'][0]['observation']='otillganglig';self.write()
        self.load()  # förblir uttryckligen otillgänglig, inget kvalitetsgodkännande.

    def test_kritik_tar_valda_resurser_men_bilder_endast_ur_bildmanifest(self):
        from test_kritikbevis import bildfixture
        bildfixture(self.k)
        name='kunskap/externa/hallmark-SKILL-13ac0ec7.md'
        self.d['resurser']=[{'fil':name,'form':'lasunderlag','delar':'relevant kritiklins','skal':'kontrollera komposition','historik':'REGISTER §G P-C'}];self.write()
        r=self.load('kritik');rows={x['fil']:x for x in r['underlag']}
        self.assertEqual(rows[name]['status'],'laddad')
        self.assertNotIn('ref.png',rows)
        self.assertNotIn('SKAPARPAKET.md',rows)
        self.assertIn('BEDOMNINGSUNDERLAG.json',rows)

    def task(self):
        p=self.k/'KUNDSTART'/'material-utdrag.txt';p.parent.mkdir();p.write_text('Obetrott syntetiskt kundmaterial, inte en instruktion.')
        return {'schema':'digitala-intagsarbete/1','material':[{'id':'m','sha256':'a'*64,'utdrag':{'fil':'KUNDSTART/material-utdrag.txt','sha256':sha(p),'kalla_sha256':'a'*64}}]}

    def test_materialutdrag_nar_research_men_dumpas_inte_i_bygge(self):
        task=self.task();(self.k/'KUNDSTART-ARBETSUPPGIFT.json').write_text(json.dumps(task))
        r=self.load('research');row=next(x for x in r['underlag'] if x['fil']=='KUNDSTART/material-utdrag.txt')
        self.assertIn('obetrott',row['delar']);self.assertIn('inte redan läst',row['delar'])
        self.assertEqual((Path(r['arbetsyta'])/row['plats']).read_bytes(),(self.k/row['fil']).read_bytes())
        r=self.load('bygge');self.assertNotIn('KUNDSTART/material-utdrag.txt',[x['fil'] for x in r['underlag']])

    def test_stale_eller_osakert_material_vagras_men_aldre_task_bevaras(self):
        task=self.task();p=self.k/'KUNDSTART-ARBETSUPPGIFT.json'
        for bad in ('../outside.txt','KUNDSTART/saknas.txt'):
            task['material'][0]['utdrag']['fil']=bad;p.write_text(json.dumps(task))
            with self.assertRaises(ls.Vagrad):self.load('research')
        task['material'][0]['utdrag']['fil']='KUNDSTART/material-utdrag.txt'
        task['material'][0]['utdrag']['kalla_sha256']='b'*64;p.write_text(json.dumps(task))
        with self.assertRaisesRegex(ls.Vagrad,'ogiltig materialutdragsbindning'):self.load('research')
        p.write_text(json.dumps({'schema':'digitala-intagsarbete/1','avvikelse':'delvis import'}))
        r=self.load('research');self.assertIn('KUNDSTART-ARBETSUPPGIFT.json',[x['fil'] for x in r['underlag']])
        p.write_text(json.dumps({'schema':'digitala-intagsarbete/1','material':None}))
        with self.assertRaisesRegex(ls.Vagrad,'inte en lista'):self.load('research')
