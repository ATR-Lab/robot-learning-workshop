"""Exercise stage handoffs without installing GPU software on the test host."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('workshop', Path(__file__).parents[1] / 'scripts/workshop.py')
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


class PipelineTest(unittest.TestCase):
    def test_stage_handoffs_and_persistent_training(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data, pipeline = root / 'data', root / 'pipeline'
            booster = pipeline / 'external/booster'
            train, assets = booster / 'booster_train', booster / 'booster_assets'
            body = data / 'body_models/smplx/SMPLX_NEUTRAL.npz'
            body.parent.mkdir(parents=True)
            body.touch()
            video = data / 'inputs/123-test.mp4'
            video.parent.mkdir()
            video.touch()
            converter = train / 'scripts/csv_to_npz.py'
            converter.parent.mkdir(parents=True)
            converter.write_text('parser.add_argument("--output_file")')
            calls = []

            def fake_run(command, **kwargs):
                cmd = list(map(str, command))
                calls.append(cmd)
                if cmd[0] == 'ffmpeg':
                    Path(cmd[-1]).touch()
                elif cmd[1].endswith('recover.py'):
                    Path(cmd[-1]).touch()
                elif cmd[1].endswith('retarget_gvhmr.py'):
                    Path(cmd[cmd.index('--output') + 1]).touch()
                elif cmd[1].endswith('batch_gmr_pkl_to_csv.py'):
                    folder = Path(cmd[-1]) / 'csv'
                    folder.mkdir()
                    (folder / 'clip_123_test_booster_k1.csv').write_text('data')
                elif cmd[1].endswith('csv_to_npz.py'):
                    Path(cmd[cmd.index('--output_file') + 1]).write_text('npz')
                elif cmd[1].endswith('make_task.py'):
                    marker = train / 'source/booster_train/booster_train/tasks/manager_based/beyond_mimic/robots/k1/clip_123_test/.expressive_motion_generated.json'
                    marker.parent.mkdir(parents=True)
                    marker.write_text(json.dumps({'clip': 'clip_123_test', 'robot': 'booster_k1', 'gym_id': 'Booster-K1-Test-v0'}))

            with patch.multiple(w, ROOT=root, DATA=data, PIPELINE=pipeline, BOOSTER=booster,
                                TRAIN=train, ASSETS=assets), patch.object(w, 'run', side_effect=fake_run):
                w.process(video, None)
                w.train('clip_123_test', 32, 2)
            self.assertTrue((assets / 'motions/K1/clip_123_test.npz').is_file())
            self.assertEqual((train / 'logs').resolve(), (data / 'outputs/training').resolve())
            self.assertIn('Booster-K1-Test-v0', calls[-1])
            self.assertIn('tensorboard', calls[-1])
            self.assertEqual(calls[-1][-1], '2')

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


if __name__ == '__main__':
    unittest.main()
