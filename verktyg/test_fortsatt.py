# -*- coding: utf-8 -*-
import io
import contextlib
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fortsatt as fs  # noqa: E402


def kor(*args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = fs.main(list(args))
    return code, json.loads(out.getvalue())


def bestallning(kund, post='DIGITALA-2-BESTALLNING-20260927', omfattning='privat-leverans', lanseringsmandat=None, testfall=False, namn='Provfirma AB'):
    b = {'schema': 1, 'post': post, 'kalla': 'nortropic-projektkontor docs/decisions.md @ 0000000', 'kund': namn, 'omfattning': omfattning,
         'lanseringsmandat': lanseringsmandat, 'utdrag': 'Beställning: hela kedjan till färdig privat leverans.', 'testfall': testfall}
    (Path(kund) / 'BESTALLNING.json').write_text(json.dumps(b, ensure_ascii=False))
    return b


class Vagen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.k = Path(self.tmp.name) / 'kund'; self.k.mkdir(); self.f = str(Path(self.tmp.name) / 'fall')
        for n in ('PROJECT-BRIEF.md', 'research.md', 'TESTDATA.md'):
            (self.k / n).write_text('syntetisk kundfil\n')
        for n in ('DRIFT.json', 'INTERVJU.json'):
            (self.k / n).write_text('{"schema": 1, "syntetisk": true}\n')
        (self.k / 'VERKSAMHET.json').write_text('{"schema": 1, "namn": "Provfirma AB", "fiktiv": false}\n')

    def tearDown(self):
        self.tmp.cleanup()

    def klar(self, steg, utforare='claude', **extra):
        args = ['--fall', self.f, 'klart', '--steg', steg, '--utfall', 'klar', '--not', 'gjort', '--utforare', utforare]
        for k, v in extra.items():
            for x in (v if isinstance(v, list) else [v]):
                args += ['--' + k, x]
        return kor(*args)

    def fram_till(self, *steg):
        for st in steg:
            code, r = kor('--fall', self.f); self.assertEqual((r['nasta'], r['lage']), (st, 'påbörjat')); self.klar(st)

    def test_vagen_laddar_nasta_steg_och_binder_bestallningen(self):
        code, r = kor('--kund', str(self.k), '--fall', self.f)
        self.assertEqual((code, r['nasta'], r['lage']), (0, 'uppstart', 'påbörjat'))
        self.assertTrue(Path(r['arbetsyta']).joinpath('LADDNING.json').is_file()); self.assertTrue(Path(r['nasta_md']).is_file())
        self.assertIn('## Redan utfört i fallet', Path(r['nasta_md']).read_text())
        self.assertEqual(stat.S_IMODE(os.stat(Path(self.f) / 'LAGE.json').st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(Path(self.f) / 'NASTA.md').st_mode), 0o600)
        self.klar('uppstart'); self.fram_till('beredning')
        code, r = kor('--fall', self.f)
        self.assertEqual((r['nasta'], r['lage']), ('intervju', 'blockerad')); self.assertIn('BESTALLNING.json saknas', r['meddelande'])
        code, r = kor('--fall', self.f); s = fs.las(self.f)
        self.assertEqual(s['steg']['intervju']['beroenden'].count(r['meddelande']), 1, 'blockeringsskälet ska inte dubbleras')
        b = bestallning(self.k)
        code, r = kor('--fall', self.f, '--bestallning', 'DIGITALA-2-BESTALLNING-20260927')
        self.assertEqual((r['nasta'], r['lage']), ('intervju', 'påbörjat'))
        s = fs.las(self.f); self.assertEqual(s['bestallning']['post'], b['post']); self.assertEqual(len(s['bestallning']['sha256']), 64)
        self.assertEqual(json.loads(Path(r['arbetsyta']).joinpath('LADDNING.json').read_text())['bestallning'], b['post'])
        self.assertIn('omfattning', Path(r['nasta_md']).read_text())
        # ändrad beställning bokförs som ombindning
        bestallning(self.k, omfattning='helhet', lanseringsmandat='DIGITALA-3-LANSERING-20260927')
        self.klar('intervju'); kor('--fall', self.f); s = fs.las(self.f)
        self.assertEqual([x['handling'] for x in s['logg'] if 'beställning' in x['handling']], ['beställning bunden', 'beställning ombunden'])
        self.assertEqual(s['bestallning']['lanseringsmandat'], 'DIGITALA-3-LANSERING-20260927')

    def test_bestallning_vagras_vid_fel_kund_id_eller_fiktiv_utan_testfall(self):
        kor('--kund', str(self.k), '--fall', self.f); self.klar('uppstart'); self.fram_till('beredning')
        bestallning(self.k, namn='Annan AB'); code, r = kor('--fall', self.f); self.assertEqual(code, 2); self.assertIn('namn', r['vagrad'])
        bestallning(self.k, post='fel id'); code, r = kor('--fall', self.f); self.assertEqual(code, 2); self.assertIn('post', r['vagrad'])
        bestallning(self.k, omfattning=['finns-inte']); code, r = kor('--fall', self.f); self.assertEqual(code, 2); self.assertIn('omfattning', r['vagrad'])
        bestallning(self.k); code, r = kor('--fall', self.f, '--bestallning', 'DIGITALA-9-ANNAN-20260927'); self.assertEqual(code, 2); self.assertIn('stämmer inte', r['vagrad'])
        (self.k / 'VERKSAMHET.json').write_text('{"schema": 1, "namn": "Provfirma AB", "fiktiv": true}\n')
        bestallning(self.k); code, r = kor('--fall', self.f); self.assertEqual(code, 2); self.assertIn('testfall', r['vagrad'])
        bestallning(self.k, testfall=True); code, r = kor('--fall', self.f); self.assertEqual((code, r['nasta'], r['lage']), (0, 'intervju', 'påbörjat'))
        (self.k / 'VERKSAMHET.json').unlink(); code, r = kor('--fall', self.f); self.assertEqual(code, 2); self.assertIn('VERKSAMHET.json saknas', r['vagrad'])
        (self.k / 'VERKSAMHET.json').write_text('{"schema": 1, "namn": "Provfirma AB", "fiktiv": true}\n')
        s = fs.las(self.f); s['ordning'].append('finns-inte'); s['steg']['finns-inte'] = dict(s['steg']['uppstart']); fs.spara(self.f, s)
        code, r = kor('--fall', self.f); self.assertEqual(code, 2); self.assertIn('inte längre finns', r['vagrad'])
        self.assertTrue(fs.las(self.f)['bestallning']['testfall'])

    def test_steg_utanfor_omfattningen_markeras_av_verktyget_och_ateroppnas_vid_utvidgad_bestallning(self):
        kor('--kund', str(self.k), '--fall', self.f); self.klar('uppstart'); self.fram_till('beredning')
        bestallning(self.k, omfattning=['intervju', 'research'])
        (self.k / 'KANALBEHOV.json').write_text(json.dumps({'seo': False, 'sokkonsol': False, 'lokal-synlighet': False, 'annonsberedning': False, 'uppfoljning': False}))
        self.fram_till('intervju', 'research')
        code, r = kor('--fall', self.f); self.assertEqual((r['nasta'], r['lage']), ('matning', 'påbörjat'))
        s = fs.las(self.f); self.assertEqual((s['steg']['brief']['status'], s['steg']['brief']['markering']), ('inte tillämpligt', 'verktyg'))
        bestallning(self.k, omfattning='privat-leverans')
        code, r = kor('--fall', self.f); self.assertEqual((r['nasta'], r['lage']), ('brief', 'påbörjat'))
        s = fs.las(self.f); self.assertEqual(s['steg']['matning']['status'], 'påbörjat'); self.assertIn('återöppnat', [x['handling'] for x in s['logg']])

    def test_underkant_loopar_samma_steg_och_sidoeffekter_bevaras(self):
        bestallning(self.k)
        kor('--kund', str(self.k), '--fall', self.f, '--bestallning', 'DIGITALA-2-BESTALLNING-20260927')
        self.klar('uppstart'); self.fram_till('beredning', 'intervju', 'research', 'brief', 'koncept')
        code, r = kor('--fall', self.f); self.assertEqual(r['nasta'], 'bygge')
        code, r = kor('--fall', self.f, 'klart', '--steg', 'bygge', '--utfall', 'underkand', '--not', 'axe 2 violations', '--sidoeffekt', 'förhandsvisning driftsatt: dpl-1 (privat)')
        self.assertEqual(r['status'], 'underkänd'); self.assertIn('omprov av bygge', r['nasta'])
        code, r = kor('--fall', self.f, '--utforare', 'codex')
        self.assertEqual((r['nasta'], r['lage']), ('bygge', 'påbörjat')); self.assertIn('laddning-bygge-2', r['arbetsyta'])
        self.assertIn('förhandsvisning driftsatt: dpl-1 (privat)', Path(r['nasta_md']).read_text())
        code, r = kor('--fall', self.f, 'status')
        self.assertEqual(r['utforare_senast'], 'codex'); self.assertEqual(r['underkanda'], {'bygge': 1}); self.assertEqual(r['sidoeffekter'], ['bygge: förhandsvisning driftsatt: dpl-1 (privat)'])
        self.assertEqual([x['utforare'] for x in fs.las(self.f)['logg']][-3:], ['claude', 'claude', 'codex'])

    def test_kanalsteg_styrs_av_kanalbehov_och_vagen_slutar_vid_leverans_utan_lanseringsmandat(self):
        bestallning(self.k)
        kor('--kund', str(self.k), '--fall', self.f)
        self.klar('uppstart'); self.fram_till('beredning', 'intervju', 'research', 'brief', 'koncept', 'bygge', 'redaktionellt-pass')
        code, r = kor('--fall', self.f)
        self.assertEqual((r['nasta'], r['lage']), ('seo', 'blockerad')); self.assertIn('KANALBEHOV.json saknas', r['meddelande'])
        (self.k / 'KANALBEHOV.json').write_text(json.dumps({'seo': True, 'sokkonsol': False, 'lokal-synlighet': False, 'annonsberedning': False, 'uppfoljning': True}))
        self.fram_till('seo', 'matning', 'kritik', 'granskning-d', 'qa', 'provare', 'uppfoljning', 'prelaunch')
        code, r = kor('--fall', self.f); self.assertEqual(r['nasta'], 'leverans'); self.klar('leverans', kvitto=str(self.k / 'VERKSAMHET.json'))
        code, r = kor('--fall', self.f)
        self.assertEqual(r['lage'], 'slut'); self.assertIn('färdig privat leverans', r['meddelande']); self.assertNotIn('lansering', r['meddelande'].split('leverans')[-1])
        s = fs.las(self.f)
        self.assertEqual({n: s['steg'][n]['status'] for n in ('annonsberedning', 'lokal-synlighet', 'sokkonsol', 'lansering', 'drift')}, {n: 'inte tillämpligt' for n in ('annonsberedning', 'lokal-synlighet', 'sokkonsol', 'lansering', 'drift')})
        self.assertEqual(s['steg']['leverans']['kvitton'], [str((self.k / 'VERKSAMHET.json').resolve())])
        # lanseringsmandatet kommer EFTER färdig privat leverans (normalfallet): lansering, sokkonsol och drift återöppnas
        bestallning(self.k, omfattning='helhet', lanseringsmandat='DIGITALA-3-LANSERING-20260927')
        code, r = kor('--fall', self.f); self.assertEqual((r['nasta'], r['lage']), ('lansering', 'påbörjat'))
        s = fs.las(self.f); self.assertEqual(s['steg']['sokkonsol']['status'], 'inte tillämpligt', 'kanalbehovet säger fortfarande false'); self.assertIn('återöppnat', [x['handling'] for x in s['logg']])
        self.klar('lansering')
        code, r = kor('--fall', self.f); self.assertEqual((r['nasta'], r['lage']), ('drift', 'påbörjat'))
        (self.k / 'KANALBEHOV.json').write_text(json.dumps({'seo': True, 'sokkonsol': True, 'lokal-synlighet': True, 'annonsberedning': False, 'uppfoljning': True}))
        code, r = kor('--fall', self.f); self.assertEqual((r['nasta'], r['lage']), ('lokal-synlighet', 'påbörjat')); self.klar('lokal-synlighet')
        code, r = kor('--fall', self.f); self.assertEqual((r['nasta'], r['lage']), ('sokkonsol', 'påbörjat'))
        # ett verkligt saknat externt beroende: vantar, allt annat fortsätter, omprova öppnar igen
        code, r = kor('--fall', self.f, 'klart', '--steg', 'sokkonsol', '--utfall', 'vantar', '--not', 'ingen Google-åtkomst', '--beroende', 'Search Console-egenskap verifierad av kunden')
        self.assertEqual(r['status'], fs.STATUS_VANTAR)
        code, r = kor('--fall', self.f); self.assertEqual((r['nasta'], r['lage']), ('drift', 'påbörjat')); self.assertIn('redan laddat', r['meddelande'])
        self.assertIn('Search Console-egenskap verifierad av kunden', Path(r['nasta_md']).read_text()); self.assertEqual(len([x for x in Path(self.f).iterdir() if x.name.startswith('laddning-drift-')]), 1)
        self.klar('drift')
        code, r = kor('--fall', self.f); self.assertEqual(r['lage'], 'slut'); self.assertIn('väntar på externt beroende: sokkonsol', r['meddelande']); self.assertIn('och lansering', r['meddelande'])
        code, r = kor('--fall', self.f, 'omprova', '--steg', 'sokkonsol', '--not', 'egenskapen verifierad'); self.assertEqual(r['var'], fs.STATUS_VANTAR)
        code, r = kor('--fall', self.f); self.assertEqual((r['nasta'], r['lage']), ('sokkonsol', 'påbörjat'))
        self.assertEqual(fs.las(self.f)['steg']['annonsberedning']['status'], 'inte tillämpligt')

    def test_klart_krav_laddat_steg_och_fel_vagras(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(fs.main(['--fall', self.f]), 2)
        code, r = kor('--kund', str(self.k), '--fall', str(HERE.parent / 'fall-i-repot')); self.assertEqual(code, 2); self.assertIn('får inte ligga i repot', r['vagrad'])
        kor('--kund', str(self.k), '--fall', self.f)
        code, r = kor('--fall', self.f, 'klart', '--steg', 'finns-inte', '--utfall', 'klar', '--not', 'x'); self.assertEqual(code, 2)
        code, r = kor('--fall', self.f, 'klart', '--steg', 'uppstart', '--utfall', 'kanske', '--not', 'x'); self.assertEqual(code, 2)
        code, r = kor('--fall', self.f, 'klart', '--steg', 'uppstart', '--utfall', 'klar', '--not', 'x', '--kvitto', '/finns/inte.json'); self.assertEqual(code, 2)
        code, r = kor('--fall', self.f, 'klart', '--steg', 'beredning', '--utfall', 'klar', '--not', 'x'); self.assertEqual(code, 2); self.assertIn('inte laddat', r['vagrad'])
        code, r = kor('--fall', self.f, 'klart', '--steg', 'uppstart', '--utfall', 'vantar', '--not', 'x'); self.assertEqual(code, 2); self.assertIn('--beroende', r['vagrad'])
        code, r = kor('--fall', self.f, 'omprova', '--steg', 'uppstart', '--not', 'x'); self.assertEqual(code, 2); self.assertIn('redan öppet', r['vagrad'])


if __name__ == '__main__':
    unittest.main()
