"""Avgränsade regressioner mot GSC, offline GBP, kontaktberedskap och textsökningens bevisnivå."""
import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import sokkonsol as gsc
import verksamhetsuppgifter as vu
import lokal_synlighet as gbp
import uppfoljning as mat
import seo_kontroll as seo
import prelaunch
from test_verksamhetsuppgifter import exempel
from test_uppfoljning import matplan

class GSC(unittest.TestCase):
    def run_transport(self, statuses, command='verifiera', urls=None):
        calls=[];wait=[]
        def transport(method,url,body,headers):
            if url==gsc.TOKEN_URL:return 200,{'access_token':'syntetisk'}
            payload=json.loads(body) if body else None;calls.append((method,url,payload))
            step='inspektera' if 'index:inspect' in url else 'verifiera' if '?verificationMethod' in url else 'agare' if '/webResource/' in url else 'sitemap' if '/sitemaps/' in url else 'egenskap'
            seq=statuses.get(step,[200]);value=seq.pop(0) if len(seq)>1 else seq[0]
            code,answer=value if isinstance(value,tuple) else (value,{})
            if step=='verifiera' and code==200:answer={'id':'id','site':{'type':'SITE','identifier':'https://example.invalid/'},'owners':['a@example.invalid']}
            if step=='inspektera' and code==200:answer={'inspectionResult':{'indexStatusResult':{'verdict':'PASS','coverageState':'Submitted and indexed'}}}
            return code,answer
        rows=gsc.kor(command,exempel(fiktiv=False),'example.invalid',urls or ['/'],{'typ':'oauth','client_id':'x','client_secret':'x','refresh_token':'x'},transport,agare=['b@example.invalid'],sov=wait.append)
        return rows,calls,wait
    def test_brott_i_varje_beroende_stoppar_efterfoljande_skrivning(self):
        for step,expected in [('verifiera',['verifiera']),('agare',['verifiera','agare']),('egenskap',['verifiera','agare','egenskap'])]:
            rows,calls,wait=self.run_transport({step:[403]});self.assertEqual([r['steg'] for r in rows],expected);self.assertEqual(wait,[])
        rows,_,_=self.run_transport({});self.assertEqual([r['steg'] for r in rows],['verifiera','agare','egenskap','sitemap'])
    def test_url_identitet_och_httpfel_utan_indexeringsrad(self):
        rows,_,_=self.run_transport({'inspektera':[403]},'inspektera',['/','/tjanst'])
        out=gsc.tolkning(rows);self.assertEqual([r['adress'] for r in out],['https://example.invalid/','https://example.invalid/tjanst'])
        self.assertTrue(all(r['http_status']==403 and 'verdict' not in r and 'indexeringsbedömning' in r['atgard'] for r in out))
        rows,_,_=self.run_transport({},'inspektera',['/','/tjanst']);self.assertEqual(gsc.tolkning(rows)[1]['verdict'],'PASS')
    def test_retry_begransat_och_bara_avsedd_transientstatus(self):
        rows,_,wait=self.run_transport({'inspektera':[429,503,200]},'inspektera');self.assertEqual(wait,[1,2]);self.assertEqual(len(gsc.tolkning(rows)),1)
        rows,_,wait=self.run_transport({'inspektera':[503]},'inspektera');self.assertEqual(len(rows),3);self.assertEqual(wait,[1,2]);self.assertEqual(gsc.tolkning(rows)[0]['status'],'API-fel')
        rows,_,wait=self.run_transport({'verifiera':[503]});self.assertEqual(len(rows),1);self.assertEqual(wait,[])
        rows,_,wait=self.run_transport({'inspektera':[(403,{'error':{'errors':[{'reason':'insufficientPermissions'}]}})]},'inspektera');self.assertEqual(len(rows),1);self.assertEqual(wait,[])

class LokaltOchMatning(unittest.TestCase):
    def test_saknad_kontakt_tillater_teknik_men_inte_full_kontaktberedskap(self):
        v=exempel(kontaktvagar=[]);self.assertTrue(any('saknas' in w for w in vu.validera(v)));self.assertIsNone(vu.nap(v)['telefon_e164'])
        for typ,value in [('telefon','påhittat'),('formular','javascript:alert(1)'),('e-post','inte-mail')]:
            with self.assertRaises(vu.Vagrad):vu.validera(exempel(kontaktvagar=[{'typ':typ,'varde':value,'belagg':'syntetisk'}]))
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'index.html').write_text('<html><head><title>Prov</title></head><body>Prov</body></html>');f=p/'v.json';f.write_text(json.dumps(v))
            r=seo.rapport(p,'forhandsvisning',str(f));self.assertEqual(r['sidor'],1);self.assertEqual(r['kontaktberedskap'],'ofullständig');self.assertTrue(r['uppgiftsvarningar'])
            self.assertIn(prelaunch.g5_seo(p,'forhandsvisning',str(f))['status'],['FAIL','PASS'])
    def test_fiktiv_datablad_fullt_men_inte_live(self):
        v=exempel(kontaktvagar=[]);text=gbp.datablad(v)
        self.assertIn('LOKALT TESTUTKAST',text);self.assertIn('## Tjänster',text);self.assertIn('saknas — får inte hittas på',text)
        with self.assertRaises(vu.Vagrad):vu.kraver_verklig(v,'verklig profil')
    def test_kommentar_och_ovillkorlig_tracking_kan_inte_bevisa_handelser_eller_samtycke(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'fixture.js'
            for code in ["// 'quote_submit' 'phone_click' consent", "track('quote_submit');track('phone_click'); // consent"]:
                p.write_text(code);r=mat.kontrollera(matplan(),tmp)
                self.assertTrue(all(x['texttraff'] and not x['handelse_verifierad'] for x in r['handelser']))
                self.assertFalse(r['samtycke']['beteende_verifierat']);self.assertFalse(r['mottagning']['verifierad']);self.assertIn('statisk',r['niva']);self.assertTrue(r['kvarstaende_prov'])

if __name__=='__main__':unittest.main()
