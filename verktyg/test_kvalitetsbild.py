"""Prov för kvalitetsbild: syntetiska körningar och kvitton ger de tre kolumnerna, och saknat fylls aldrig i."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent


def korning(fall, name, profil, etikett, run=None, exit_code=0, outcome='klar'):
    (fall / name).write_text(json.dumps({'schema': 1, 'profil': profil, 'etikett': etikett, 'exit': exit_code,
                                         'laddning': {'sha256': 'a' * 64, 'steg': profil},
                                         'resultat': {'run': str(run) if run else None, 'outcome': outcome}}))


class Kvalitetsbild(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='nd-kb-'))
        self.fall = self.tmp / 'fall'
        self.fall.mkdir()

    def build(self, *extra):
        ut = self.fall / 'KVALITETSBILD.md'
        done = subprocess.run([sys.executable, '-B', str(HERE / 'kvalitetsbild.py'), '--fall', str(self.fall), '--ut', str(ut), '--json', *extra],
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        return ut.read_text(), json.loads(done.stdout)

    def test_tre_kolumner_ur_kvitton(self):
        run_m = self.tmp / 'run-matning'
        run_m.mkdir()
        (run_m / 'KVITTO.json').write_text(json.dumps({'profile': 'matning', 'outcome': 'klar'}))
        (run_m / 'SAMMANFATTNING.json').write_text(json.dumps({'views': {'mobil-390': {'status': 'ok', 'h1': [{'lines': 2}], 'action': {'fully_in_first_view': True},
                                                                          'axe': {'violations': [], 'incomplete': ['color-contrast']}, 'detector': {'findings': 12, 'meaning': 'fynd'}}},
                                                               'lighthouse': {'mobile': {'scores': {'performance': 0.97}}}}))
        run_k = self.tmp / 'run-kritik'
        run_k.mkdir()
        (run_k / 'KVITTO.json').write_text(json.dumps({'profile': 'kritik', 'outcome': 'svar_giltigt', 'images': {'complete': True}}))
        (run_k / 'svar.json').write_text(json.dumps({'verdict': 'approved', 'blocking_findings': [], 'summary': 'bra'}))
        korning(self.fall, 'KORNING-1-matning-m1.json', 'matning', 'm1', run_m)
        korning(self.fall, 'KORNING-2-kritik-k1.json', 'kritik', 'k1', run_k, outcome='svar_giltigt')
        run_p = self.tmp / 'run-provare'
        run_p.mkdir()
        (run_p / 'KVITTO.json').write_text(json.dumps({'profile': 'provare', 'outcome': 'klar'}))
        korning(self.fall, 'KORNING-3-provare-p1.json', 'provare', 'p1', run_p, outcome='klar')
        besok = self.fall / 'BESOK-20260927T1'; besok.mkdir()
        (besok / 'BESOK.json').write_text(json.dumps({'schema': 1, 'verktyg': 'besok', 'lage': 'besok', 'adress': 'http://127.0.0.1:1/', 'torr': False, 'utforare': 'claude', 'modell': 'm', 'utforare_status': 0, 'inom_gransen': True,
                                                      'efterkontroll': {'antal_forfragningar': 9, 'blockerade': 0, 'inom_gransen': True}, 'besok': {'utfall': 'lost'}}))
        (self.fall / 'KONTROLL-besok.json').write_text(json.dumps({'schema': 1, 'korning': str(besok), 'utfall': 'godkänd'}))
        text, out = self.build('--ej-observerat', 'säsongsvariation')
        self.assertEqual(out['korningar'], 4)
        self.assertIn('Playwright-vägen (besok.mjs, claude/m)', text); self.assertIn('inom gränsen True', text)
        self.assertEqual(next(r['status'] for r in out['rader'] if r['etikett'] == 'BESOK-20260927T1'), 'ok')
        self.assertIn('kontrollantens bedömning: finns (KONTROLL-besok.json)', text, 'pekaren ska namnge den funna filen')
        (self.fall / 'KONTROLL-trasig.json').write_text('[1, 2]'); (self.fall / 'KONTROLL-null.json').write_text(json.dumps({'korning': None}))
        (self.fall / 'KVALITETSBILD.md').unlink()  # verktyget skriver aldrig över en befintlig utfil
        text2, out2 = self.build('--leverans', 'revision=abc')
        self.assertIn('ingen leveransbindning', next(r['status'] for r in out2['rader'] if r['etikett'] == 'BESOK-20260927T1'))
        self.assertIn('## 1. Tekniskt prövat', text)
        self.assertIn('axe violations 0, incomplete 1', text)
        self.assertIn('Lighthouse mobile', text)
        self.assertIn('## 2. Professionellt bedömt', text)
        self.assertIn('verdict: "approved"', text)
        self.assertIn('blockerande fynd: 0', text)
        self.assertIn('KONTROLL SAKNAS', text, 'ett scenario utan kontrollantens bedömning är inte avgjort')
        self.assertIn('## 3. Ej observerat', text)
        self.assertIn('säsongsvariation', text)
        self.assertIn('mänskliga användarprov', text)

    def test_tomt_fall_ger_ej_provat_och_ej_bedomt(self):
        text, out = self.build()
        self.assertEqual(out['korningar'], 0)
        self.assertIn('ej prövat', text)
        self.assertIn('ej bedömt', text)

    def test_befintlig_utfil_skrivs_inte_over(self):
        (self.fall / 'KVALITETSBILD.md').write_text('gammal')
        done = subprocess.run([sys.executable, '-B', str(HERE / 'kvalitetsbild.py'), '--fall', str(self.fall), '--ut', str(self.fall / 'KVALITETSBILD.md')], capture_output=True, text=True)
        self.assertNotEqual(done.returncode, 0)
        self.assertEqual((self.fall / 'KVALITETSBILD.md').read_text(), 'gammal')


if __name__ == '__main__':
    unittest.main()
