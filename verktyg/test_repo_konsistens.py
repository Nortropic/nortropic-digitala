"""Repots egen konsistens: stegdefinitionen, pinnarna, mallarna, schemadialekten mot Runtime och proveniensen."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROT = HERE.parent
sys.path.insert(0, str(HERE))
import ladda_steg  # noqa: E402
import pinna  # noqa: E402

RUNTIME = Path(os.environ.get('NR_HOST_ROOT') or (ROT.parent / 'Nortropic Runtime'))


class Konsistens(unittest.TestCase):
    def test_stegdefinitionen_ar_giltig_och_varje_professionsfil_finns_och_ar_pinnad(self):
        data = ladda_steg.las_steg(ROT)
        pins = ladda_steg.las_pinnar(ROT)
        self.assertEqual(pinna.pinnar(ROT), pins, 'pinnarna stämmer med filerna (annars: nytt beslut, verktyg/pinna.py --skriv)')
        for name, step in data['steg'].items():
            for item in step['underlag']:
                if item['klass'] == 'profession':
                    self.assertTrue((ROT / item['fil']).is_file(), '%s: %s' % (name, item['fil']))
                    self.assertIn(item['fil'], pins)
        self.assertEqual({s['mandat'] for s in data['steg'].values()}, {'staende', 'bestallning'})

    def test_varje_steg_laddas_i_en_arbetsyta_utanfor_repot(self):
        import tempfile
        data = ladda_steg.las_steg(ROT)
        tmp = Path(tempfile.mkdtemp(prefix='nd-steg-'))
        kund = tmp / 'kund'
        kund.mkdir()
        for name in ('PROJECT-BRIEF.md', 'research.md', 'TESTDATA.md'):
            (kund / name).write_text('syntetisk kundfil\n')
        for name, step in data['steg'].items():
            receipt = ladda_steg.ladda(ROT, name, tmp / name, kund=kund,
                                       bestallning='PROV-BESTALLNING-1' if step['mandat'] == 'bestallning' else None)
            self.assertTrue(all(r['status'] == 'laddad' for r in receipt['underlag'] if r['klass'] == 'profession'), name)

    def test_kritikmallarna_har_platshallare_och_scheman_i_runtimes_dialekt(self):
        probe = 'import json,sys; from runtime.web_critique import check_schema; check_schema(json.load(open(sys.argv[1]))); print("ok")'
        self.assertTrue((RUNTIME / 'runtime/web_critique.py').is_file(), 'Runtime hittas inte: sätt NR_HOST_ROOT')
        python = RUNTIME / '.runtime/temporal-venv/bin/python'
        self.assertTrue(python.is_file(), 'Runtimes venv saknas')
        for schema in sorted((ROT / 'kritik').glob('SCHEMA-*.json')):
            fraga = ROT / 'kritik' / schema.name.replace('SCHEMA-', 'FRAGA-').replace('.json', '.md')
            self.assertTrue(fraga.is_file(), schema.name)
            self.assertTrue(re.search(r'\{\{[A-ZÅÄÖ0-9_]+\}\}', fraga.read_text()) or 'femsekunderstest' in fraga.name, fraga.name)
            done = subprocess.run([str(python), '-B', '-c', probe, str(schema)], cwd=RUNTIME, capture_output=True, text=True,
                                  env=dict(os.environ, NR_HOST_ROOT=str(RUNTIME), PYTHONDONTWRITEBYTECODE='1'))
            self.assertEqual(done.returncode, 0, schema.name + ': ' + done.stderr[-400:])

    def test_profilen_och_mallarna_ar_valformade(self):
        profil = json.loads((ROT / 'matning/PROFIL.json').read_text())
        self.assertEqual(set(profil), {'schema', 'beskrivning', 'vyer', 'axe_taggar', 'delar', 'sektioner', 'krav'})
        for spec in profil['vyer'].values():
            self.assertEqual(set(spec), {'width', 'height', 'deviceScaleFactor', 'isMobile', 'hasTouch'})
        mall = (ROT / 'provare/UPPGIFT-MALL.md').read_text()
        self.assertIn('Startadress: {{STARTADRESS}}', mall)
        self.assertIn('{{KOMMANDO}}', mall)
        self.assertIn('{{SCENARIO}}', (ROT / 'provare/KONTROLL-MALL.md').read_text())

    def test_proveniensen_stammer_med_filerna(self):
        prov = json.loads((ROT / 'PROVENIENS.json').read_text())
        import hashlib
        for row in prov['filer']:
            path = ROT / row['fil']
            self.assertTrue(path.is_file(), row['fil'])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), row['sha256'], row['fil'] + ' har ändrats sedan migreringen')

    def test_inga_hemligheter_eller_skyddade_adresser_i_repot(self):
        bad = re.compile(r'vercel\.app|VERCEL_AUTOMATION_BYPASS_SECRET=|\.secret\b.*=|dpl_[A-Za-z0-9]{10,}')
        for path in ROT.rglob('*'):
            if path.is_file() and '.git' not in path.parts and path.suffix in ('.md', '.json', '.py', '.txt') and path.name != Path(__file__).name:
                text = path.read_text(encoding='utf-8', errors='replace')
                self.assertIsNone(bad.search(text), str(path))


class MandatOchKunskapsgranser(unittest.TestCase):
    """Etapp 2 i HELHET-20260927: inga ägarstopp, ingen automatisk praxis, inga Norrglänta-härledda stilregler."""

    def test_inga_agarstopp_i_steg_arbetssatt_eller_ingang(self):
        for name in ('steg/steg.json', 'ARBETSSATT.md', 'AGENTS.md', 'MANDAT.md'):
            text = (ROT / name).read_text(encoding='utf-8').lower()
            self.assertNotIn('briefstopp', text, name)
        self.assertIn('En beställning bär hela det accepterade uppdraget', (ROT / 'MANDAT.md').read_text(encoding='utf-8'))

    def test_erfarenhet_klassas_och_blir_inte_praxis_av_antal(self):
        text = (ROT / 'kunskap/LARDOMAR.md').read_text(encoding='utf-8')
        for word in ('observation', 'kundpreferens', 'hypotes', 'dokumenterad felorsak'):
            self.assertIn(word, text)
        for name in ('ARBETSSATT.md', 'AGENTS.md', 'kunskap/REGISTER.md', 'kunskap/LARDOMAR.md'):
            self.assertNotIn('två relevanta tillämpningar', (ROT / name).read_text(encoding='utf-8'), name)

    def test_kvalitetskriterierna_ar_uppgiftsmotiverade_och_norrglanta_ar_inte_referens(self):
        text = (ROT / 'KVALITET.md').read_text(encoding='utf-8')
        self.assertNotIn('Designspecificitet bedöms före allt annat', text)
        self.assertIn('underkänt som kvalitetsresultat', text)
        self.assertIn('underkänt som kvalitetsresultat', (ROT / 'MANDAT.md').read_text(encoding='utf-8'))
        fraga = (ROT / 'kritik/FRAGA-renderingslasning.md').read_text(encoding='utf-8')
        self.assertNotIn('exakt en primär handling', fraga)
        krav = json.loads((ROT / 'matning/PROFIL.json').read_text(encoding='utf-8'))['krav']
        self.assertIn('briefen', krav['h1']); self.assertIn('briefen', krav['handling'])



if __name__ == '__main__':
    unittest.main()
