"""Dependency-only installation must never prompt for body-model passwords."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SetupTest(unittest.TestCase):
    def executable(self, path, body):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('#!/bin/bash\nset -e\n' + body + '\n')
        path.chmod(0o755)

    def test_dependency_only_install_on_mac_and_linux_skips_auth(self):
        for system in ('Darwin', 'Linux'):
            with self.subTest(system=system), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                shutil.copy2(ROOT / 'setup.sh', root / 'setup.sh')
                shutil.copy2(ROOT / 'Dockerfile', root / 'Dockerfile')
                (root / 'scripts').mkdir()
                shutil.copy2(ROOT / 'scripts/python-env.sh', root / 'scripts/python-env.sh')
                self.executable(root / 'bin/uname',
                                f'if [[ "$1" == -m ]]; then echo x86_64; else echo {system}; fi')
                for command in ('ffmpeg', 'ffprobe', 'docker', 'nvidia-smi', 'git'):
                    self.executable(root / 'bin' / command, 'exit 0')
                self.executable(root / 'bin/sysctl', 'echo 1')  # Apple Silicon
                self.executable(root / 'sim', 'exit 0')
                self.executable(root / 'workshop', 'echo "$*" >> "$TEST_CALLS"')
                for folder in ('.venv', '.venv-sim', '.venv-gmr'):
                    self.executable(root / folder / 'bin/python', 'exit 0')
                    self.executable(root / folder / 'bin/gvhmr', 'echo "$*" >> "$TEST_CALLS"')
                    (root / folder / 'pyvenv.cfg').touch()
                calls = root / 'calls.log'
                result = subprocess.run(['bash', str(root / 'setup.sh'), '--deps-only'],
                                        text=True, capture_output=True, env={
                                            **os.environ, 'PATH': f'{root / "bin"}:/usr/bin:/bin',
                                            'TEST_CALLS': str(calls), 'WORKSHOP_IMAGE': '',
                                        })
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('./workshop auth', result.stdout)
                self.assertEqual(calls.read_text() if calls.exists() else '',
                                 'doctor\n' if system == 'Linux' else '')

    def test_docker_viewer_uses_next_free_port_or_explicit_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copy2(ROOT / 'sim', root / 'sim')
            (root / 'scripts').mkdir()
            shutil.copy2(ROOT / 'scripts/python-env.sh', root / 'scripts/python-env.sh')
            self.executable(root / 'bin/ss', 'if [[ "$*" == *8080* ]]; then echo LISTEN; fi')
            self.executable(root / 'bin/docker',
                            'if [[ "$*" == *run* ]]; then echo "$SIM_PORT" > "$TEST_PORT"; fi')
            port = root / 'port.txt'
            for override, expected in (('', '8081'), ('8095', '8095')):
                result = subprocess.run(['bash', str(root / 'sim'), '--docker', 'play', 'examples/cartwheel'],
                                        text=True, capture_output=True, env={
                                            **os.environ, 'PATH': f'{root / "bin"}:/usr/bin:/bin',
                                            'SIM_PORT': override, 'TEST_PORT': str(port),
                                        })
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(port.read_text().strip(), expected)
                self.assertIn(f'http://localhost:{expected}', result.stdout)
