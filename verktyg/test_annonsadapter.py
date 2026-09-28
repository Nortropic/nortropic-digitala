"""HTTP-kontrakt med testtransport. Inga API-konton kontaktas eller skapas."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import annonsadapter as a
import annonsberedning as ab
import verksamhetsuppgifter as vu
from test_annonsberedning import kanalplan
from test_verksamhetsuppgifter import exempel

class Ads(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.out=Path(self.tmp.name)/'kvitto.json';self.v=exempel(fiktiv=False);self.kp=kanalplan(mal='trafik');self.ut=ab.bygg(self.kp,self.v)
        self.c={'schema':'digitala-annonskonto/1','kanal':'google','verksamhet':self.v['namn'],'plan_sha256':a.sha(self.kp),'tillat_paused_overforing':True,'mandat':'syntetiskt överföringsmandat','valuta':'SEK','access_token':'test-token','developer_token':'test-dev','api_version':'v22','customer_id':'1234567890','kampanjer':{'Anläggning Provstad':{'geo_ids':['1001'],'language_ids':['1002'],'cpc_bid_micros':1000000,'eu_politiskt_innehall':False},'Vårkampanj':{'page_id':'12345','image_hash':'provhash','targeting':{'geo_locations':{'countries':['SE']}},'bildrattighet':'syntetisk provbild'}}};self.calls=[];self.counter=100;self.remote={};self.bad_status=False;self.fail_at=None;self.unknown=False
    def tearDown(self):self.tmp.cleanup()
    def transport(self,method,url,headers,body):
        self.calls.append({'method':method,'url':url,'body':body})
        if self.fail_at==len(self.calls):return 403,{'fel':'syntetiskt behörighetsfel'}
        if self.unknown:raise a.Vagrad('syntetiskt tappat svar')
        if url.endswith('googleAds:mutate'):
            out=[]
            for op in body['mutateOperations']:
                key=next(iter(op));obj=op[key]['create'];kind=key.replace('Operation','Result'); self.counter+=1
                coll={'campaignBudgetResult':'campaignBudgets','campaignResult':'campaigns','adGroupResult':'adGroups','campaignCriterionResult':'campaignCriteria','adGroupCriterionResult':'adGroupCriteria','adGroupAdResult':'adGroupAds'}[kind]
                rn='customers/1234567890/'+coll+'/'+str(self.counter);self.remote[rn]={'resourceName':rn,'status':obj.get('status')};out.append({kind:{'resourceName':rn}})
                if 'status' in obj:self.assertEqual(obj['status'],'PAUSED')
            self.assertFalse(body['partialFailure']);return 200,{'mutateOperationResponses':out}
        if url.endswith('googleAds:search'):
            query=body['query']
            if 'customer.currency_code' in query:return 200,{'results':[{'customer':{'currencyCode':'SEK'}}]}
            rn=query.split("'")[1];obj=copy.deepcopy(self.remote[rn]);table=query.split(' FROM ')[1].split(' ')[0];key={'campaign':'campaign','ad_group':'adGroup','ad_group_ad':'adGroupAd'}[table]
            if self.bad_status:obj['status']='ENABLED'
            return 200,{'results':[{key:obj}]}
        if 'act_1234567890?fields' in url:return 200,{'id':'act_1234567890','currency':'SEK'}
        if method=='POST':
            self.counter+=1;id_=str(self.counter);self.remote[id_]=body
            if not url.endswith('/adcreatives'):self.assertEqual(body['status'],'PAUSED')
            return 200,{'id':id_}
        id_=url.split('/')[-1].split('?')[0]
        return 200,{'id':id_,'account_id':'1234567890','name':self.remote[id_]['name'],'status':'ACTIVE' if self.bad_status else 'PAUSED','effective_status':'PAUSED'}
    def test_google_exact_object_status_and_readback(self):
        r=a.overfor('google',self.kp,self.v,self.ut,self.c,self.out,self.transport)
        self.assertEqual(r['lage'],'PAUSED återläst');self.assertEqual(r['niva'],'testtransport');self.assertFalse(r['verklig_api']);self.assertEqual(len(r['pausade_objekt']),3)
        before=len(self.calls)
        with self.assertRaisesRegex(a.Vagrad,'kvitto finns'):a.overfor('google',self.kp,self.v,self.ut,self.c,self.out,self.transport)
        self.assertEqual(len(self.calls),before)
        a.aterlas(self.c,self.out,self.transport);self.assertTrue(all(x['url'].endswith('googleAds:search') for x in self.calls[before:]))
        self.assertNotIn('test-token',self.out.read_text());self.assertNotIn('test-dev',self.out.read_text())
    def test_meta_campaign_adset_creative_ad_and_readback(self):
        self.c.update(kanal='meta',api_version='v24.0',ad_account_id='1234567890')
        r=a.overfor('meta',self.kp,self.v,self.ut,self.c,self.out,self.transport)
        self.assertEqual(len(r['objekt']),4);self.assertEqual(len(r['pausade_objekt']),3)
        self.assertEqual(self.remote['102']['campaign_id'],'101');self.assertEqual(self.remote['104']['adset_id'],'102');self.assertEqual(self.remote['104']['creative']['creative_id'],'103')
        self.assertIn('utm_source=meta',self.remote['103']['object_story_spec']['link_data']['link'])
    def test_guard_before_any_http_for_fiction_mandate_config_or_unsupported_goal(self):
        for field,value in [('tillat_paused_overforing',False),('plan_sha256','wrong'),('api_version','https://evil.invalid'),('customer_id','12/34')]:
            c=copy.deepcopy(self.c);c[field]=value
            with self.assertRaises(a.Vagrad):a.overfor('google',self.kp,self.v,self.ut,c,self.out,self.transport)
        with self.assertRaises(vu.Vagrad):a.overfor('google',self.kp,exempel(fiktiv=True),self.ut,self.c,self.out,self.transport)
        kp=kanalplan();c=copy.deepcopy(self.c);c.update(kanal='meta',api_version='v24.0',ad_account_id='1234567890',plan_sha256=a.sha(kp))
        with self.assertRaisesRegex(a.Vagrad,'endast webbtrafik'):a.overfor('meta',kp,self.v,ab.bygg(kp,self.v),c,self.out,self.transport)
        self.assertEqual(self.calls,[])
    def test_403_stops_chain_and_wrong_readback_never_passes(self):
        self.c.update(kanal='meta',api_version='v24.0',ad_account_id='1234567890');self.fail_at=3
        with self.assertRaises(a.Vagrad):a.overfor('meta',self.kp,self.v,self.ut,self.c,self.out,self.transport)
        self.assertEqual(len(self.calls),3);self.assertEqual(len(json.loads(self.out.read_text())['objekt']),1)
        self.assertEqual(json.loads(self.out.read_text())['lage'],'avbruten/ej verifierad')
        self.fail_at=None
        with self.assertRaisesRegex(a.Vagrad,'ofullständig'):a.aterlas(self.c,self.out,self.transport)
        self.assertFalse(json.loads(self.out.read_text())['overforing_fullstandig'])
        self.out=Path(self.tmp.name)/'andra.json';self.fail_at=None;self.bad_status=True
        with self.assertRaisesRegex(a.Vagrad,'PAUSED'):a.overfor('meta',self.kp,self.v,self.ut,self.c,self.out,self.transport)
    def test_unknown_response_is_not_retried(self):
        self.unknown=True
        with self.assertRaises(a.Vagrad):a.overfor('google',self.kp,self.v,self.ut,self.c,self.out,self.transport)
        self.assertEqual(len(self.calls),1);d=json.loads(self.out.read_text());self.assertEqual(d['anrop'][0]['lage'],'utfall okänt')
        with self.assertRaisesRegex(a.Vagrad,'kvitto finns'):a.overfor('google',self.kp,self.v,self.ut,self.c,self.out,self.transport)
        self.assertEqual(len(self.calls),1)
    def test_config_is_private_and_not_inside_repo(self):
        p=Path(self.tmp.name)/'konto.json';p.write_text(json.dumps(self.c));p.chmod(0o644)
        with self.assertRaisesRegex(a.Vagrad,'0600'):a.las_config(p)
        p.chmod(0o600);self.assertEqual(a.las_config(p)['customer_id'],'1234567890')

if __name__=='__main__':unittest.main()
