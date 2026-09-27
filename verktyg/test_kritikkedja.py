"""Semantisk rapportkedja r3 med faktiskt laddade syntetiska filer. Ingen modellkörning."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import kritikbevis as kb
import kvalitetsbild as kbild
import ladda_steg
from test_kritikbevis import bildfixture, ROT

class Kedja(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.k=self.root/'kund';self.d=bildfixture(self.k);(self.k/'PROJECT-BRIEF.md').write_text('syntetisk brief')
        self.l=self.root/'laddning';ladda_steg.ladda(ROT,'kritik',self.l,kund=self.k);self.lp=self.l/'LADDNING.json';self.binding,self.d=kb.ur_laddning(self.lp)
        self.run=self.root/'run';self.run.mkdir();(self.run/'strom.jsonl').write_text('{"syntetiskt":true}\n');(self.run/'start.json').write_text('{"syntetiskt":true}')
        self.answer={'kriterieversion':kb.VERSION,'bedomningsbindning':self.binding,'verdict':'approved','blocking_findings':[],'could_not_review':[],'seen_files':[b['plats'] for b in self.d['bilder']],'referensjamforelser':[{'kandidatbild':'VYER/kandidat.png','referensbild':'REFERENSER/referens.png','kalla':'syntetisk testbild','tid':'2026-09-27T00:00:00Z','vy':'1x1','drag':'kontraktsprov','observation':'syntetisk','konsekvens':'ingen produktdom','beslut_och_skal':'syntetiskt'}]}
        self.receipt={'outcome':'svar_giltigt','parameters':{'executor':'claude'},'images':{'complete':True,'delivered_or_opened':self.answer['seen_files'],'how':'opened with Read (from the stream)'},'underlag':[{'place':b['plats'],'source_sha256':b['sha256'],'copy_sha256':b['sha256']} for b in self.d['bilder']]}
        self.post={'profil':'kritik','mall':'renderingslasning','bedomningsbindning':copy.deepcopy(self.binding),'bildbedomningsunderlag':copy.deepcopy(self.d),'laddning':{'fil':str(self.lp),'sha256':kb.stegbevis.sha(self.lp)},'bindning':{}}
        self.save()
    def tearDown(self):self.tmp.cleanup()
    def save(self):
        (self.run/'svar.json').write_text(json.dumps(self.answer));self.receipt['outputs']={n:{'sha256':kb.stegbevis.sha(self.run/n)} for n in ('svar.json','strom.jsonl','start.json')};(self.run/'KVITTO.json').write_text(json.dumps(self.receipt));digest=kb.stegbevis.sha(self.run/'KVITTO.json');(self.run/'KVITTO.sha256').write_text(digest+'  KVITTO.json\n');self.post['runtime_kvitto_sha256']=digest
    def entry(self):return {'run':str(self.run),'kvitto':self.receipt,'utfall':'svar_giltigt','svar':self.answer}
    def status(self):return kbild.bevisstatus(self.post,self.entry(),None)
    def test_reell_laddkedja_och_forgat_par_post_svar(self):
        self.assertEqual(self.status(),'ok')
        self.post['bedomningsbindning']['rackvidd']='utökad i efterhand';self.answer['bedomningsbindning']=self.post['bedomningsbindning'];self.save()
        self.assertIn('faktiskt laddat',self.status())
    def test_runtime_hash_och_rabild_maste_stamma(self):
        (self.run/'KVITTO.sha256').unlink();self.assertIn('integritetsrad',self.status());self.save()
        self.post['runtime_kvitto_sha256']='0'*64;self.assertIn('körningens bindning',self.status());self.save()
        self.receipt['underlag'][0]['copy_sha256']='0'*64;self.save();self.assertIn('Runtime-bildens hash',self.status())
        self.receipt['underlag'][0]['copy_sha256']=self.d['bilder'][0]['sha256'];self.save();(self.run/'strom.jsonl').write_text('ändrad');self.assertIn('strom.jsonl',self.status())
    def test_laddad_bildrad_maste_finnas_och_ha_samma_hash(self):
        r=json.loads(self.lp.read_text());r['underlag']=[row for row in r['underlag'] if row['fil']!='referens.png'];self.lp.write_text(json.dumps(r));self.post['laddning']['sha256']=kb.stegbevis.sha(self.lp)
        self.assertIn('bild saknas/avviker',self.status())
    def test_femsekunder_ar_inte_kvalitetsdom(self):
        self.post['mall']='femsekunderstest';self.assertTrue(self.status().startswith('begriplighetsprov'))
    def test_rejected_och_ej_bedombart_redovisas_som_verkliga_domar(self):
        for verdict in ('rejected','ej_bedombart'):
            self.answer['verdict']=verdict;self.answer['blocking_findings']=[{'finding':'konkret yrkesbrist'}] if verdict=='rejected' else [];self.answer['could_not_review']=['mobil saknas'] if verdict=='ej_bedombart' else [];self.save()
            entry={**self.entry(),'fil':'syntetisk.json','profil':'kritik','etikett':'syntetisk','laddning':'a'*64,'steg':'kritik','status':self.status(),'mall':'renderingslasning'}
            text=kbild.rendera([entry],None)
            self.assertIn('"'+verdict+'"',text);self.assertNotIn('Ingen kritik- eller läsarsession',text)
            if verdict=='rejected':self.assertIn('konkret yrkesbrist',text)
            else:self.assertIn('mobil saknas',text)
    def test_dagens_roll_och_fri_tackning_na_vagras(self):
        d=copy.deepcopy(self.d);old=copy.deepcopy(d['bilder'][0]);old.update(fil='dagens.png',plats='DAGENS/start.png',roll='dagens',tacker=[]);(self.k/'dagens.png').write_bytes((self.k/'kandidat.png').read_bytes());d['bilder'].append(old);kb.manifest(d,self.k)
        d['tackning'][0]['na_skal']='bilder hanns inte med'
        with self.assertRaisesRegex(kb.Vagrad,'fördefinierade'):kb.manifest(d,self.k)
        req=self.k/'BEVISKRAV.json';r=json.loads(req.read_text());r['bildbedomning']['typ']='produkt';req.write_text(json.dumps(r));d=copy.deepcopy(self.d);d['krav_sha256']=kb.stegbevis.sha(req)
        with self.assertRaisesRegex(kb.Vagrad,'kategorier'):kb.manifest(d,self.k)

if __name__=='__main__':unittest.main()
