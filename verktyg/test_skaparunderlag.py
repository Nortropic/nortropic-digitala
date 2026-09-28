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

    def test_brief_far_aktuellt_materialutdrag_utan_pastadd_lasning(self):
        task=self.task()
        current=self.k/'KUNDSTART'/'signal-2'/'utdrag.txt';current.parent.mkdir()
        current.write_text('Obetrott aktuellt kundmaterial. Uppgiften behöver kontrolleras.')
        task.update(exportrevision=2)
        task['material'][0].update(lasstatus='extraherad',utdrag={
            'fil':'KUNDSTART/signal-2/utdrag.txt','sha256':sha(current),'kalla_sha256':'a'*64})
        task_path=self.k/'KUNDSTART-ARBETSUPPGIFT.json';task_path.write_text(json.dumps(task))
        original_task=task_path.read_bytes()
        (self.k/'research.md').write_text('Intern syntes ersätter inte aktuell kundkälla.')
        r=self.load('brief');rows={x['fil']:x for x in r['underlag']}
        row=rows['KUNDSTART/signal-2/utdrag.txt']
        self.assertNotIn('KUNDSTART/material-utdrag.txt',rows)
        self.assertEqual(row['sha256'],sha(current))
        self.assertEqual((Path(r['arbetsyta'])/row['plats']).read_bytes(),current.read_bytes())
        self.assertEqual(row['status'],'laddad')
        self.assertIn('obetrott',row['delar']);self.assertIn('inte redan läst',row['delar'])
        self.assertIn('originalsha256 '+'a'*64,row['delar'])
        self.assertEqual(task_path.read_bytes(),original_task)
        self.assertEqual(json.loads(task_path.read_text())['material'][0]['lasstatus'],'extraherad')

    def test_brief_vagrar_andrat_material_fore_skrivning(self):
        task=self.task();task_path=self.k/'KUNDSTART-ARBETSUPPGIFT.json'
        task_path.write_text(json.dumps(task));original_task=task_path.read_bytes()
        (self.k/'research.md').write_text('Syntetisk research.')
        (self.k/'KUNDSTART/material-utdrag.txt').write_text('Ändrat efter intagsbindningen.')
        with self.assertRaisesRegex(ls.Vagrad,'materialutdrag saknas eller har ändrats'):self.load('brief')
        self.assertFalse((self.root/'run-1').exists())
        self.assertEqual(task_path.read_bytes(),original_task)

    def historical_resource(self):
        name='kunskap/externa/historisk-SKILL.md'
        self.d['resurser']=[{'fil':name,'form':'metod','delar':'hela','skal':'Syntetiskt val','historik':'Syntetisk tidigare version'}]
        self.write()
        fixture=self.root/'professionsrot';source=fixture/name;source.parent.mkdir(parents=True)
        source.write_text('Syntetisk professionsresurs.')
        return name,fixture.resolve(),source

    def test_borttagen_historisk_resurs_stoppar_inte_brief_eller_aktiveras(self):
        name,fixture,source=self.historical_resource();pins={name:sha(source)}
        ls.skaparplan(self.k.resolve(),fixture,pins)  # det tidigare valet var giltigt
        source.unlink()
        with self.assertRaisesRegex(ls.Vagrad,'pinnad professionsfil'):ls.skaparplan(self.k.resolve(),fixture,pins)
        (self.k/'research.md').write_text('Aktuell research.')
        original=(self.k/ls.SKAPARFIL).read_bytes();r=self.load('brief')
        package=next(x for x in r['underlag'] if x['fil']==ls.SKAPARFIL)
        self.assertIn('inaktuellt historiskt resursval; inte laddat',package['delar'])
        self.assertIn('utan valauktoritet',package['delar'])
        self.assertEqual((Path(r['arbetsyta'])/package['plats']).read_bytes(),original)
        self.assertEqual((Path(r['arbetsyta'])/'underlag/kund/ref.png').read_bytes(),(self.k/'ref.png').read_bytes())
        self.assertFalse((Path(r['arbetsyta'])/'underlag/profession'/name).exists())
        self.assertFalse((Path(r['arbetsyta'])/'SKAPARPAKET.md').exists())
        with self.assertRaisesRegex(ls.Vagrad,'omprova.*--steg brief'):self.load('koncept')

    def test_ompinnad_tillganglig_resurs_ar_inte_i_sig_en_historisk_blockering(self):
        name,fixture,source=self.historical_resource()
        source.write_text('Ny läst och beslutad professionsversion.')
        pins={name:sha(source)}
        _,_,strict=ls.skaparplan(self.k.resolve(),fixture,pins)
        _,_,historical=ls.skaparplan(self.k.resolve(),fixture,pins,historiskt=True)
        self.assertIn(name,strict);self.assertEqual(historical,{})

    def test_historiskt_felaktigt_paket_laddas_som_original_inte_nytt_val(self):
        (self.k/'research.md').write_text('Aktuell research.')
        original=copy.deepcopy(self.d)
        for mode in ('schema','form'):
            self.d=copy.deepcopy(original)
            if mode=='schema':self.d['schema']='digitala-skaparunderlag/0'
            else:self.d['bilagor'][0]['roll']='historisk-okand-roll'
            self.write();raw=(self.k/ls.SKAPARFIL).read_bytes()
            with self.subTest(mode=mode):
                r=self.load('brief');rows={x['fil']:x for x in r['underlag']}
                self.assertIn('utan valauktoritet',rows[ls.SKAPARFIL]['delar'])
                self.assertEqual((Path(r['arbetsyta'])/rows[ls.SKAPARFIL]['plats']).read_bytes(),raw)
                self.assertNotIn('ref.png',rows)
                self.assertFalse((Path(r['arbetsyta'])/'SKAPARPAKET.md').exists())
                with self.assertRaisesRegex(ls.Vagrad,'omprova.*--steg brief'):self.load('koncept')

    def test_historik_foljer_inte_osaker_kalla_och_paketlank_vagras(self):
        (self.k/'research.md').write_text('Aktuell research.')
        outside=self.root/'outside.png';outside.write_bytes((self.k/'ref.png').read_bytes())
        (self.k/'ref.png').unlink();(self.k/'ref.png').symlink_to(outside)
        r=self.load('brief');rows={x['fil']:x for x in r['underlag']}
        self.assertIn('symbolisk länk',rows[ls.SKAPARFIL]['delar'])
        self.assertNotIn('ref.png',rows)
        self.assertFalse((Path(r['arbetsyta'])/'underlag/kund/ref.png').exists())
        raw=(self.k/ls.SKAPARFIL).read_bytes();outside_package=self.root/'paket.json';outside_package.write_bytes(raw)
        (self.k/ls.SKAPARFIL).unlink();(self.k/ls.SKAPARFIL).symlink_to(outside_package)
        with self.assertRaisesRegex(ls.Vagrad,'symbolisk länk'):self.load('brief')

    def test_stale_historisk_fil_observeras_utan_ny_valbindning(self):
        (self.k/'research.md').write_text('Aktuell research.')
        old=self.d['bilagor'][0]['sha256'];(self.k/'ref.png').write_bytes(b'Annans senare material')
        r=self.load('brief');row=next(x for x in r['underlag'] if x['fil']=='ref.png')
        self.assertEqual(row['sha256'],old)
        self.assertEqual(row['aktuell_sha256'],sha(self.k/'ref.png'))
        self.assertIsNone(row['plats']);self.assertIn('inte laddat',row['status'])
        self.assertFalse((Path(r['arbetsyta'])/'underlag/kund/ref.png').exists())
        with self.assertRaisesRegex(ls.Vagrad,'har ändrats'):self.load('koncept')

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
