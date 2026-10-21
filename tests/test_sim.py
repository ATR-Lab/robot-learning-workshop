"""Policy bundle boundaries and portable launch behavior; no GPU dependencies."""
import importlib.util
import io
import json
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

spec = importlib.util.spec_from_file_location('sim', Path(__file__).parents[1] / 'scripts/sim.py')
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)


def make_bundle(root):
    folder = root / 'policies/demo'
    folder.mkdir(parents=True)
    (root / 'robot').mkdir()
    (root / 'robot/k1.xml').write_text('<mujoco/>')
    (root / 'robot/mesh.stl').write_bytes(b'mesh')
    (folder / 'policy.onnx').write_bytes(b'onnx')
    (folder / 'motion.npz').write_bytes(b'motion')
    config = dict(onnx='policy.onnx', motion='motion.npz', robot_xml='../../robot/k1.xml',
                  joint_names=[str(i) for i in range(22)], obs_dim=119)
    (folder / 'config.json').write_text(json.dumps(config))
    (root / 'untrusted.py').write_text('raise RuntimeError("must never run")')


class BundleTests(unittest.TestCase):
    def test_plain_onnx_download_is_prepared_automatically(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_bundle(root / 'prepared')
            response = io.BytesIO(b'onnx model')
            response.url = 'https://example.org/policy.onnx'
            helper = SimpleNamespace(prepare_onnx=lambda path, policies: root / 'prepared')
            with patch.object(s, 'POLICIES', root / 'installed'), \
                    patch.object(s, 'urlopen', return_value=response), \
                    patch.dict(sys.modules, {'prepare_policy': helper}):
                installed = s.resolve_source('https://example.org/policy.onnx')
            self.assertTrue(s.validate_bundle(installed).is_file())

    def test_download_import_and_data_only_export_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source'
            make_bundle(source)
            archive = io.BytesIO()
            with zipfile.ZipFile(archive, 'w') as z:
                for path in source.rglob('*'):
                    if path.is_file():
                        z.write(path, path.relative_to(source))
            response = io.BytesIO(archive.getvalue())
            response.url = 'https://example.org/policy.zip'
            with patch.object(s, 'POLICIES', root / 'installed'), patch.object(s, 'urlopen', return_value=response):
                installed = s.import_bundle('https://example.org/policy.zip', 'demo')
                s.pack_bundle('demo', root / 'share.zip')
                with zipfile.ZipFile(root / 'share.zip') as z:
                    self.assertIn('robot/mesh.stl', z.namelist())
                    self.assertNotIn('untrusted.py', z.namelist())
                restored = s.import_bundle(str(root / 'share.zip'), 'restored')
                self.assertEqual(s.validate_bundle(restored).read_text(), s.validate_bundle(installed).read_text())
                with self.assertRaises(FileExistsError):
                    s.import_bundle(str(source), 'demo')

    def test_rejects_zip_traversal_and_symlinks(self):
        for name in ('../outside', '/absolute', 'C:/windows', 'dir\\outside'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                archive = Path(tmp) / 'bad.zip'
                with zipfile.ZipFile(archive, 'w') as z:
                    z.writestr(name, b'bad')
                with self.assertRaises(ValueError):
                    s.unpack(archive, Path(tmp) / 'unpacked')
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / 'link.zip'
            item = zipfile.ZipInfo('link')
            item.external_attr = (stat.S_IFLNK | 0o777) << 16
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr(item, '/etc/passwd')
            with self.assertRaises(ValueError):
                s.unpack(archive, Path(tmp) / 'unpacked')

    def test_rejects_missing_motion_and_escaping_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_bundle(root)
            (root / 'policies/demo/motion.npz').unlink()
            with self.assertRaises(FileNotFoundError):
                s.validate_bundle(root)
            (root / 'policies/demo/motion.npz').touch()
            config = s.find_config(root)
            cfg = json.loads(config.read_text())
            cfg['robot_xml'] = '../../../outside.xml'
            config.write_text(json.dumps(cfg))
            with self.assertRaisesRegex(ValueError, 'escapes'):
                s.validate_bundle(root)

    def test_native_mac_uses_mjpython_but_headless_and_docker_use_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_bundle(root)
            with patch.object(s.sys, 'platform', 'darwin'), patch.dict(s.os.environ, {}, clear=True), \
                    patch.object(s.subprocess, 'run') as run:
                s.main(['play', str(root)])
                self.assertTrue(run.call_args.args[0][0].endswith('/mjpython'))
                s.main(['play', str(root), '--check'])
                self.assertEqual(run.call_args.args[0][0], s.sys.executable)
            with patch.object(s.sys, 'platform', 'linux'), patch.dict(s.os.environ, {'SIM_DOCKER': '1'}), \
                    patch.object(s.subprocess, 'run') as run:
                s.main(['play', str(root)])
                self.assertIn('--web', run.call_args.args[0])
                s.main(['play', str(root), '--check'])
                self.assertNotIn('--web', run.call_args.args[0])


if __name__ == '__main__':
    unittest.main()
