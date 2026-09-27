"""Signal -> vanlig import -> research-underlag -> kvittens. Inga nätanrop eller verkliga kunder."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import kundstart as ks
import intervju as iv
from test_kundstart import paket

class Konsumtion(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.k=Path(self.tmp.name)/'kund';self.k.mkdir();self.base='http://127.0.0.1:1'
        ks.spara_kundstart(self.k,{'schema':1,'arende_id':'ar_test12345678','bas_url':self.base,'testdialog':True,'hamtat':[]})
        self.p=paket();self.p['material']=[]
        self.p['signal']={'id':'ar_test12345678:7','arende_id':'ar_test12345678','revision':7,'typ':'inlamning'}
        self.p['behov']=[{'id':'BEH3_1','nyckel':'delade_resurser','status':'oppen','citat':'Vi delar ett rum','kalla_fraga':'A1','revision':3}]
        self.p['tackning']=[{'nyckel':'marknadsforing','status':'inte_undersokt'}]
        self.p['omgangar'].append({'nr':3,'fragor':[{'id':'BEH3_1','nyckel':'delade_resurser','omrade':'H','text':'Vilket rum delas?','paverkar':'kapacitet'}], 'svar':[{'fraga_id':'BEH3_1','text':'Det enda rummet.','revision':7,'mottaget':'2026-09-27T15:00:00Z'}]})
        self.calls=[];self.ack=[];self.closed=False;self.lose=False
    def tearDown(self):self.tmp.cleanup()
    def api(self,bas,key,metod,vag,kropp=None,bypass=None,rå=False):
        self.calls.append((metod,vag))
        if vag.startswith('/api/intern/signaler'):
            return {'schema':'kundstart-signaler/1','signaler':[] if self.closed else [self.p['signal']],'cursor':None}
        if vag.endswith('/export'):return json.dumps(self.p,indent=2).encode() if rå else self.p
        if vag.endswith('/kvittens'):
            self.ack.append(kropp);self.closed=True
            if self.lose:self.lose=False;raise ks.Vagrad('syntetiskt tappat svar efter sparad kvittens')
            return {'ok':True}
        if vag.endswith('/returfragor'):return {'ok':True,'fragor':['RET8_1']}
        raise AssertionError(vag)
    def test_import_behov_idempotens_och_farsk_utforare_efter_tappat_ack(self):
        with patch.object(ks,'anrop',self.api):
            self.lose=True
            with self.assertRaisesRegex(ks.Vagrad,'tappat'):ks.konsumera(self.k,self.base,'ingen-hemlighet',None,'forsta')
            first=(self.k/'KUNDSTART/signal-7/EXPORT.json').read_bytes()
            self.p['exporterad']='senare klockslag får inte ändra kvittenshashen'
            d,r=ks.konsumera(self.k,self.base,'ingen-hemlighet',None,'farsk')
            self.assertEqual(r['lage'],'kvitterad');self.assertEqual(r['ansvarig'],'forsta')
            self.assertEqual(self.ack[0],self.ack[1]);self.assertEqual(len([c for c in self.calls if c[1].endswith('/export')]),1)
            self.assertEqual(first,(self.k/'KUNDSTART/signal-7/EXPORT.json').read_bytes())
            s=iv.las(self.k);self.assertEqual(len([x for x in s['svar'] if x['fraga_id']=='BEH3_1']),1)
            research=(self.k/'research-intervju.md').read_text();self.assertIn('Vi delar ett rum',research);self.assertIn('marknadsforing: inte_undersokt',research)
            task=json.loads((self.k/'KUNDSTART-ARBETSUPPGIFT.json').read_text());self.assertIn('återstår',task['lage'])
            self.assertEqual(ks.konsumera(self.k,self.base,'x',None,'farsk')[1]['lage'],'inget nytt')
    def test_sen_rattelse_och_returfraga_samma_arende(self):
        with patch.object(ks,'anrop',self.api):
            ks.konsumera(self.k,self.base,'x',None,'ansvarig')
            self.closed=False;self.p['arende']['revision']=9;self.p['signal']['revision']=9;self.p['signal']['id']='ar_test12345678:9'
            self.p['rattelser_fakta'].append({'nyckel':'ton','varde':'Sakligt','kalla':'kundstart rättelse rev 9','omrade':'E'})
            self.p['fakta_ai'].append({'nyckel':'ton','varde':'Lekfullt','kalla':'kundstart AI rev 8','omrade':'E'})
            ks.konsumera(self.k,self.base,'x',None,'ansvarig')
            facts=[x for x in iv.las(self.k)['fakta'] if x['nyckel']=='ton'];self.assertEqual([x['varde'] for x in facts],['Sakligt'])
            q=self.k/'fragor.json';q.write_text(json.dumps({'idempotens':'test-retur-1','bas_revision':7,'fragor':[{'nyckel':'delade_resurser','text':'När används rummet?','paverkar':'kapacitet'}]}))
            with self.assertRaisesRegex(ks.Vagrad,'senast'):ks.returfragor(self.k,self.base,'x',None,q,'ansvarig')
            body=json.loads(q.read_text());body['bas_revision']=9;q.write_text(json.dumps(body));ks.returfragor(self.k,self.base,'x',None,q,'ansvarig')
            self.assertEqual(self.calls[-1][1],'/api/intern/arenden/ar_test12345678/returfragor')
    def test_nyare_signal_ersatter_gammalt_tappat_ack_utan_oandlig_retry(self):
        with patch.object(ks,'anrop',self.api):
            self.lose=True
            with self.assertRaises(ks.Vagrad):ks.konsumera(self.k,self.base,'x',None,'ansvarig')
            self.closed=False;self.p['arende']['revision']=9;self.p['signal']['revision']=9;self.p['signal']['id']='ar_test12345678:9'
            ks.konsumera(self.k,self.base,'x',None,'ansvarig')
            old=json.loads((self.k/'KUNDSTART/signal-7/KONSUMTION.json').read_text());self.assertEqual(old['lage'],'ersatt av nyare import');self.assertEqual(old['ersatt_av'],'ar_test12345678:9')
            self.assertEqual(ks.konsumera(self.k,self.base,'x',None,'ansvarig')[1]['lage'],'inget nytt');self.assertEqual(len(self.ack),2)
    def test_okant_arende_registreras_aldrig(self):
        self.p['signal']['arende_id']='ar_okand123456'
        with patch.object(ks,'anrop',self.api):self.assertEqual(ks.konsumera(self.k,self.base,'x',None,'ansvarig')[1]['lage'],'inget nytt')
        self.assertFalse((self.k/'INTERVJU.json').exists());self.assertEqual(len(self.calls),1)
    def test_lasning_ar_explicit_och_ett_annat_material_vagras(self):
        m=self.k/'KUNDSTART/material';m.mkdir(parents=True);p=m/'m_12345678-original.txt';p.write_text('sanning')
        proof=self.k/'lasbevis.json';proof.write_text(json.dumps({'fil':str(p),'sha256':ks.hashlib.sha256(p.read_bytes()).hexdigest(),'resultat':'Läst innehåll och noterad gammal uppgift.'}))
        with patch.object(ks,'anrop',self.api):
            with self.assertRaisesRegex(ks.Vagrad,'inte hämtat'):ks.material_last(self.k,self.base,'x',None,'m_87654321',proof,'ansvarig')
        self.assertEqual(self.calls,[])
    def test_dubbel_konsument_lases_och_pagination_full_scan(self):
        with ks.konsumtionslas(self.k):
            with self.assertRaisesRegex(ks.Vagrad,'redan'):ks.konsumera(self.k,self.base,'x',None,'andra')
        pages=[]
        def api(b,k,m,v,*a,**kw):
            pages.append(v);return {'schema':'kundstart-signaler/1','signaler':[{'id':v}],'cursor':'nasta' if '?' not in v else None}
        with patch.object(ks,'anrop',api):
            self.assertEqual(len(ks.signaler(self.base,'x',None)),2);ks.signaler(self.base,'x',None)
        self.assertEqual(pages[0],pages[2]);self.assertIn('cursor=nasta',pages[1])

if __name__=='__main__':unittest.main()
