"""Check rerun/migration behavior without installing dependencies or Homebrew."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PYTHON312 = shutil.which('python3.12')


class PythonEnvironmentTest(unittest.TestCase):
    def shell(self, root, command, **env):
        return subprocess.run(
            ['bash', '-euc', 'ROOT="$1"; source "$2"; ' + command,
             'test', str(root), str(ROOT / 'scripts/python-env.sh')],
            env={**os.environ, **env}, text=True, capture_output=True)

    def test_explicit_wrong_python_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wrong = root / 'python3.14'
            wrong.write_text('#!/bin/sh\nexit 1\n')
            wrong.chmod(0o755)
            result = self.shell(root, 'select_python312', SIM_PYTHON=str(wrong))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('must point to Python 3.12', result.stderr)

    @unittest.skipUnless(PYTHON312, 'Requires Python 3.12')
    def test_installs_missing_python_through_homebrew(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            brew = root / 'brew'
            brew.write_text('''#!/bin/bash
set -eu
if [[ "$1" == --prefix ]]; then
    echo "$TEST_PREFIX"
else
    [[ "$1 $2" == 'install python@3.12' ]]
    /bin/mkdir -p "$TEST_PREFIX/opt/python@3.12/bin"
    /bin/ln -s "$TEST_PYTHON312" "$TEST_PREFIX/opt/python@3.12/bin/python3.12"
    echo installed > "$TEST_PREFIX/install-called"
fi
''')
            brew.chmod(0o755)
            result = self.shell(root, '''
command() {
    if [[ "$*" == '-v python3.12' ]]; then return 1; fi
    if [[ "$*" == '-v brew' ]]; then echo "$ROOT/brew"; return; fi
    builtin command "$@"
}
select_python312
is_python312 "$WORKSHOP_PYTHON"
''', SIM_PYTHON='', TEST_PREFIX=str(root), TEST_PYTHON312=PYTHON312)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / 'install-called').exists())

    @unittest.skipUnless(PYTHON312, 'Requires Python 3.12')
    def test_repairs_old_environment_preserves_data_and_reuses_on_rerun(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / '.venv'
            (old / 'bin').mkdir(parents=True)
            (old / 'bin/python').write_text('#!/bin/sh\nexit 1\n')
            (old / 'bin/python').chmod(0o755)
            (old / 'model.ckpt').write_text('saved model')
            (root / 'data').mkdir()
            (root / 'data/input.mp4').write_text('saved input')
            command = 'select_python312; ensure_python312_env "$ROOT/.venv"'
            result = self.shell(root, command, SIM_PYTHON=PYTHON312)
            self.assertEqual(result.returncode, 0, result.stderr)
            backups = list((root / 'data/environment-backups').glob('*/environment'))
            self.assertEqual(len(backups), 1)
            self.assertEqual((backups[0] / 'model.ckpt').read_text(), 'saved model')
            self.assertEqual((root / 'data/input.mp4').read_text(), 'saved input')
            (old / 'keep-on-rerun').touch()
            result = self.shell(root, command, SIM_PYTHON=PYTHON312)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((old / 'keep-on-rerun').exists())
            self.assertEqual(len(list((root / 'data/environment-backups').iterdir())), 1)

    @unittest.skipUnless(PYTHON312, 'Requires Python 3.12')
    def test_launchers_ignore_active_environment_and_pythonpath(self):
        for launcher in ('gvhmr', 'sim'):
            with self.subTest(launcher=launcher):
                result = subprocess.run(
                    [str(ROOT / launcher), '--help'], cwd=ROOT, text=True,
                    capture_output=True,
                    env={**os.environ, 'VIRTUAL_ENV': '/nonexistent/wrong-env',
                         'PYTHONPATH': '/nonexistent/packages',
                         'PYTHONHOME': '/nonexistent/python'})
                # Only exercise installed environments; clean CI checks migration above.
                env_dir = '.venv' if launcher == 'gvhmr' else '.venv-sim'
                if (ROOT / env_dir / 'bin/python').exists():
                    self.assertEqual(result.returncode, 0, result.stderr)
                else:
                    self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
