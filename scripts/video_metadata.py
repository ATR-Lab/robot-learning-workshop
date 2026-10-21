"""Count decoded video frames when PyAV has no container frame count."""
from functools import lru_cache
import json
from pathlib import Path
import subprocess


@lru_cache(maxsize=16)
def _probe(path, mtime_ns, size):
    result = subprocess.run([
        'ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_frames',
        '-show_entries', 'stream=nb_read_frames,width,height', '-of', 'json', path,
    ], check=True, text=True, capture_output=True)
    streams = json.loads(result.stdout).get('streams', [])
    if not streams:
        raise ValueError(f'No video stream: {path}')
    stream = streams[0]
    try:
        frames, width, height = (int(stream[k]) for k in ('nb_read_frames', 'width', 'height'))
    except (KeyError, ValueError) as exc:
        raise ValueError(f'Cannot count decoded video frames: {path}') from exc
    if min(frames, width, height) <= 0:
        raise ValueError(f'Video has no readable frames: {path}')
    return frames, width, height


def decoded_video_lwh(path):
    path = Path(path).resolve()
    stat = path.stat()
    return _probe(str(path), stat.st_mtime_ns, stat.st_size)


def install_frame_count_fallback(video_io):
    original = video_io.get_video_lwh

    def get_video_lwh(path):
        shape = original(path)
        if shape[0] > 0:
            return shape
        frames, width, height = decoded_video_lwh(path)
        if video_io.get_video_rotation(path) % 2:
            width, height = height, width
        return frames, width, height

    video_io.get_video_lwh = get_video_lwh
