import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('video_metadata', Path(__file__).parents[1] / 'scripts/video_metadata.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


class VideoMetadataTest(unittest.TestCase):
    def test_missing_metadata_uses_decoded_count_and_rotation(self):
        io = SimpleNamespace(get_video_lwh=lambda _: (0, 1920, 1080),
                             get_video_rotation=lambda _: 1)
        with patch.object(v, 'decoded_video_lwh', return_value=(216, 1920, 1080)):
            v.install_frame_count_fallback(io)
            self.assertEqual(io.get_video_lwh('dance.mp4'), (216, 1080, 1920))

    def test_valid_metadata_is_unchanged(self):
        io = SimpleNamespace(get_video_lwh=lambda _: (313, 812, 720))
        with patch.object(v, 'decoded_video_lwh') as probe:
            v.install_frame_count_fallback(io)
            self.assertEqual(io.get_video_lwh('clip.mp4'), (313, 812, 720))
            probe.assert_not_called()

    def test_empty_video_is_rejected(self):
        result = SimpleNamespace(stdout='{"streams":[{"nb_read_frames":"0","width":16,"height":16}]}')
        with patch.object(v.subprocess, 'run', return_value=result):
            with self.assertRaisesRegex(ValueError, 'no readable frames'):
                v._probe('empty.mp4', 0, 0)

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'Requires FFmpeg')
    def test_counts_decoded_frames_in_fragmented_mp4(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'fragmented.mp4'
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                            'color=size=16x16:rate=30', '-frames:v', '6',
                            '-c:v', 'libx264', '-movflags', 'frag_keyframe+empty_moov',
                            str(path)], check=True)
            self.assertEqual(v.decoded_video_lwh(path), (6, 16, 16))


if __name__ == '__main__':
    unittest.main()
