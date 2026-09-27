import base64
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import kritikbevis as kb
import ladda_steg
import kor_profil
import kvalitetsbild
from types import SimpleNamespace

ROT=Path(__file__).resolve().parent.parent

def bildfixture(kund):
    kund=Path(kund);kund.mkdir(exist_ok=True)
    # Synthetic one-pixel image: validates transport, never evidence of product quality.
    png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl6qFcAAAAASUVORK5CYII=')
    (kund/'kandidat.png').write_bytes(png);(kund/'referens.png').write_bytes(png)
    candidate=kund/'kandidat.txt';candidate.write_text('syntetisk dokumentkandidat')
    d={'schema':'digitala-bildbedomning/2','kriterieversion':kb.VERSION,'kriterier_sha256':hashlib.sha256((ROT/kb.KONTRAKT).read_bytes()).hexdigest(),'rackvidd':'syntetiskt kontraktsprov, ingen visuell produktdom','sammanhang':{'kandidat':{'typ':'filer','filer':[{'fil':str(candidate.resolve()),'sha256':hashlib.sha256(candidate.read_bytes()).hexdigest()}]},'miljo':{'namn':'isolerat prov','typ':'dokument'},'konfiguration':{'filer':[],'ej_tillampligt':'endast schemaprov'}},'tackning':[{'id':'forsta','beskrivning':'syntetisk första vy'}],'bilder':[]}
    for role,fil,place in [('kandidat','kandidat.png','VYER/kandidat.png'),('referens','referens.png','REFERENSER/referens.png')]:
        d['bilder'].append({'fil':fil,'sha256':hashlib.sha256(png).hexdigest(),'plats':place,'roll':role,'kalla':'syntetisk testbild','tid':'2026-09-27T00:00:00Z','vy':'1x1','drag':'kontraktsprov','tacker':['forsta'] if role=='kandidat' else []})
    req={'schema':'digitala-beviskrav/1','version':'syntetiskt-v1','bildbedomning':{'typ':'komp','faststalld_av':'syntetisk provledare','faststalld_tid':'2026-09-27T00:00:00Z','tackning':copy.deepcopy(d['tackning'])}}
    kr=kund/'BEVISKRAV.json';kr.write_text(json.dumps(req));d['kravfil']='BEVISKRAV.json';d['krav_sha256']=hashlib.sha256(kr.read_bytes()).hexdigest()
    (kund/kb.BILDFIL).write_text(json.dumps(d,ensure_ascii=False))
    return d

class Kritik(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.k=self.root/'kund';self.d=bildfixture(self.k)
    def tearDown(self):self.tmp.cleanup()
    def test_bildmanifest_negativa_och_positivt(self):
        kb.manifest(self.d,self.k)
        for field in ['kalla','tid','vy','sha256']:
            d=copy.deepcopy(self.d);d['bilder'][1].pop(field)
            with self.assertRaises(kb.Vagrad):kb.manifest(d,self.k)
        d=copy.deepcopy(self.d);d['bilder']=d['bilder'][:1]
        with self.assertRaisesRegex(kb.Vagrad,'referensbilder'):kb.manifest(d,self.k)
        d=copy.deepcopy(self.d);d['tackning'].append({'id':'saknas','beskrivning':'mobil felläge'})
        with self.assertRaisesRegex(kb.Vagrad,'fördefinierade'):kb.manifest(d,self.k)
        d['tackning'][-1]['na_skal']='den statiska kompen visar ingen sådan funktion'
        with self.assertRaisesRegex(kb.Vagrad,'fördefinierade'):kb.manifest(d,self.k)
    def test_laddare_och_profil_binder_faktiska_bilder_och_kriterier(self):
        (self.k/'PROJECT-BRIEF.md').write_text('syntetisk brief')
        r=ladda_steg.ladda(ROT,'kritik',self.root/'laddning',kund=self.k)
        self.assertTrue(any(x['fil']=='referens.png' and x['obligatorisk'] for x in r['underlag']))
        files=self.root/'files.json';files.write_text('[]');fall=self.root/'fall';fall.mkdir()
        a=SimpleNamespace(mall='renderingslasning',parameter=['NUMMER=1','ANTAL=1','VAD=syntetiskt','KUND=prov'],filer=str(files),fall=str(fall),etikett='syntetisk',torr=True,utforare='claude',modell='testmodell',tid=10)
        argv,extra=kor_profil.bygg_kritik(a,{'python':'python'},None,r,'a'*64)
        self.assertIn('REFERENSER/referens.png',extra['manifest_platser']);self.assertIn('VYER/kandidat.png',extra['manifest_platser']);self.assertEqual(extra['bedomningsbindning']['kriterier_sha256'],self.d['kriterier_sha256'])
        self.assertIn('UNDERLAG/BEDOMNING-v2.md',extra['manifest_platser'])
    def test_dom_kraver_jamforelse_proveniens_bildkvitto_bindning_och_riktigt_verdict(self):
        binding=kb.bindning(self.d,'a'*64)
        c={'kandidatbild':'VYER/kandidat.png','referensbild':'REFERENSER/referens.png','kalla':'syntetisk testbild','tid':'2026-09-27T00:00:00Z','vy':'1x1','drag':'kontraktsprov','observation':'syntetisk','konsekvens':'ingen verklig dom','beslut_och_skal':'behåll för test'}
        answer={'kriterieversion':kb.VERSION,'bedomningsbindning':binding,'verdict':'approved','blocking_findings':[],'could_not_review':[],'seen_files':[b['plats'] for b in self.d['bilder']],'referensjamforelser':[c]}
        receipt={'parameters':{'executor':'claude'},'images':{'complete':True,'delivered_or_opened':answer['seen_files'],'how':'opened with Read (from the stream)'}}
        self.assertEqual(kb.dom(answer,binding,self.d,receipt),'ok')
        self.assertEqual(kb.bildbelagg(receipt),'Read-spår för Claude')
        codex={'parameters':{'executor':'codex'},'images':{**receipt['images'],'how':'attached on the command line (read back from argv)'}}
        self.assertIn('inte självständigt',kb.bildbelagg(codex));self.assertEqual(kb.dom(answer,binding,self.d,codex),'ok')
        for change in [{'referensjamforelser':[]},{'seen_files':[]},{'bedomningsbindning':{}},{'blocking_findings':[{'finding':'yrkesbrist'}]},{'verdict':'svar_giltigt'}]:
            self.assertNotEqual(kb.dom({**answer,**change},binding,self.d,receipt),'ok')
        self.assertTrue(kb.dom({**answer,'verdict':'ej_bedombart','could_not_review':['mobilbild saknas']},binding,self.d,receipt).startswith('ej bedömbart'))
        self.assertNotEqual(kb.dom(answer,binding,self.d,{'images':{'complete':False}}),'ok')
        bad=copy.deepcopy(answer);bad['referensjamforelser'][0]['kalla']='påhittat';self.assertNotEqual(kb.dom(bad,binding,self.d,receipt),'ok')
        (self.k/'kandidat.txt').write_text('ny kandidat efter kritiken')
        self.assertTrue(kb.dom(answer,binding,self.d,receipt).startswith('inaktuell'))

if __name__=='__main__':unittest.main()
