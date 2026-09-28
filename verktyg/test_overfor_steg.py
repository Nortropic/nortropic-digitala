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
