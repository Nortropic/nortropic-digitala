"""Ordinarie fortsättning: positiva bevis, semantiska avslag, ändring och beroenden."""
import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fortsatt as fs
import stegbevis as sb


def skriv(p, d):
    p.write_text(json.dumps(d, ensure_ascii=False)); return p


def bevis(fall, kund, steg, *, niva='dokument', status='PASS'):
    f=Path(fall);k=Path(kund);s=fs.las(f)
    candidate=k/'syntetisk-kandidat.txt'
    if not candidate.exists():candidate.write_text('syntetisk kandidat, ingen kundprodukt')
    ctx={'kandidat':{'typ':'filer','filer':[{'fil':str(candidate),'sha256':sb.sha(candidate)}]},'miljo':{'namn':'isolerat regressionstest','typ':'lokal'},'konfiguration':{'filer':[],'ej_tillampligt':'dokumentprov utan körkonfiguration'}}
    kr=f/'BEVISKRAV.json';d=sb.las(kr) if kr.exists() else {'schema':'digitala-beviskrav/1','version':'syntetisk-v1','steg':{}}
    d['steg'][steg]={'niva':niva,'sammanhang':ctx,'kontroller':{'resultat':{'forvantat':'godkänt konkret resultat'}}};skriv(kr,d)
    raw=skriv(f/(steg+'-resultat.json'),{'status':status,'sammanhang':ctx,'genomfort':True})
    return skriv(f/(steg+'-bevis.json'),{'schema':'digitala-stegbevis/1','steg':steg,'kund':str(k.resolve()),'krav_sha256':sb.sha(kr),'laddning_sha256':sb.sha(s['steg'][steg]['laddning']),'utfall':'klar','genomfort':True,'utforare':'syntetiskt regressionstest','omfattning':'isolerat dokumentprov','niva':niva,'sammanhang':ctx,'kontroller':[{'id':'resultat','utfall':'godkant','observerat':'råresultatet kontrollerat','fil':str(raw),'sha256':sb.sha(raw),'utfallspekare':['status'],'bindningspekare':{key:['sammanhang',key] for key in ctx}}]})


class Bevis(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.k=Path(self.tmp.name)/'kund';self.k.mkdir();self.f=Path(self.tmp.name)/'fall'
        fs.fortsatt(self.f,self.k,None,'codex')
    def tearDown(self):self.tmp.cleanup()
    def test_tomt_fel_arbitrar_och_negativt_kvitto_vagras(self):
        with self.assertRaisesRegex(fs.Vagrad,'--bevis'):fs.klart(self.f,'uppstart','klar','saknas','codex')
        b=bevis(self.f,self.k,'uppstart',status='FAIL')
        with self.assertRaisesRegex(fs.Vagrad,'råresultatet'):fs.klart(self.f,'uppstart','klar','fel','codex',bevis=b)
        d=sb.las(b);d['sammanhang']['miljo']['namn']='annan';skriv(b,d)
        with self.assertRaisesRegex(fs.Vagrad,'fel kandidat, miljö'):fs.klart(self.f,'uppstart','klar','fel','codex',bevis=b)
        b=bevis(self.f,self.k,'uppstart');d=sb.las(b);r=d['kontroller'][0];raw=sb.las(r['fil']);raw['sammanhang']['kandidat']['filer'][0]['sha256']='0'*64;skriv(Path(r['fil']),raw);r['sha256']=sb.sha(r['fil']);skriv(b,d)
        with self.assertRaisesRegex(fs.Vagrad,'råresultatet gäller annan kandidat'):fs.klart(self.f,'uppstart','klar','fel','codex',bevis=b)
    def test_godkant_aterbruk_och_invalidation(self):
        b=bevis(self.f,self.k,'uppstart');fs.klart(self.f,'uppstart','klar','bevisat','codex',bevis=b,sidoeffekter=['privat prov skapat'])
        s=fs.las(self.f);fs.giltighetskontroll(s,'claude');self.assertEqual(s['steg']['uppstart']['status'],'klar')
        (self.k/'syntetisk-kandidat.txt').write_text('ändrat')
        fs.giltighetskontroll(s,'claude');self.assertEqual(s['steg']['uppstart']['status'],'inte påbörjat');self.assertEqual(s['steg']['uppstart']['sidoeffekter'],['privat prov skapat']);self.assertTrue(s['steg']['uppstart']['historik'])
    def test_lost_beroende_historik_och_nytt_beroende(self):
        fs.klart(self.f,'uppstart','vantar','väntar','codex',beroende='A');fs.omprova(self.f,'uppstart','A finns','claude');fs.fortsatt(self.f,None,None,'claude')
        fs.klart(self.f,'uppstart','vantar','A verifierat, B återstår','claude',beroende='B',losta=['A'])
        s=fs.status(fs.las(self.f));self.assertEqual(s['beroenden'],['uppstart: B']);self.assertEqual(s['losta_beroenden']['uppstart'][0]['beroende'],'A')
    def test_na_kraver_forhandsbeslut_och_andrad_konfiguration_ateroppnar(self):
        b=bevis(self.f,self.k,'uppstart'); d=sb.las(b); d['utfall']='inte-tillampligt'; d['na_skal']='åtkomst saknas'; skriv(b,d)
        with self.assertRaisesRegex(fs.Vagrad,'N/A'): fs.klart(self.f,'uppstart','inte-tillampligt','saknar åtkomst','codex',bevis=b)
        b=bevis(self.f,self.k,'uppstart'); d=sb.las(b); cfg=self.k/'konfiguration.json';cfg.write_text('{}')
        d['sammanhang']['konfiguration']={'filer':[{'fil':str(cfg),'sha256':sb.sha(cfg)}]}
        kr=self.f/'BEVISKRAV.json'; k=sb.las(kr);k['steg']['uppstart']['sammanhang']=d['sammanhang'];skriv(kr,k); d['krav_sha256']=sb.sha(kr)
        r=d['kontroller'][0]; raw=sb.las(r['fil']);raw['sammanhang']=d['sammanhang'];skriv(Path(r['fil']),raw);r['sha256']=sb.sha(r['fil']);skriv(b,d)
        fs.klart(self.f,'uppstart','klar','provad config','codex',bevis=b);cfg.write_text('{"ny":true}')
        s=fs.las(self.f);fs.giltighetskontroll(s,'claude');self.assertEqual(s['steg']['uppstart']['status'],'inte påbörjat')
    def test_bygge_far_inte_klaras_nar_koncept_ateroppnats(self):
        s=fs.las(self.f);s['steg']['bygge'].update(status='påbörjat',laddning=s['steg']['uppstart']['laddning']);fs.spara(self.f,s)
        b=bevis(self.f,self.k,'bygge')
        with self.assertRaisesRegex(fs.Vagrad,'förutsättningar'):fs.klart(self.f,'bygge','klar','syntetiskt byggprov','codex',bevis=b)
    def test_alla_beroenden_kan_losas_och_sparar_historik(self):
        fs.klart(self.f,'uppstart','vantar','saknas','codex',beroende='A');fs.omprova(self.f,'uppstart','mottaget','claude');fs.fortsatt(self.f,None,None,'claude')
        b=bevis(self.f,self.k,'uppstart');s,_=fs.klart(self.f,'uppstart','klar','A verifierat i bevis','claude',bevis=b,losta=['A'])
        self.assertEqual(s['steg']['uppstart']['beroenden'],[]);self.assertEqual(s['steg']['uppstart']['status'],'klar');self.assertEqual(s['steg']['uppstart']['losta_beroenden'][0]['beroende'],'A')
    def test_aldre_klar_uppgraderas_inte_och_koncept_vantan_blockerar_bygge(self):
        s=fs.las(self.f);s['steg']['uppstart']['status']='klar';fs.giltighetskontroll(s,'codex');self.assertNotEqual(s['steg']['uppstart']['status'],'klar')
        # Isolated state: every other stage excluded by the tool, concept required and waiting.
        for st in s['steg'].values():st.update(status=fs.STATUS_VERKTYG,markering='verktyg')
        s['steg']['koncept']['status']=fs.STATUS_VANTAR;s['steg']['bygge']['status']='inte påbörjat'
        s['bestallning']={'post':'PROV-BESTALLNING-1','omfattning':['koncept','bygge'],'lanseringsmandat':None};(self.k/'VERKSAMHET.json').write_text('{}');(self.k/'KANALBEHOV.json').write_text(json.dumps({k:False for k in fs.KANALSTEG}))
        # Restrict order to the two dependent stages without inventing new stage definitions.
        s['ordning']=['koncept','bygge'];n,lage,why=fs.nasta_steg(s);self.assertEqual(lage,'blockerad');self.assertIn('koncept',why);self.assertNotIn('färdig',why)

if __name__=='__main__':unittest.main()
