"""Dispatcherprov med riktig syntetisk underprocess; inga publiceringscredentials."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import publicera as pb


class Publicering(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.hem = Path(self.temp.name).resolve()
        self.repos = self.hem / 'nortropic-repos'
        self.primar = self.repos / 'nortropic-digitala'
        self.ingang = self.primar / 'verktyg/publicera.py'
        self.ingang.parent.mkdir(parents=True)
        self.ingang.write_text('# enbart syntetisk sökvägsfixtur\n')
        self.host = self.repos / 'Nortropic Runtime'
        self.launcher = self.host / '.runtime/ap11/check-issuer/launch.py'
        self.launcher.parent.mkdir(parents=True)
        self.launcher.parent.chmod(0o700)
        self.python = self.host / '.runtime/temporal-venv/bin/python'
        self.python.parent.mkdir(parents=True)
        self.python.symlink_to(sys.executable)
        self.observation = self.host / 'observation.json'
        self.launcher.write_text(
            'import json,os,sys\nfrom pathlib import Path\n'
            'Path("observation.json").write_text(json.dumps({"argv":sys.argv[1:],'
            '"cwd":str(Path.cwd()),"env":dict(os.environ),"stdin":sys.stdin.read(),'
            '"isolated":sys.flags.isolated,"no_bytecode":sys.dont_write_bytecode}))\n'
            'sys.exit(0)\n')
        self.adopt()
        self.identity = patch.object(pb, '__file__', str(self.ingang))
        self.home = patch.object(pb, 'systemhem', return_value=self.hem)
        self.identity.start(); self.home.start()

    def adopt(self):
        self.launcher.chmod(0o600)
        self.adoption = self.launcher.parent / 'launcher-adoption.json'
        self.adoption.write_text(json.dumps({'schema': 'nortropic-launcher-adoption/1',
            'verdict': 'approved', 'blocking_findings': [], 'reviewer_run': 'synthetic-independent-read',
            'implementation_run': 'synthetic-author',
            'launcher_sha256': hashlib.sha256(self.launcher.read_bytes()).hexdigest()}))
        self.adoption.chmod(0o600)

    def tearDown(self):
        self.home.stop(); self.identity.stop(); self.temp.cleanup()

    def call(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
            try:
                code = pb.main(list(args))
            except SystemExit as error:
                code = error.code
        return code, output.getvalue()

    def test_verklig_underprocess_far_bara_task_fast_vag_och_isolerad_python(self):
        code, output = self.call('--task', 'digitala-prov-20260928')
        self.assertEqual((code, output), (0, ''))
        observed = json.loads(self.observation.read_text())
        self.assertEqual(observed['argv'], ['digitala', '--task', 'digitala-prov-20260928'])
        self.assertEqual(observed['cwd'], str(self.host))
        self.assertEqual(observed['stdin'], '')
        self.assertEqual(observed['isolated'], 1)
        self.assertTrue(observed['no_bytecode'])
        self.assertEqual(observed['env']['HOME'], str(self.hem))

    def test_anroparens_kod_auth_och_hostoverrides_nar_inte_hallaren(self):
        names = ('NR_HOST_ROOT', 'PYTHONPATH', 'PYTHONHOME', 'GH_TOKEN', 'GITHUB_TOKEN',
                 'GIT_DIR', 'GIT_WORK_TREE', 'GIT_CONFIG_COUNT', 'BASH_ENV', 'DYLD_INSERT_LIBRARIES')
        with patch.dict(os.environ, {**{n: 'synthetic-not-a-secret' for n in names}, 'HOME': '/synthetic/wrong-home'}):
            code, _ = self.call('--task', 'digitala-prov')
        self.assertEqual(code, 0)
        env = json.loads(self.observation.read_text())['env']
        self.assertFalse(set(names) & set(env))
        self.assertEqual(env['HOME'], str(self.hem))

    def test_kandidatens_kopia_vagras_fore_underprocess(self):
        with patch.object(pb, '__file__', str(self.hem / 'worktree/verktyg/publicera.py')):
            code, output = self.call('--task', 'digitala-prov')
        self.assertEqual(code, 2); self.assertIn('primäringången', output)
        self.assertFalse(self.observation.exists())

    def test_saknad_eller_lankad_launcher_vagras_utan_reservvag(self):
        self.launcher.unlink()
        code, output = self.call('--task', 'digitala-prov')
        self.assertEqual(code, 2); self.assertIn('hållaren saknas', output)
        target = self.hem / 'untrusted.py'; target.write_text('raise RuntimeError("must not run")\n')
        self.launcher.symlink_to(target)
        code, _ = self.call('--task', 'digitala-prov')
        self.assertEqual(code, 2); self.assertFalse(self.observation.exists())

    def test_primar_som_lank_till_kandidat_vagras(self):
        moved = self.repos / 'candidate'
        self.primar.rename(moved); self.primar.symlink_to(moved, target_is_directory=True)
        code, _ = self.call('--task', 'digitala-prov')
        self.assertEqual(code, 2); self.assertFalse(self.observation.exists())

    def test_ogiltigt_task_och_gamla_auktoritetsargument_vagras(self):
        for task in ('../uppgift', 'UPPGIFT', '-fel', 'x' * 81, 'x;y', 'x\ny', ''):
            with self.subTest(task=task):
                code, _ = self.call('--task', task)
                self.assertEqual(code, 2)
        for args in (('--gren', 'g', '--granskning', '/tmp/g', '--titel', 'x', '--kropp', '/tmp/body'),
                     ('--task', 'x', '--rot', '/tmp/candidate'), ('--task', 'x', '--torr'), ('--tas', 'x')):
            with self.subTest(args=args):
                code, _ = self.call(*args); self.assertEqual(code, 2)
        self.assertFalse(self.observation.exists())

    def test_hallarens_vagran_vidarebefordras_utan_omforsok_eller_egen_gron_status(self):
        self.launcher.write_text(self.launcher.read_text().replace('sys.exit(0)', 'sys.exit(7)'))
        self.adopt()
        code, output = self.call('--task', 'digitala-prov')
        self.assertEqual(code, 7); self.assertEqual(output, '')
        self.assertEqual(json.loads(self.observation.read_text())['argv'][-1], 'digitala-prov')

    def test_andrad_launcher_eller_sjalvgranskad_adoption_vagras_fore_exec(self):
        self.launcher.write_text(self.launcher.read_text() + '# ändrad efter adoption\n')
        code, output = self.call('--task', 'digitala-prov')
        self.assertEqual(code, 2); self.assertIn('exakt dessa bytes', output)
        self.adopt()
        record = json.loads(self.adoption.read_text()); record['reviewer_run'] = record['implementation_run']
        self.adoption.write_text(json.dumps(record))
        code, _ = self.call('--task', 'digitala-prov')
        self.assertEqual(code, 2); self.assertFalse(self.observation.exists())

    def test_oppna_rattigheter_saknad_och_lankad_adoption_vagras(self):
        self.launcher.chmod(0o644)
        code, _ = self.call('--task', 'digitala-prov'); self.assertEqual(code, 2)
        self.launcher.chmod(0o600); self.adoption.chmod(0o644)
        code, _ = self.call('--task', 'digitala-prov'); self.assertEqual(code, 2)
        self.adoption.unlink()
        code, _ = self.call('--task', 'digitala-prov'); self.assertEqual(code, 2)
        target = self.hem / 'untrusted-adoption.json'; target.write_text('{}')
        self.adoption.symlink_to(target)
        code, _ = self.call('--task', 'digitala-prov'); self.assertEqual(code, 2)
        self.assertFalse(self.observation.exists())


if __name__ == '__main__':
    unittest.main()
