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
        for name in ('VERKSAMHET.json', 'DRIFT.json'):
            (kund / name).write_text('{"schema": 1, "syntetisk": true}\n')
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
        md = (ROT / 'PROVENIENS.md').read_text(encoding='utf-8')
        for row in prov['filer']:
            path = ROT / row['fil']
            self.assertIn('`%s`' % row['fil'], md, row['fil'] + ' saknas i PROVENIENS.md')
            self.assertIn('`%s…`' % row['sha256'][:16], md, row['fil'] + ': PROVENIENS.md bär inte den gällande hashens första 16 tecken')
            self.assertEqual(path.stat().st_size, row['byte'], row['fil'] + ': PROVENIENS.json byte stämmer inte med filen')
            self.assertRegex(md, r'\| `%s` \| [^|]+ \| `[0-9a-f]{16}…`[^|]* \| %d \|' % (re.escape(row['fil']), row['byte']), row['fil'] + ': PROVENIENS.md-raden bär inte gällande byte')
            if row.get('sha256_vid_flytt'):
                self.assertIn('(flyttad: `%s…`)' % row['sha256_vid_flytt'][:16], md, row['fil'] + ': PROVENIENS.md-raden saknar den flyttade versionen')
            self.assertIn('| ' + row['not'] + ' |', md, row['fil'] + ': PROVENIENS.md-radens not skiljer sig från PROVENIENS.json')
        noter = [r['not'] for r in prov['filer'] if 'ändrad 2026' in r['not']]
        self.assertEqual(len(noter), len(set(noter)), 'två ändrade filer har identisk ändringsnot: noten ska beskriva filens egen ändring')

    def test_inga_hemligheter_eller_skyddade_adresser_i_repot(self):
        bad = re.compile(r'[a-z0-9-]{3,}\.vercel\.app|VERCEL_AUTOMATION_BYPASS_SECRET=|\.secret\b.*=|dpl_[A-Za-z0-9]{10,}')  # en förhandsvisningsadress (etikett före suffixet), inte suffixet självt
        for path in ROT.rglob('*'):
            if path.is_file() and '.git' not in path.parts and path.suffix in ('.md', '.json', '.py', '.txt') and path.name != Path(__file__).name:
                text = path.read_text(encoding='utf-8', errors='replace')
                self.assertIsNone(bad.search(text), str(path))


class MandatOchKunskapsgranser(unittest.TestCase):
    """Etapp 2 i HELHET-20260927: inga ägarstopp, ingen automatisk praxis, inga Norrglänta-härledda stilregler, i hela repot
    (text, stegdefinition, mallar och verktygens egna texter; lärdomar, proveniens och externa källor undantagna)."""

    FORBJUDET = ('briefstopp', 'två relevanta tillämpningar', 'designspecificitet före allt annat', 'exakt en primär handling',
                 'tre dial-värden', 'två–tre riktningar')

    def texter(self):
        for path in sorted(ROT.rglob('*')):
            if path.is_file() and '.git' not in path.parts and 'externa' not in path.parts and path.suffix in ('.md', '.json', '.py') \
                    and path.name not in (Path(__file__).name, 'LARDOMAR.md', 'PROVENIENS.md'):
                yield path, path.read_text(encoding='utf-8', errors='replace')

    def test_inga_agarstopp_och_ingen_praxis_av_antal_i_hela_repot(self):
        for path, text in self.texter():
            for phrase in self.FORBJUDET:
                self.assertNotIn(phrase.lower(), text.lower(), '%s bär det ersatta läget: %r' % (path.relative_to(ROT), phrase))
        self.assertIn('En beställning bär hela det accepterade uppdraget', (ROT / 'MANDAT.md').read_text(encoding='utf-8'))

    def test_erfarenhet_klassas(self):
        text = (ROT / 'kunskap/LARDOMAR.md').read_text(encoding='utf-8')
        for word in ('observation', 'kundpreferens', 'hypotes', 'dokumenterad felorsak'):
            self.assertIn(word, text)
        self.assertNotIn('två relevanta tillämpningar', text)

    def test_kvalitetskriterierna_ar_uppgiftsmotiverade_och_norrglanta_ar_inte_referens(self):
        self.assertIn('underkänt som kvalitetsresultat', (ROT / 'KVALITET.md').read_text(encoding='utf-8'))
        self.assertIn('underkänt som kvalitetsresultat', (ROT / 'MANDAT.md').read_text(encoding='utf-8'))
        krav = json.loads((ROT / 'matning/PROFIL.json').read_text(encoding='utf-8'))['krav']
        self.assertIn('briefen', krav['h1'])
        self.assertIn('briefen', krav['handling'])


if __name__ == '__main__':
    unittest.main()
