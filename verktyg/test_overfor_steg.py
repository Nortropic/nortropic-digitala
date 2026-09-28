"""Provar den ordinarie överföringsvägen, historik och negativa källbindningar."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import fortsatt as fs
import ladda_steg as ls
import overfor_steg as tr
from test_fortsatt import bestallning
from test_stegbevis import bevis


class Overforing(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.k = self.root/'kund'; self.k.mkdir()
        self.f = self.root/'fall'
        (self.k/'VERKSAMHET.json').write_text(json.dumps({'schema':1,'namn':'Prov','fiktiv':True}))
        bestallning(self.k, omfattning=['research','brief','koncept'], testfall=True, namn='Prov')
        s=fs.las(self.f,self.k);s['ordning']=['research','brief','koncept'];fs.spara(self.f,s)
        _,r=fs.fortsatt(self.f,self.k,None,'codex');self.work=Path(r['arbetsyta'])

    def tearDown(self):
        self.tmp.cleanup()

    def brief(self):
        (self.work/'research.md').write_text('Kunden uppger fem alternativ. Oberoende belägg saknas. Betalning ej undersökt.')
        fs.overfor(self.f,'research','codex')
        fs.klart(self.f,'research','klar','syntetiskt mekanismprov','codex',bevis=bevis(self.f,self.k,'research'))
        _,r=fs.fortsatt(self.f,self.k,None,'codex');self.work=Path(r['arbetsyta'])
        (self.work/'PROJECT-BRIEF.md').write_text('Jämför de fem kunduppgivna alternativen.')
        (self.work/'SKAPARUPPDRAG.md').write_text('Pröva jämförelsens innehåll och läsbarhet.')
        (self.work/'FAKTABAS.md').write_text('Kunden uppger fem; inte oberoende verifierat.')
        self.package={'schema':'digitala-skaparunderlag/1','uppdrag':{'fil':'SKAPARUPPDRAG.md','sha256':None},
            'bilagor':[{'fil':'underlag/kund/research.md','sha256':None,'roll':'fakta','varfor':'Källbunden syntes.'},
                       {'fil':'FAKTABAS.md','sha256':None,'roll':'fakta','varfor':'Kort källstatus.'}],
            'referenser':[],'resurser':[]}
        self.save_package()

    def save_package(self):
        (self.work/ls.SKAPARFIL).write_text(json.dumps(self.package))

    def reopen_brief(self):
        fs.klart(self.f,'brief','klar','syntetiskt mekanismprov','codex',bevis=bevis(self.f,self.k,'brief'))
        fs.omprova(self.f,'brief','pröva nytt kundunderlag','codex')
        _,r=fs.fortsatt(self.f,self.k,None,'codex')
        self.assertEqual(r['nasta'],'brief');self.work=Path(r['arbetsyta'])
        return json.loads((self.work/'LADDNING.json').read_bytes())

    def test_liten_brief_utan_skaparpaket(self):
        self.brief();(self.work/ls.SKAPARFIL).unlink()
        _,r=fs.overfor(self.f,'brief','codex')
        self.assertEqual(set(r['filer']),{'PROJECT-BRIEF.md'})
        self.assertFalse((self.k/ls.SKAPARFIL).exists())
        self.assertFalse(json.loads(Path(r['kvitto']).read_bytes())['bindning']['skaparpaket'])

    def test_omprov_laddar_binara_bilagor_och_normaliserar_referenspekare(self):
        self.brief()
        png=b'\x89PNG\r\n\x1a\nsyntetiskt byteprov'
        (self.work/'ref.png').write_bytes(png)
        self.package['bilagor'].append({'fil':'ref.png','sha256':None,'roll':'referensbild','varfor':'Syntetiskt kopieringsprov'})
        self.package['referenser']=[{'id':'r','kalla':'syntetisk bild','roller':['hantverk'],'urvalsskal':'Prov',
            'observation':'live','bevis':['ref.png'],'paverkar':'Inget verkligt designval','begransning':'Syntetiskt'}]
        resource='kunskap/externa/emil-prototype-SKILL.md'
        self.package['resurser']=[{'fil':resource,'form':'metod','delar':'relevant avsnitt','skal':'Prov','historik':'REGISTER §A7'}]
        self.save_package();fs.overfor(self.f,'brief','codex')
        original=(self.k/ls.SKAPARFIL).read_bytes()
        receipt=self.reopen_brief()
        self.assertEqual((self.work/'underlag/kund'/ls.SKAPARFIL).read_bytes(),original)
        self.assertEqual((self.work/'underlag/kund/ref.png').read_bytes(),png)
        self.assertFalse((self.work/'SKAPARPAKET.md').exists())
        self.assertFalse(any(r['fil']==resource and r['status']=='laddad' for r in receipt['underlag']))
        self.package=json.loads(original)
        for row in [self.package['uppdrag']]+self.package['bilagor']:
            if row['fil'] != 'ref.png':
                row['fil']='underlag/kund/'+row['fil']
        self.package['referenser'][0]['bevis']=['underlag/kund/ref.png']
        self.save_package();(self.work/'PROJECT-BRIEF.md').write_text('Omarbetad brief')
        _,r=fs.overfor(self.f,'brief','codex')
        d,_,resources=ls.skaparplan(self.k,fs.ROT,ls.las_pinnar(fs.ROT))
        self.assertEqual(d['referenser'][0]['bevis'],['ref.png'])
        self.assertTrue(resource in resources)
        self.assertEqual(d['bilagor'][0]['fil'],'research.md')
        self.assertFalse((self.k/'underlag').exists())
        self.assertEqual((self.k/'ref.png').read_bytes(),png)
        self.assertIn('ref.png',json.loads(Path(r['kvitto']).read_bytes())['bindning']['refererat_laddat'])

    def test_andrad_research_tillater_brief_omarbetning_men_inte_stale_skaparpaket(self):
        self.brief();fs.overfor(self.f,'brief','codex')
        fs.klart(self.f,'brief','klar','syntetiskt mekanismprov','codex',bevis=bevis(self.f,self.k,'brief'))
        original=(self.k/ls.SKAPARFIL).read_bytes()
        (self.k/'research.md').write_text('Nytt verifierbart kundunderlag')
        _,r=fs.fortsatt(self.f,self.k,None,'codex');self.assertEqual(r['nasta'],'brief')
        self.work=Path(r['arbetsyta'])
        loading=json.loads((self.work/'LADDNING.json').read_bytes())
        rows=[r for r in loading['underlag'] if r['fil']=='research.md']
        self.assertTrue(any(r['status'].startswith('inaktuellt') and r['plats'] is None for r in rows))
        self.assertEqual((self.work/'underlag/kund/research.md').read_bytes(),(self.k/'research.md').read_bytes())
        self.assertEqual((self.work/'underlag/kund'/ls.SKAPARFIL).read_bytes(),original)
        self.assertEqual((self.work/'underlag/kund/FAKTABAS.md').read_bytes(),(self.k/'FAKTABAS.md').read_bytes())
        with self.assertRaisesRegex(ls.Vagrad,'har ändrats'):
            ls.ladda(fs.ROT,'koncept',self.root/'stale-koncept',kund=self.k,bestallning='PROV-BESTALLNING-1')
        self.package=json.loads(original);self.package['bilagor'][0]['sha256']=None
        self.save_package();(self.work/'PROJECT-BRIEF.md').write_text('Reviderad brief efter research')
        fs.overfor(self.f,'brief','codex')
        d,_,_=ls.skaparplan(self.k,fs.ROT,ls.las_pinnar(fs.ROT))
        self.assertEqual(d['bilagor'][0]['sha256'],ls.sha256_file(self.k/'research.md'))

    def test_kundindata_och_skiftlagesalias_kan_inte_nya_bilagor_skriva(self):
        self.brief()
        for name in ('bestallning.json','KUNDSTART-ARBETSUPPGIFT.json','KANALBEHOV.json','INTERVJU/svar.md'):
            with self.subTest(name=name):
                self.package['uppdrag']['fil']=name;self.save_package()
                path=self.work/name;path.parent.mkdir(exist_ok=True);path.write_text('Otillåtet')
                with self.assertRaises(ls.Vagrad):fs.overfor(self.f,'brief','codex')
                self.assertFalse((self.k/'PROJECT-BRIEF.md').exists())
        self.package['uppdrag']['fil']='SKAPARUPPDRAG.md';self.package['bilagor'][1]['fil']='FaktaBas.md'
        self.save_package()
        with self.assertRaisesRegex(ls.Vagrad,'skiftläge'):fs.overfor(self.f,'brief','codex')

    def test_valfria_utdata_valideras_och_overfors_med_historik(self):
        from test_verksamhetsuppgifter import exempel
        old=(self.k/'VERKSAMHET.json').read_bytes()
        (self.work/'research.md').write_text('Research')
        path=self.work/'VERKSAMHET.json';path.write_text(json.dumps(exempel(namn='Prov')))
        _,r=fs.overfor(self.f,'research','codex')
        self.assertEqual((self.k/'VERKSAMHET.json').read_bytes(),path.read_bytes())
        self.assertEqual((Path(r['kvitto']).parent/'fore/VERKSAMHET.json').read_bytes(),old)
        self.brief();choice=self.work/'INTEGRATIONSVAL.json'
        choice.write_text(json.dumps({'schema':'digitala-integrationsval/1','val':[]}))
        fs.overfor(self.f,'brief','codex')
        self.assertEqual((self.k/'INTEGRATIONSVAL.json').read_bytes(),choice.read_bytes())

    def test_ogiltiga_valfria_utdata_vagras_fore_nagon_kundskrivning(self):
        (self.work/'research.md').write_text('Research')
        (self.work/'VERKSAMHET.json').write_text('{"schema":1}')
        with self.assertRaisesRegex(ls.Vagrad,'VERKSAMHET'):fs.overfor(self.f,'research','codex')
        self.assertFalse((self.k/'research.md').exists())
        (self.work/'VERKSAMHET.json').unlink();self.brief()
        (self.work/'INTEGRATIONSVAL.json').write_text('{"schema":"fel","val":[]}')
        with self.assertRaisesRegex(ls.Vagrad,'INTEGRATIONSVAL'):fs.overfor(self.f,'brief','codex')
        self.assertFalse((self.k/'PROJECT-BRIEF.md').exists())

    def test_staende_research_kan_uppdatera_verksamhet_utan_bestallning(self):
        from test_verksamhetsuppgifter import exempel
        (self.k/'BESTALLNING.json').unlink();fall=self.root/'staende-fall'
        s=fs.las(fall,self.k);s['ordning']=['research'];fs.spara(fall,s)
        _,r=fs.fortsatt(fall,self.k,None,'codex');work=Path(r['arbetsyta'])
        (work/'research.md').write_text('Stående research')
        (work/'VERKSAMHET.json').write_text(json.dumps(exempel(namn='Prov')))
        fs.overfor(fall,'research','codex')
        self.assertEqual((self.k/'VERKSAMHET.json').read_bytes(),(work/'VERKSAMHET.json').read_bytes())

    def test_historik_och_nya_utdata_skyddas_mot_symlink_och_sen_andring(self):
        self.brief();_,r=fs.overfor(self.f,'brief','codex')
        history=Path(r['kvitto']).parent
        original=history/'original';old=original.rename(history/'orignal-bevarat')
        original.symlink_to(old,target_is_directory=True)
        with self.assertRaisesRegex(ls.Vagrad,'symbolisk'):fs.overfor(self.f,'brief','codex')
        original.unlink();old.rename(original)
        (self.k/'FAKTABAS.md').write_text('Extern senare rättelse')
        (self.work/'FAKTABAS.md').write_text('Nytt arbetsresultat')
        with self.assertRaisesRegex(ls.Vagrad,'målet har ändrats'):fs.overfor(self.f,'brief','codex')
        self.assertEqual((self.k/'FAKTABAS.md').read_text(),'Extern senare rättelse')

    def test_ateroppnad_giltighet_sparas_aven_nar_transfer_vagrar(self):
        state=fs.las(self.f);state['steg']['brief']['status']='klar'
        fs.spara(self.f,state)
        with self.assertRaisesRegex(ls.Vagrad,'skriv filen'):
            fs.overfor(self.f,'research','codex')
        state=fs.las(self.f)
        self.assertNotEqual(state['steg']['brief']['status'],'klar')
        self.assertTrue(state['steg']['brief']['historik'])

    def test_tidigare_journal_far_inte_auktorisera_andrat_kundmal(self):
        self.brief();_,r=fs.overfor(self.f,'brief','codex')
        (self.k/'FAKTABAS.md').write_text('Extern rättelse')
        (self.work/'FAKTABAS.md').write_text('Nytt arbetsresultat')
        journal=Path(r['kvitto']);d=json.loads(journal.read_bytes())
        d['bindning']['filer']['FAKTABAS.md']=ls.sha256_file(self.k/'FAKTABAS.md')
        journal.write_text(json.dumps(d))
        with self.assertRaisesRegex(ls.Vagrad,'tidigare överföringsjournal'):
            fs.overfor(self.f,'brief','codex')
        self.assertEqual((self.k/'FAKTABAS.md').read_text(),'Extern rättelse')

    def test_aterbruk_av_laddade_bytes_vagras_efter_egen_senare_overforing(self):
        self.brief();fs.overfor(self.f,'brief','codex');self.reopen_brief()
        self.package=json.loads((self.work/'underlag/kund'/ls.SKAPARFIL).read_bytes())
        (self.work/'PROJECT-BRIEF.md').write_text('Briefens revision')
        (self.work/'FAKTABAS.md').write_text('Nyare överförd faktabas')
        self.package['bilagor'][1]['sha256']=None;self.save_package()
        fs.overfor(self.f,'brief','codex')
        transferred=(self.k/ls.SKAPARFIL).read_bytes()
        (self.work/'FAKTABAS.md').unlink()
        self.package['bilagor'][1]['fil']='underlag/kund/FAKTABAS.md';self.save_package()
        with self.assertRaisesRegex(ls.Vagrad,'inte längre kundens aktuella bytes'):
            fs.overfor(self.f,'brief','codex')
        self.assertEqual((self.k/ls.SKAPARFIL).read_bytes(),transferred)
        self.assertEqual((self.k/'FAKTABAS.md').read_text(),'Nyare överförd faktabas')

    def test_sen_researchandring_ateroppnas_och_sparas_fore_overforing(self):
        self.brief();(self.k/'research.md').write_text('Ändrad efter laddning')
        with self.assertRaises(fs.Vagrad):fs.overfor(self.f,'brief','codex')
        state=fs.las(self.f)
        self.assertNotEqual(state['steg']['brief']['status'],'påbörjat')
        self.assertIn('research.md',state['steg']['brief']['historik'][-1]['skal'])

    def test_farsk_cli_materialiserar_vald_bilaga_och_hashar_utan_assistans(self):
        self.brief(); original=(self.work/ls.SKAPARFIL).read_bytes()
        cmd=[sys.executable,'-B',fs.__file__,'overfor','--fall',str(self.f),'--steg','brief']
        result=subprocess.run(cmd,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        record=json.loads(result.stdout)
        self.assertFalse(record['sakgodkannande'])
        self.assertEqual((self.work/ls.SKAPARFIL).read_bytes(),original)
        self.assertEqual((Path(record['kvitto']).parent/'original'/ls.SKAPARFIL).read_bytes(),original)
        d,_,_=ls.skaparplan(self.k,fs.ROT,ls.las_pinnar(fs.ROT))
        for row in [d['uppdrag']]+d['bilagor']:
            self.assertEqual(row['sha256'],ls.sha256_file(self.k/row['fil']))
        fs.klart(self.f,'brief','klar','syntetiskt mekanismprov','codex',bevis=bevis(self.f,self.k,'brief'))
        _,next_step=fs.fortsatt(self.f,self.k,None,'codex')
        self.assertEqual(next_step['nasta'],'koncept')
        creator=Path(next_step['arbetsyta'])
        self.assertEqual((creator/'underlag/kund'/d['bilagor'][0]['fil']).read_bytes(),(self.k/'research.md').read_bytes())

    def test_felaktig_hash_eller_otillganglig_fil_vagras_fore_kundskrivning(self):
        self.brief()
        self.package['uppdrag']['sha256']='a'*64;self.save_package()
        with self.assertRaisesRegex(ls.Vagrad,'filhash'):fs.overfor(self.f,'brief','codex')
        self.assertFalse((self.k/'PROJECT-BRIEF.md').exists())
        self.package['uppdrag']['sha256']=None;self.package['bilagor'][0]['fil']='underlag/kund/saknas.md';self.save_package()
        with self.assertRaises(ls.Vagrad):fs.overfor(self.f,'brief','codex')
        self.assertFalse((self.k/ls.SKAPARFIL).exists())

    def test_sen_kallandring_och_laddad_filmanipulation_vagras(self):
        self.brief()
        (self.k/'research.md').write_text('Sen rättelse')
        with self.assertRaises(fs.Vagrad):fs.overfor(self.f,'brief','codex')
        self.assertFalse((self.k/'PROJECT-BRIEF.md').exists())

    def test_symlink_och_mandatskrivning_vagras(self):
        self.brief()
        (self.root/'annan.md').write_text('otillåtet')
        (self.work/'FAKTABAS.md').unlink();(self.work/'FAKTABAS.md').symlink_to(self.root/'annan.md')
        with self.assertRaisesRegex(ls.Vagrad,'symbolisk'):fs.overfor(self.f,'brief','codex')
        (self.work/'FAKTABAS.md').unlink();(self.work/'FAKTABAS.md').write_text('Fakta')
        self.package['uppdrag']['fil']='BESTALLNING.json';self.save_package()
        (self.work/'BESTALLNING.json').write_text('obeställd ändring')
        with self.assertRaisesRegex(ls.Vagrad,'tillåtet'):fs.overfor(self.f,'brief','codex')

    def test_avbruten_overforing_aterupptas_med_samma_historik(self):
        (self.work/'research.md').write_text('Första research')
        real_write=tr.write
        def fail(path, raw):
            if path==self.k/'research.md':raise OSError('syntetiskt diskfel')
            real_write(path,raw)
        with patch.object(tr,'write',fail),self.assertRaisesRegex(fs.Vagrad,'diskfel'):
            fs.overfor(self.f,'research','codex')
        _,r=fs.overfor(self.f,'research','codex')
        _,again=fs.overfor(self.f,'research','codex')
        self.assertEqual(r['kvitto'],again['kvitto'])
        self.assertEqual(len(list(self.f.glob('overforing-*'))),1)
        self.assertEqual(fs.las(self.f)['steg']['research']['status'],'påbörjat')
        (self.k/'research.md').write_text('Någon annans senare research')
        with self.assertRaisesRegex(ls.Vagrad,'målet har ändrats'):fs.overfor(self.f,'research','codex')

    def test_delvis_skrivet_paket_kan_rattas_efter_processavbrott(self):
        self.brief();fs.overfor(self.f,'brief','codex');self.reopen_brief()
        (self.work/'PROJECT-BRIEF.md').write_text('Andra briefen')
        (self.work/'SKAPARUPPDRAG.md').write_text('Andra uppdraget')
        (self.work/'FAKTABAS.md').write_text('Andra faktabasen')
        self.save_package();real_write=tr.write
        def fail(path,raw):
            if path==self.k/ls.SKAPARFIL:raise SystemExit('syntetiskt processavbrott')
            real_write(path,raw)
        with patch.object(tr,'write',fail),self.assertRaises(SystemExit):
            fs.overfor(self.f,'brief','codex')
        state=fs.las(self.f)
        partial=[Path(p) for p in state['steg']['brief']['kvitton'] if Path(p).name=='KVITTO.json'
                 and json.loads(Path(p).read_bytes())['lage']=='förberedd']
        self.assertEqual(len(partial),1)
        (self.work/'SKAPARUPPDRAG.md').write_text('Rättat efter avbrottet')
        _,result=fs.overfor(self.f,'brief','codex')
        self.assertEqual((self.k/'SKAPARUPPDRAG.md').read_text(),'Rättat efter avbrottet')
        self.assertEqual((Path(result['kvitto']).parent/'fore/SKAPARUPPDRAG.md').read_text(),'Andra uppdraget')
        self.assertEqual(json.loads(partial[0].read_bytes())['lage'],'förberedd')
        ls.skaparplan(self.k,fs.ROT,ls.las_pinnar(fs.ROT))

    def test_stale_bilaga_far_nytt_arbetsresultat_efter_farsk_laddning(self):
        self.brief();fs.overfor(self.f,'brief','codex')
        fs.klart(self.f,'brief','klar','syntetiskt mekanismprov','codex',bevis=bevis(self.f,self.k,'brief'))
        (self.k/'FAKTABAS.md').write_text('Extern rättelse före omladdning')
        fs.omprova(self.f,'brief','ta hänsyn till rättelsen','codex')
        _,r=fs.fortsatt(self.f,self.k,None,'codex');self.work=Path(r['arbetsyta'])
        (self.work/'PROJECT-BRIEF.md').write_text('Rättad brief')
        (self.work/'FAKTABAS.md').write_text('Nytt uttryckligt arbetsresultat')
        self.save_package()
        (self.k/'FAKTABAS.md').write_text('Ändring efter omladdning')
        with self.assertRaisesRegex(ls.Vagrad,'ändrat'):fs.overfor(self.f,'brief','codex')
        (self.k/'FAKTABAS.md').write_text('Extern rättelse före omladdning')
        _,result=fs.overfor(self.f,'brief','codex')
        self.assertEqual((self.k/'FAKTABAS.md').read_text(),'Nytt uttryckligt arbetsresultat')
        self.assertEqual((Path(result['kvitto']).parent/'fore/FAKTABAS.md').read_text(),'Extern rättelse före omladdning')

    def test_ateroverforing_bevarar_befintlig_filrattighet(self):
        (self.work/'research.md').write_text('Första research');fs.overfor(self.f,'research','codex')
        (self.k/'research.md').chmod(0o640)
        (self.work/'research.md').write_text('Rättad research');fs.overfor(self.f,'research','codex')
        self.assertEqual((self.k/'research.md').stat().st_mode & 0o777,0o640)
