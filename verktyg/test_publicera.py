# -*- coding: utf-8 -*-
import io
import contextlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import publicera as pb  # noqa: E402


class Publicering(unittest.TestCase):
    """Ett minirepo (git init) med pinna.py, en stegdefinition och ett grönt prov; granskningskatalogen utanför repot."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.rot = Path(self.tmp.name) / 'repo'; (self.rot / 'verktyg').mkdir(parents=True); (self.rot / 'steg').mkdir(); (self.rot / 'kunskap').mkdir()
        shutil.copy(HERE / 'pinna.py', self.rot / 'verktyg' / 'pinna.py')
        (self.rot / 'kunskap' / 'a.md').write_text('a\n')
        (self.rot / 'steg' / 'steg.json').write_text(json.dumps({'schema': 1, 'beskrivning': 'x', 'steg': {'s': {'mandat': 'staende', 'syfte': 'x', 'anvisning': 'x', 'underlag': [{'fil': 'kunskap/a.md', 'klass': 'profession', 'obligatorisk': True, 'delar': 'hela'}]}}}))
        (self.rot / 'verktyg' / 'test_ok.py').write_text('import unittest\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n')
        subprocess.run([sys.executable, '-B', 'verktyg/pinna.py', '--skriv'], cwd=self.rot, capture_output=True, check=True)
        env = dict(os.environ, GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@example.com', GIT_COMMITTER_NAME='t', GIT_COMMITTER_EMAIL='t@example.com')
        for cmd in (['git', 'init', '-q', '-b', 'main'], ['git', 'add', '-A'], ['git', 'commit', '-q', '-m', 'bas'], ['git', 'checkout', '-q', '-b', 'kandidat']):
            subprocess.run(cmd, cwd=self.rot, check=True, env=env)
        (self.rot / 'kunskap' / 'a.md').write_text('a2\n'); subprocess.run([sys.executable, '-B', 'verktyg/pinna.py', '--skriv'], cwd=self.rot, capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-q', '-am', 'kandidat'], cwd=self.rot, check=True, env=env)
        self.head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=self.rot, capture_output=True, text=True).stdout.strip()
        self.g = Path(self.tmp.name) / 'granskning'; self.g.mkdir()
        (self.g / 'review.json').write_text(json.dumps({'answer': {'verdict': 'approved', 'blocking_findings': [], 'summary': 'ok'}}))
        (self.g / 'underlag.json').write_text(json.dumps({'filer': [['x', 'repo/a', 'fil på grenen kandidat (%s)' % self.head[:7]]]}))
        self.kropp = Path(self.tmp.name) / 'KROPP.md'; self.kropp.write_text('kropp\n')

    def tearDown(self):
        self.tmp.cleanup()

    def kor(self, *extra):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = pb.main(['--rot', str(self.rot), '--gren', 'kandidat', '--granskning', str(self.g), '--titel', 'T', '--kropp', str(self.kropp), '--torr', *extra])
        return code, json.loads(out.getvalue())

    def test_torr_publicering_passerar_alla_kontroller_och_skriver_kvitto(self):
        code, r = self.kor()
        self.assertEqual(code, 0, r); self.assertTrue(r['torr']); self.assertEqual(r['head'], self.head[:7]); self.assertIsNone(r['main'])
        k = json.loads(Path(r['kvitto']).read_text())
        self.assertEqual(k['kontroller']['verdict'], 'approved'); self.assertTrue(any(l.startswith('OK') for l in k['kontroller']['prov'])); self.assertEqual(len(k['plan']), 5); self.assertIn('gh pr merge kandidat --squash', k['plan'][2])
        self.assertFalse(Path(r['kvitto']).resolve().is_relative_to(self.rot.resolve()))

    def test_vagras_utan_godkand_granskning_annan_version_smutsigt_trad_eller_rott_prov(self):
        (self.g / 'review.json').write_text(json.dumps({'answer': {'verdict': 'rejected'}}))
        code, r = self.kor(); self.assertEqual(code, 2); self.assertIn('inte godkänd', r['vagrad'])
        (self.g / 'review.json').write_text(json.dumps({'answer': {'verdict': 'approved'}}))
        (self.g / 'underlag.json').write_text(json.dumps({'filer': [['x', 'repo/a', 'fil på grenen kandidat (0000000)']]}))
        code, r = self.kor(); self.assertEqual(code, 2); self.assertIn('annan version', r['vagrad'])
        (self.g / 'underlag.json').write_text(json.dumps({'filer': [['x', 'repo/a', 'fil (%s)' % self.head[:7]]]}))
        (self.rot / 'smuts.txt').write_text('x')
        code, r = self.kor(); self.assertEqual(code, 2); self.assertIn('inte rent', r['vagrad'])
        (self.rot / 'smuts.txt').unlink()
        (self.rot / 'verktyg' / 'test_ok.py').write_text('import unittest\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(False)\n')
        subprocess.run(['git', 'commit', '-q', '-am', 'rött'], cwd=self.rot, check=True, env=dict(os.environ, GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@example.com', GIT_COMMITTER_NAME='t', GIT_COMMITTER_EMAIL='t@example.com'))
        head2 = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=self.rot, capture_output=True, text=True).stdout.strip()
        (self.g / 'underlag.json').write_text(json.dumps({'filer': [['x', 'repo/a', 'fil (%s)' % head2[:7]]]}))
        code, r = self.kor(); self.assertEqual(code, 2); self.assertIn('inte grön', r['vagrad'])
        g2 = self.rot / 'granskning-i-repot'; g2.mkdir(); shutil.copy(self.g / 'review.json', g2 / 'review.json'); shutil.copy(self.g / 'underlag.json', g2 / 'underlag.json')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = pb.main(['--rot', str(self.rot), '--gren', 'kandidat', '--granskning', str(g2), '--titel', 'T', '--kropp', str(self.kropp), '--torr'])
        self.assertEqual(code, 2); self.assertIn('utanför repot', json.loads(out.getvalue())['vagrad'])

    def test_commit_faltet_binder_exakt_och_torrlaget_kor_inga_natverkskommandon(self):
        (self.g / 'underlag.json').write_text(json.dumps({'commit': self.head, 'filer': [['x', 'repo/a', 'fil utan revision i texten']]}))
        kord = []; orig = pb.subprocess.run

        def spion(cmd, *a_, **kw):
            kord.append([str(x) for x in cmd]); return orig(cmd, *a_, **kw)
        pb.subprocess.run = spion
        try:
            code, r = self.kor()
        finally:
            pb.subprocess.run = orig
        self.assertEqual(code, 0, r)
        self.assertEqual(json.loads(Path(r['kvitto']).read_text())['kontroller']['bindning'], 'commit-fält')
        self.assertTrue(kord, 'kontrollerna kör git/prov genom subprocess')
        self.assertEqual([c[:2] for c in kord if c[0] == 'gh' or (c[0] == 'git' and c[1] in ('push', 'checkout', 'pull', 'merge'))], [], 'torrläget får inte köra push, pr, merge, checkout eller pull')
        (self.g / 'underlag.json').write_text(json.dumps({'commit': '0123456789abcdef', 'filer': [['x', 'repo/a', 'fil (%s)' % self.head[:7]]]}))
        code, r = self.kor(); self.assertEqual(code, 2); self.assertIn('annan version', r['vagrad'])
        (self.g / 'underlag.json').write_text(json.dumps({'filer': [['x', 'repo/a', 'fil (%s)' % self.head[:7]], ['y', 'repo/b', 'fil utan revision']]}))
        code, r = self.kor(); self.assertEqual(code, 2); self.assertIn('inte varje post', r['vagrad'])

    def test_tradbindning_efter_rebase_saknad_granskning_och_fel_gren_vagras(self):
        env = dict(os.environ, GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@example.com', GIT_COMMITTER_NAME='t', GIT_COMMITTER_EMAIL='t@example.com')
        # samma träd på en ny commit (t.ex. efter rebase på identisk bas): bindningen godtas och namnger ursprunget
        subprocess.run(['git', 'commit', '-q', '--allow-empty', '-m', 'rebasad (samma träd)'], cwd=self.rot, check=True, env=env)
        (self.g / 'underlag.json').write_text(json.dumps({'commit': self.head, 'filer': [['x', 'repo/a', 'fil']]}))
        code, r = self.kor(); self.assertEqual(code, 0, r)
        self.assertIn('samma träd', json.loads(Path(r['kvitto']).read_text())['kontroller']['bindning'])
        # annat träd: vägras
        (self.rot / 'kunskap' / 'a.md').write_text('a3\n'); subprocess.run([sys.executable, '-B', 'verktyg/pinna.py', '--skriv'], cwd=self.rot, capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-q', '-am', 'annat träd'], cwd=self.rot, check=True, env=env)
        code, r = self.kor(); self.assertEqual(code, 2); self.assertIn('träden skiljer sig', r['vagrad'])
        # saknad review.json / underlag.json och fel gren
        (self.g / 'review.json').unlink(); code, r = self.kor(); self.assertEqual(code, 2); self.assertIn('review.json', r['vagrad'])
        (self.g / 'review.json').write_text(json.dumps({'answer': {'verdict': 'approved'}}))
        (self.g / 'underlag.json').unlink(); code, r = self.kor(); self.assertEqual(code, 2); self.assertIn('underlag.json', r['vagrad'])
        (self.g / 'underlag.json').write_text(json.dumps({'commit': self.head, 'filer': [['x', 'repo/a', 'fil']]}))
        subprocess.run(['git', 'checkout', '-q', 'main'], cwd=self.rot, check=True, env=env)
        code, r = self.kor(); self.assertEqual(code, 2); self.assertIn('utcheckad gren', r['vagrad'])

    def test_befintlig_pr_och_worktreevanlig_plan(self):
        """Planen ska varken checka ut main eller radera den lokala grenen (main kan vara utcheckad i en annan worktree);
        mergeläget verifieras med gh pr view, inte gh:s exitkod; en redan skapad PR återanvänds."""
        code, r = self.kor(); self.assertEqual(code, 0, r)
        plan = json.loads(Path(r['kvitto']).read_text())['plan']
        self.assertEqual([p.split(' ')[:3] for p in plan], [['git', 'push', '-u'], ['gh', 'pr', 'create'], ['gh', 'pr', 'merge'], ['gh', 'pr', 'view'], ['git', 'fetch', 'origin']])
        self.assertNotIn('--delete-branch', ' '.join(plan))
        # simulerad skarp körning: gh pr create svarar "already exists", merge 0, view MERGED
        svar = {('gh', 'pr', 'create'): (1, '', 'a pull request for branch "kandidat" into branch "main" already exists: https://example.invalid/pr/7'),
                ('gh', 'pr', 'merge'): (0, '', ''), ('gh', 'pr', 'view'): (0, json.dumps({'state': 'MERGED', 'mergeCommit': {'oid': 'f' * 40}, 'number': 7, 'url': 'https://example.invalid/pr/7'}), ''),
                ('git', 'push', '-u'): (0, '', ''), ('git', 'fetch', 'origin'): (0, '', ''), ('git', 'push', 'origin'): (0, '', '')}
        orig = pb.subprocess.run

        class P:
            def __init__(self, rc, out, err): self.returncode, self.stdout, self.stderr = rc, out, err

        def falsk(cmd, *a_, **kw):
            n = tuple(str(x) for x in cmd[:3])
            if n in svar: return P(*svar[n])
            return orig(cmd, *a_, **kw)
        pb.subprocess.run = falsk
        try:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = pb.main(['--rot', str(self.rot), '--gren', 'kandidat', '--granskning', str(self.g), '--titel', 'T', '--kropp', str(self.kropp)])
        finally:
            pb.subprocess.run = orig
        r = json.loads(out.getvalue()); self.assertEqual(code, 0, r); self.assertTrue(str(r['main']).startswith('fffffff'))
        k = json.loads(Path(r['kvitto']).read_text()); self.assertEqual(k['main'], 'f' * 40); self.assertEqual(k['pr']['nummer'], 7); self.assertTrue(k['fjarrgren_borttagen']); self.assertIn('fanns redan', k['utfall'][1]['not'])

    def _skarp(self, svar, *argv):
        orig = pb.subprocess.run

        class P:
            def __init__(self, rc, out, err): self.returncode, self.stdout, self.stderr = rc, out, err

        def falsk(cmd, *a_, **kw):
            n = tuple(str(x) for x in cmd[:3])
            if n in svar: return P(*svar[n])
            return orig(cmd, *a_, **kw)
        pb.subprocess.run = falsk
        try:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = pb.main(['--rot', str(self.rot), '--gren', 'kandidat', '--granskning', str(self.g), '--titel', 'T', '--kropp', str(self.kropp), *argv])
        finally:
            pb.subprocess.run = orig
        return code, json.loads(out.getvalue())

    def test_mergeutfallet_avgors_av_pr_view_inte_av_gh_exitkod_och_ingangen_snabbspolas(self):
        env = dict(os.environ, GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@example.com', GIT_COMMITTER_NAME='t', GIT_COMMITTER_EMAIL='t@example.com')
        ingang = Path(self.tmp.name) / 'ingang'; subprocess.run(['git', 'clone', '-q', str(self.rot), str(ingang)], check=True, env=env)
        subprocess.run(['git', 'checkout', '-q', 'main'], cwd=ingang, check=True, env=env)
        bas = {('git', 'push', '-u'): (0, '', ''), ('gh', 'pr', 'create'): (0, 'https://example.invalid/pr/8', ''), ('git', 'fetch', 'origin'): (0, '', ''), ('git', 'push', 'origin'): (0, '', '')}
        merged = (0, json.dumps({'state': 'MERGED', 'mergeCommit': {'oid': 'e' * 40}, 'number': 8, 'url': 'https://example.invalid/pr/8'}), '')
        # gh pr merge faller (efterarbete i worktree) men servern har mergat: view avgör → main satt, ingången snabbspolad
        code, r = self._skarp({**bas, ('gh', 'pr', 'merge'): (1, '', "failed to run git: fatal: 'main' is already used by worktree"), ('gh', 'pr', 'view'): merged}, '--ingang', str(ingang))
        self.assertEqual(code, 0, r); self.assertEqual(r['main'], 'eeeeeee'); k = json.loads(Path(r['kvitto']).read_text())
        self.assertEqual(k['utfall'][2]['status'], 1); self.assertIn('pr view', k['utfall'][2]['not']); self.assertTrue(k['ingang']['snabbspolad'], k['ingang'])
        self.assertNotIn(str(Path.home()), Path(r['kvitto']).read_text(), 'inga privata absoluta sökvägar i kvittot')
        # view säger OPEN: avbrutet, main None
        code, r = self._skarp({**bas, ('gh', 'pr', 'merge'): (0, '', ''), ('gh', 'pr', 'view'): (0, json.dumps({'state': 'OPEN', 'mergeCommit': None, 'number': 8, 'url': 'u'}), '')})
        self.assertEqual(code, 1, r); self.assertIsNone(r['main']); self.assertIn('inte mergad (state OPEN)', r['avbrutet'])
        # view ger ogiltig JSON: avbrutet med skäl
        code, r = self._skarp({**bas, ('gh', 'pr', 'merge'): (0, '', ''), ('gh', 'pr', 'view'): (0, 'inte json', '')})
        self.assertEqual(code, 1, r); self.assertIsNone(r['main']); self.assertIn('inget giltigt svar', r['avbrutet'])
        # smutsig ingång lämnas orörd
        (ingang / 'smuts.txt').write_text('x')
        code, r = self._skarp({**bas, ('gh', 'pr', 'merge'): (0, '', ''), ('gh', 'pr', 'view'): merged}, '--ingang', str(ingang))
        self.assertEqual(code, 0, r); k = json.loads(Path(r['kvitto']).read_text()); self.assertFalse(k['ingang']['snabbspolad']); self.assertIn('inte ren', k['ingang']['ut'])


if __name__ == '__main__':
    unittest.main()
