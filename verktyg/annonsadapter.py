"""Begränsade PAUSED-adaptrar. Inget aktiveringskommando, ingen automatisk POST-retry.

Google: Search med manuell CPC, sökord och responsiv annons. Meta: webbtrafik,
en befintligt uppladdad bild med explicit image_hash/page_id. Andra mål vägras.
Testtransport ersätter bara HTTP, aldrig fiktivspärr eller mandat. Kvitton skiljer provnivå.
"""
import hashlib
import json
import os
import re
import urllib.request
import urllib.error
from pathlib import Path
import kundstart as private
import verksamhetsuppgifter as vu

class Vagrad(Exception):
    pass

class IngenOmdirigering(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

def http(method, url, headers, body):
    request = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, headers=headers, method=method)
    try:
        with urllib.request.build_opener(IngenOmdirigering).open(request, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        # Never echo provider error bodies: they can contain credentials or customer data.
        return e.code, {'fel': 'plattformen avvisade anropet'}
    except (urllib.error.URLError, TimeoutError, ValueError):
        raise Vagrad('transport/svar oklart; ingen automatisk upprepning av skapande')

def sha(d):
    return hashlib.sha256(json.dumps(d, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()

def las_config(path):
    p=Path(path).expanduser().resolve(); repo=Path(__file__).resolve().parents[1]
    if repo == p or repo in p.parents or p.stat().st_mode & 0o077:
        raise Vagrad('privat konfigurationsfil krävs utanför repot, rättighet 0600')
    d=json.loads(p.read_text())
    if d.get('schema') != 'digitala-annonskonto/1':
        raise Vagrad('okänt annonskontoschema')
    return d

def config(c, kanal, v, kp):
    if c.get('kanal') != kanal or c.get('verksamhet') != v['namn'] or c.get('plan_sha256') != sha(kp):
        raise Vagrad('konto, verksamhet och exakt kanalplan måste vara bundna i konfigurationen')
    if c.get('tillat_paused_overforing') is not True or not c.get('mandat'):
        raise Vagrad('uttryckligt mandat för PAUSED-överföring saknas')
    if c.get('valuta') != 'SEK' or not c.get('access_token') or any(x in str(c['access_token']) for x in '\r\n'):
        raise Vagrad('konto i SEK och giltig bearer-konfiguration krävs')
    version=c.get('api_version','')
    if not re.fullmatch(r'v\d+' if kanal=='google' else r'v\d+\.\d+', version):
        raise Vagrad('explicit pinnad API-version krävs')
    account=str(c.get('customer_id' if kanal=='google' else 'ad_account_id',''))
    if not re.fullmatch(r'\d{5,20}',account):
        raise Vagrad('konto-id måste vara enbart siffror')
    if kanal=='google' and (not c.get('developer_token') or any(x in str(c['developer_token']) for x in '\r\n')):
        raise Vagrad('Google developer_token krävs')
    if c.get('login_customer_id') and not re.fullmatch(r'\d{5,20}',str(c['login_customer_id'])):
        raise Vagrad('ogiltigt login_customer_id')
    return account

def planer(kanal, kp, ut, c):
    """Validera allt lokalt före första externa skrivning. Ingen godtycklig API-payload."""
    maps=c.get('kampanjer',{}); plans=[]
    for draft in ut[kanal]:
        name=draft['campaign']['name']; m=maps.get(name,{})
        if kanal=='google':
            if m.get('eu_politiskt_innehall') is not False:
                raise Vagrad('adaptern kräver uttryckligt sakbeslut att materialet inte är EU-politisk annonsering')
            if not m.get('geo_ids') or not m.get('language_ids') or not isinstance(m.get('cpc_bid_micros'),int) or m['cpc_bid_micros']<=0:
                raise Vagrad('Google kräver explicita geo_ids, language_ids och cpc_bid_micros per kampanj')
            if not all(re.fullmatch(r'\d+',str(x)) for x in m['geo_ids']+m['language_ids']):
                raise Vagrad('Google geografier/språk ska vara verifierade API-id, inte ortnamn')
            if not draft['ad_groups'][0]['keywords']:
                raise Vagrad('Google-adaptern kräver sökord')
        else:
            if kp['mal']!='trafik':
                raise Vagrad('Meta-adaptern stöder endast webbtrafik; lead/sales kräver separat konverterings- och kontokontrakt')
            if not all(m.get(x) for x in ('page_id','image_hash','targeting')) or not re.fullmatch(r'\d+',str(m['page_id'])) or not isinstance(m['targeting'],dict):
                raise Vagrad('Meta kräver page_id, uppladdad image_hash och explicit targeting')
            if not m['targeting'].get('geo_locations') or not m.get('bildrattighet'):
                raise Vagrad('Meta saknar geografisk avgränsning eller bildrättighetskälla')
            if not isinstance(draft['campaign']['special_ad_categories'],list):
                raise Vagrad('Meta special_ad_categories ska vara ett uttryckligt klassningsbeslut')
        plans.append((draft,m))
    if not plans:
        raise Vagrad('kanalplanen har inga kampanjer för vald kanal')
    return plans

class Korning:
    def __init__(self,c,kanal,account,out,transport):
        self.c=c;self.kanal=kanal;self.account=account;self.out=Path(out);self.transport=transport or http
        self.base=('https://googleads.googleapis.com/' if kanal=='google' else 'https://graph.facebook.com/')+c['api_version']+'/'
        self.headers={'Content-Type':'application/json','Authorization':'Bearer '+c['access_token']}
        if kanal=='google':
            self.headers['developer-token']=c['developer_token']
            if c.get('login_customer_id'): self.headers['login-customer-id']=str(c['login_customer_id'])
        self.d={'schema':'digitala-annonsoverforing/1','kanal':kanal,'konto':account,'api_version':c['api_version'],'plan_sha256':c['plan_sha256'],'konfiguration_sha256':sha({k:v for k,v in c.items() if k not in ('access_token','developer_token')}),'mandat':c['mandat'],'niva':'testtransport' if transport else 'extern-api','verklig_api':transport is None,'lage':'påbörjad','anrop':[],'objekt':[],'overforing_fullstandig':False,'aktivering':False,'spendering_verifierad':False}
    def save(self):private.privat_json(self.out,self.d)
    def call(self,method,path,body=None,mutation=False):
        # Save intent before HTTP. A process crash must never invite automatic create retry.
        row={'metod':method,'path':path,'mutation':mutation,'lage':'utfall okänt','begaran':body};self.d['anrop'].append(row);self.save()
        status,response=self.transport(method,self.base+path,self.headers,body)
        row.update(status=status,svar=response,lage='svar mottaget');self.save()
        if status<200 or status>=300 or not isinstance(response,dict) or response.get('error') or response.get('partialFailureError'):
            raise Vagrad('API-anrop avvisat eller ofullständigt; läs kvittot, inget efterföljande skrivsteg körs')
        return response
    def obj(self,kind,id_,name=None):
        self.d['objekt'].append({'typ':kind,'id':id_,'namn':name});self.save()
    def meta_create(self,kind,body):
        r=self.call('POST','act_'+self.account+'/'+kind,body,True);id_=str(r.get('id',''))
        if not re.fullmatch(r'\d+',id_):raise Vagrad('Meta svar saknar giltigt objekt-id')
        self.obj(kind,id_,body.get('name'));return id_
    def google(self,plans):
        r=self.call('POST','customers/'+self.account+'/googleAds:search',{'query':'SELECT customer.currency_code FROM customer LIMIT 1'})
        if not r.get('results') or r['results'][0].get('customer',{}).get('currencyCode')!='SEK':raise Vagrad('Google-kontots återlästa valuta är inte SEK')
        for draft,m in plans:
            root='customers/'+self.account;name=draft['campaign']['name'];budget=root+'/campaignBudgets/-1';campaign=root+'/campaigns/-2';group=root+'/adGroups/-3';g=draft['ad_groups'][0]
            ops=[{'campaignBudgetOperation':{'create':{'resourceName':budget,'name':name+' budget','amountMicros':str(draft['campaign']['campaign_budget']['amount_micros']),'deliveryMethod':'STANDARD','explicitlyShared':False}}},
                 {'campaignOperation':{'create':{'resourceName':campaign,'name':name,'status':'PAUSED','advertisingChannelType':'SEARCH','campaignBudget':budget,'manualCpc':{},'containsEuPoliticalAdvertising':'DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING'}}},
                 {'adGroupOperation':{'create':{'resourceName':group,'name':g['name'],'status':'PAUSED','campaign':campaign,'type':'SEARCH_STANDARD','cpcBidMicros':str(m['cpc_bid_micros'])}}}]
            for key,ids in (('location',m['geo_ids']),('language',m['language_ids'])):
                for id_ in ids:ops.append({'campaignCriterionOperation':{'create':{'campaign':campaign,key:{'geoTargetConstant' if key=='location' else 'languageConstant':('geoTargetConstants/' if key=='location' else 'languageConstants/')+str(id_)}}}})
            for kw in g['keywords']:
                ops.append({'adGroupCriterionOperation':{'create':{'adGroup':group,'status':'PAUSED','keyword':{'text':kw['keyword']['text'],'matchType':kw['keyword']['match_type']}}}})
            for kw in g['negative_keywords']:
                ops.append({'adGroupCriterionOperation':{'create':{'adGroup':group,'negative':True,'keyword':{'text':kw['text'],'matchType':kw['match_type']}}}})
            a=g['ads'][0];ops.append({'adGroupAdOperation':{'create':{'adGroup':group,'status':'PAUSED','ad':{'responsiveSearchAd':{'headlines':a['headlines'],'descriptions':a['descriptions']},'finalUrls':a['final_urls']}}}})
            r=self.call('POST',root+'/googleAds:mutate',{'mutateOperations':ops,'partialFailure':False},True)
            results=r.get('mutateOperationResponses',[])
            if len(results)!=len(ops):raise Vagrad('Google returnerade inte alla skapade objekt; ingen framgång antas')
            for operation,result in zip(ops,results):
                expected=next(iter(operation)).replace('Operation','Result')
                if set(result)!={expected}:raise Vagrad('Google returnerade fel objekttyp för skapandeoperation')
                for kind,value in result.items():
                    resource=value.get('resourceName','')
                    if not re.fullmatch(re.escape(root)+r'/[A-Za-z]+/[0-9~]+',resource):raise Vagrad('Google returnerade oväntad resursidentitet')
                    self.obj(kind,resource)
    def meta(self,plans):
        r=self.call('GET','act_'+self.account+'?fields=id,currency')
        if r.get('id')!='act_'+self.account or r.get('currency')!='SEK':raise Vagrad('Meta-kontots återlästa identitet/valuta stämmer inte')
        for draft,m in plans:
            campaign=self.meta_create('campaigns',draft['campaign'])
            adset=self.meta_create('adsets',{'name':draft['adset']['name'],'campaign_id':campaign,'status':'PAUSED','daily_budget':str(draft['adset']['daily_budget']),'billing_event':'IMPRESSIONS','optimization_goal':'LINK_CLICKS','bid_strategy':'LOWEST_COST_WITHOUT_CAP','targeting':m['targeting']})
            a=draft['ad'];creative=a['creative']
            cid=self.meta_create('adcreatives',{'name':a['name']+' bild','object_story_spec':{'page_id':str(m['page_id']),'link_data':{'image_hash':m['image_hash'],'link':creative['link'],'message':creative['primary_text'],'name':creative['headline'],'description':creative['description'],'call_to_action':{'type':creative['call_to_action'],'value':{'link':creative['link']}}}}})
            self.meta_create('ads',{'name':a['name'],'adset_id':adset,'status':'PAUSED','creative':{'creative_id':cid}})
    def readback(self):
        states=[]
        for o in self.d['objekt']:
            if self.kanal=='meta':
                if o['typ']=='adcreatives':continue
                r=self.call('GET',o['id']+'?fields=id,name,status,effective_status,account_id')
                if r.get('id')!=o['id'] or str(r.get('account_id'))!=self.account or r.get('status')!='PAUSED':raise Vagrad('Meta readback saknar samma konto/id och PAUSED-status')
                states.append({'id':o['id'],'status':r['status'],'effective_status':r.get('effective_status')})
            else:
                kinds={'campaignResult':('campaign','campaign'),'adGroupResult':('ad_group','adGroup'),'adGroupAdResult':('ad_group_ad','adGroupAd')}
                if o['typ'] not in kinds:continue
                table,key=kinds[o['typ']]
                r=self.call('POST','customers/'+self.account+'/googleAds:search',{'query':"SELECT %s.resource_name, %s.status FROM %s WHERE %s.resource_name = '%s'"%(table,table,table,table,o['id'])})
                rows=r.get('results',[])
                if len(rows)!=1 or rows[0].get(key,{}).get('resourceName')!=o['id'] or rows[0][key].get('status')!='PAUSED':raise Vagrad('Google readback saknar samma resurs och PAUSED-status')
                states.append({'id':o['id'],'status':'PAUSED'})
        if not states:raise Vagrad('inga pausade objekt kunde återläsas')
        if not self.d.get('overforing_fullstandig') or len(states)!=self.d.get('forvantade_pausade_objekt'):
            self.d.update(lage='delvis PAUSED återläst; överföring ofullständig',pausade_objekt=states);self.save()
            raise Vagrad('återlästa objekt är PAUSED men överföringen är ofullständig; ingen hel framgång')
        self.d.update(lage='PAUSED återläst',pausade_objekt=states);self.save()

def overfor(kanal,kp,v,ut,c,out,transport=None):
    vu.kraver_verklig(v,'överföring till annonsplattform')
    account=config(c,kanal,v,kp);plans=planer(kanal,kp,ut,c)
    if ut.get('fynd'):raise Vagrad('beredningen har öppna fynd; överföring vägras')
    path=Path(out)
    path.parent.mkdir(parents=True,exist_ok=True)
    try:
        with os.fdopen(os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),'w') as f:f.write('{}\n')
    except FileExistsError:raise Vagrad('kvitto finns redan; upprepa inte skapande. Använd aterlas eller utred okänt utfall')
    run=Korning(c,kanal,account,out,transport)
    try:
        run.d['forvantade_pausade_objekt']=3*len(plans)
        run.save();getattr(run,kanal)(plans)
        run.d['overforing_fullstandig']=True;run.save();run.readback()
    except Vagrad:
        run.d['lage']='avbruten/ej verifierad';run.save();raise
    return run.d

def aterlas(c,out,transport=None):
    old=json.loads(Path(out).read_text());kanal=old['kanal'];account=str(c.get('customer_id' if kanal=='google' else 'ad_account_id',''))
    if old['konto']!=account or old['api_version']!=c.get('api_version') or old['plan_sha256']!=c.get('plan_sha256') or old['verklig_api']!=(transport is None):raise Vagrad('återläsning kräver samma konto/API/plan/provnivå')
    run=Korning(c,kanal,account,out,transport);run.d=old;run.readback();return run.d
