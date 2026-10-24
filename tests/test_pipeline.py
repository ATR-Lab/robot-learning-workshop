"""Exercise stage handoffs without installing GPU software on the test host."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import unittest.mock
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('workshop', Path(__file__).parents[1] / 'scripts/workshop.py')
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


class PipelineTest(unittest.TestCase):
    def setUp(self):
        # No GPU/OpenGL on the test host: the rendering probe is tested separately below.
        patcher = patch.object(w, 'video_rendering')
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_changed_input_preserves_old_results_instead_of_reusing_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / 'data/inputs/clip.mp4'
            video.parent.mkdir(parents=True)
            video.write_bytes(b'new video')
            folder = root / 'data/outputs/clip'
            (folder / 'gvhmr').mkdir(parents=True)
            (folder / 'gvhmr/hmr4d_results.pt').write_bytes(b'old motion')
            (folder / 'source.sha256').write_text('old hash')
            with patch.multiple(w, ROOT=root, DATA=root / 'data'), \
                    patch.object(w.shutil, 'which', return_value='/usr/bin/ffmpeg'), \
                    patch.object(w, 'run'):
                w.convert(video, None)
            backups = list(folder.glob('previous-*/gvhmr/hmr4d_results.pt'))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_bytes(), b'old motion')
            self.assertFalse((folder / 'gvhmr/hmr4d_results.pt').exists())

    def test_auth_logs_in_then_downloads_everything_and_checks(self):
        with tempfile.TemporaryDirectory() as tmp, \
                patch.multiple(w, ROOT=Path('/workspace'), DATA=Path(tmp)), patch.object(w, 'run') as run, \
                patch.object(w.urllib.request, 'urlretrieve',
                             side_effect=lambda url, path: Path(path).write_bytes(b'video')) as fetch:
            w.main(['auth'])
            self.assertEqual((Path(tmp) / 'inputs/tennis.mp4').read_bytes(), b'video')
        commands = [[str(arg) for arg in call.args[0]] for call in run.call_args_list]
        self.assertEqual(commands, [['/opt/gvhmr/bin/gvhmr', 'auth', 'smpl'],
                                    ['/opt/gvhmr/bin/python', '/workspace/scripts/body_models.py'],
                                    ['/opt/gvhmr/bin/gvhmr', 'download', 'demo'],
                                    ['/opt/gvhmr/bin/python', '/workspace/scripts/ready.py']])
        fetch.assert_called_once()

    def test_download_keeps_existing_sample(self):
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(w, 'DATA', Path(tmp)), patch.object(w, 'run'), \
                patch.object(w.urllib.request, 'urlretrieve') as fetch:
            (Path(tmp) / 'inputs').mkdir()
            (Path(tmp) / 'inputs/tennis.mp4').write_bytes(b'mine')
            w.main(['download'])
        fetch.assert_not_called()

    def test_missing_video_explains_where_to_put_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.multiple(w, ROOT=root, DATA=root / 'data'):
                with self.assertRaisesRegex(FileNotFoundError, r'data/inputs/clip\.mp4[\s\S]*curl'):
                    w.data_file(root / 'data/inputs/clip.mp4')

    def test_native_conversion_uses_local_env_and_same_output_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / 'dance.mp4'
            video.touch()
            python = root / '.venv/bin/python'
            with patch.multiple(w, NATIVE=True, ROOT=root, DATA=root / 'data',
                                PYTHONS={'gvhmr': python}), \
                    patch.object(w.shutil, 'which', return_value='/usr/bin/ffmpeg'), \
                    patch.object(w, 'run') as run:
                prediction, clip = w.convert(video, None)
            self.assertEqual(prediction, root / 'data/outputs/dance/gvhmr/hmr4d_results.pt')
            self.assertEqual(run.call_args_list[1].args[0][0], python)
            self.assertIn('yuv420p', run.call_args_list[0].args[0])

    def test_convert_does_not_retarget_or_require_robot_models(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / 'data/inputs/clip.mp4'
            video.parent.mkdir(parents=True)
            video.touch()
            with patch.multiple(w, ROOT=root, DATA=root / 'data'), patch.object(w, 'run') as run, \
                    patch.object(w, 'retarget') as retarget:
                prediction, clip = w.convert(video, None)
            self.assertEqual(prediction, root / 'data/outputs/clip/gvhmr/hmr4d_results.pt')
            self.assertEqual(clip, 'clip')
            self.assertEqual(run.call_count, 2)
            retarget.assert_not_called()

    def test_video_to_robot_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data, pipeline = root / 'data', root / 'pipeline'
            body = data / 'body_models/smplx/SMPLX_NEUTRAL.npz'
            body.parent.mkdir(parents=True)
            body.touch()
            video = data / 'inputs/123-test.mp4'
            video.parent.mkdir()
            video.touch()
            calls = []

            def fake_run(command, **kwargs):
                cmd = list(map(str, command))
                calls.append(cmd)
                if cmd[0] == 'ffmpeg':
                    Path(cmd[-1]).touch()
                elif cmd[1].endswith('recover.py'):
                    Path(cmd[3]).touch()
                elif cmd[1].endswith('retarget_gvhmr.py'):
                    Path(cmd[cmd.index('--output') + 1]).touch()
                elif cmd[1].endswith('batch_gmr_pkl_to_csv.py'):
                    folder = Path(cmd[-1]) / 'csv'
                    folder.mkdir()
                    (folder / 'clip_123_test_booster_k1.csv').write_text('data')
                elif cmd[1].endswith('render_motion.py'):
                    Path(cmd[3]).touch()

            with patch.multiple(w, ROOT=root, DATA=data, PIPELINE=pipeline), patch.object(w, 'run', side_effect=fake_run):
                w.process(video, None)
            self.assertEqual((data / 'outputs/clip_123_test/clip_123_test.csv').read_text(), 'data')
            self.assertTrue((data / 'outputs/clip_123_test/robot_data/booster_k1/clip_123_test_booster_k1.pkl').is_file())
            self.assertEqual(len(calls), 5)
            self.assertTrue((data / 'outputs/clip_123_test/clip_123_test_k1.mp4').is_file())
            self.assertIn('--beside', calls[-1])
            self.assertIn('--camera-from', calls[-1])
            self.assertTrue(calls[1][-1].endswith('clip_123_test_pose.mp4'))
            self.assertFalse(any('train.py' in arg or 'csv_to_npz.py' in arg for call in calls for arg in call))

    def test_retarget_by_clip_name_and_no_video(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / 'data'
            for path in (data / 'outputs/tennis/gvhmr/hmr4d_results.pt',
                         data / 'body_models/smplx/SMPLX_NEUTRAL.npz'):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()

            def fake_run(command, **kwargs):
                cmd = list(map(str, command))
                if cmd[1].endswith('batch_gmr_pkl_to_csv.py'):
                    (Path(cmd[-1]) / 'csv').mkdir()
                    (Path(cmd[-1]) / 'csv/tennis_booster_k1.csv').write_text('data')

            with patch.multiple(w, ROOT=root, DATA=data), patch.object(w, 'run', side_effect=fake_run) as run:
                w.main(['robot', 'tennis', '--no-video'])
            self.assertEqual((data / 'outputs/tennis/tennis.csv').read_text(), 'data')
            self.assertEqual(run.call_count, 2)
            with patch.multiple(w, ROOT=root, DATA=data), self.assertRaisesRegex(FileNotFoundError, 'workshop body'):
                w.main(['retarget', 'dance'])  # old name still works

    def test_convert_no_video_skips_pose_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / 'data/inputs/clip.mp4'
            video.parent.mkdir(parents=True)
            video.touch()
            with patch.multiple(w, ROOT=root, DATA=root / 'data'), patch.object(w, 'run') as run:
                w.main(['body', str(video), '--no-video'])
            self.assertEqual(len(run.call_args_list[1].args[0]), 4)

    def test_rejects_inputs_outside_data(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(w, 'DATA', Path(tmp) / 'data'):
            with self.assertRaises(ValueError):
                w.data_file('/etc/passwd')

    def test_stops_after_failed_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / 'data/input.mp4'
            video.parent.mkdir()
            video.touch()
            with patch.multiple(w, ROOT=root, DATA=video.parent), patch.object(w, 'run', side_effect=RuntimeError('GPU failed')) as run:
                with self.assertRaisesRegex(RuntimeError, 'GPU failed'):
                    w.process(video, 'test')
                self.assertEqual(run.call_count, 1)

    def test_native_retarget_uses_local_gmr_and_gvhmr_body_models(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / 'data'
            body = root / 'models'
            for path in (data / 'outputs/clip/gvhmr/hmr4d_results.pt', body / 'smplx/SMPLX_NEUTRAL.npz',
                         root / '.venv-gmr/bin/python'):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            calls = []

            def fake_run(command, **kwargs):
                cmd = list(map(str, command))
                calls.append(cmd)
                if cmd[1].endswith('batch_gmr_pkl_to_csv.py'):
                    (Path(cmd[-1]) / 'csv').mkdir()
                    (Path(cmd[-1]) / 'csv/clip_booster_k1.csv').write_text('data')

            with patch.multiple(w, NATIVE=True, ROOT=root, DATA=data, PIPELINE=root / '.pipeline',
                                PYTHONS={'gvhmr': root / '.venv/bin/python', 'gmr': root / '.venv-gmr/bin/python'}), \
                    patch.object(w, 'body_model_root', return_value=body), \
                    patch.object(w, 'run', side_effect=fake_run):
                w.retarget('clip', None, record=False)
            self.assertEqual(calls[0][0], str(root / '.venv-gmr/bin/python'))
            self.assertEqual(calls[0][1], str(root / '.pipeline/scripts/retarget_gvhmr.py'))
            self.assertEqual(calls[0][calls[0].index('--body-models') + 1], str(body))

    def test_videos_fall_back_to_cpu_opengl_only_when_gpu_rendering_fails(self):
        self.addCleanup(patch.stopall)
        patch.stopall()  # use the real video_rendering
        for probe_code, forced, expect_mesa in ((0, '', False), (1, '', True), (0, '1', True)):
            env = {'WORKSHOP_SOFTWARE_GL': forced}
            with self.subTest(probe=probe_code, forced=forced), patch.dict(w.os.environ, env, clear=True), \
                    patch.object(w.subprocess, 'run', return_value=unittest.mock.Mock(returncode=probe_code)):
                w.video_rendering()
                self.assertEqual(w.os.environ.get('__EGL_VENDOR_LIBRARY_FILENAMES') == w.MESA_EGL, expect_mesa)


if __name__ == '__main__':
    unittest.main()
