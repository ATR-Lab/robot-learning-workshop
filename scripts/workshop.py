"""Workshop CLI. All heavy libraries execute in their own Python environments."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

NATIVE = os.environ.get('WORKSHOP_NATIVE') == '1'
ROOT = Path(__file__).resolve().parents[1] if NATIVE else Path('/workspace')
DATA = ROOT / 'data'
PIPELINE = Path('/opt/pipeline')
PYTHONS = {name: Path('/opt') / name / 'bin/python' for name in ('gvhmr', 'gmr')}
if NATIVE:
    PYTHONS['gvhmr'] = ROOT / '.venv/bin/python'


def run(command, *, cwd=ROOT, log=None):
    command = [str(item) for item in command]
    print('+', subprocess.list2cmdline(command), flush=True)
    if log is None:
        subprocess.run(command, cwd=cwd, check=True)
        return
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open('w') as out:
        process = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True)
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end='', flush=True)
            out.write(line)
        if process.wait():
            raise RuntimeError(f'Stage failed. See {log}')


def clip_name(value):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,47}', value):
        raise argparse.ArgumentTypeError('Use 1–48 letters, digits or underscores; start with a letter.')
    return value


def data_file(value, *, allow_external=False):
    path = Path(value).resolve()
    if not allow_external and not path.is_relative_to(DATA.resolve()):
        raise ValueError('Put the input inside this repository’s data/ directory.')
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def doctor():
    run(['nvidia-smi'])
    snapshots = DATA / 'outputs/environment'
    snapshots.mkdir(parents=True, exist_ok=True)
    for name, python in PYTHONS.items():
        run([python, '-c', 'import torch; assert torch.cuda.is_available(), "CUDA is unavailable"; '
             'print(torch.__version__, torch.cuda.get_device_name(0)); '
             'x=torch.ones(16, device="cuda"); print((x*x).sum().item())'])
        run([python, '-m', 'pip', 'check'])
        with (snapshots / f'{name}.txt').open('w') as out:
            subprocess.run([str(python), '-m', 'pip', 'freeze'], stdout=out, check=True)
    run([PYTHONS['gmr'], '-c', 'import general_motion_retargeting, mujoco; print("GMR imports OK")'])


def convert(video, clip):
    video = data_file(video, allow_external=NATIVE)
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        raise RuntimeError('FFmpeg/ffprobe are missing. Rerun ./setup.sh.')
    inferred = re.sub(r'[^A-Za-z0-9_]', '_', video.stem)
    if not inferred or not inferred[0].isalpha():
        inferred = 'clip_' + inferred
    clip = clip_name(clip or inferred[:48])
    folder = DATA / 'outputs' / clip
    folder.mkdir(parents=True, exist_ok=True)
    staged = folder / 'input.mp4'
    if video == staged.resolve():
        raise ValueError('Use the original video as input, not the generated outputs/<clip>/input.mp4.')
    run(['ffmpeg', '-nostdin', '-y', '-v', 'error', '-xerror', '-i', video,
         '-map', '0:v:0', '-an', '-vf', 'fps=30', '-c:v', 'libx264',
         '-pix_fmt', 'yuv420p', '-movflags', '+faststart', staged],
        log=folder / 'logs/resample.log')
    prediction = folder / 'gvhmr/hmr4d_results.pt'
    prediction.parent.mkdir(parents=True, exist_ok=True)
    run([PYTHONS['gvhmr'], ROOT / 'scripts/recover.py', staged, prediction],
        log=folder / 'logs/gvhmr.log')
    print(f'Human motion: data/outputs/{clip}/gvhmr/hmr4d_results.pt')
    return prediction, clip


def process(video, clip):
    if NATIVE:
        raise RuntimeError('On Mac use ./workshop convert <video>; GMR → CSV runs on the NVIDIA/Linux server.')
    prediction, clip = convert(video, clip)
    retarget(prediction, clip)


def retarget(prediction, clip):
    if NATIVE:
        raise RuntimeError('GMR → CSV requires the NVIDIA/Linux workshop server. '
                           'Copy the .pt there and run ./workshop retarget <path-to-pt> --clip ' + clip)
    prediction = data_file(prediction)
    folder = DATA / 'outputs' / clip
    robot_data = folder / 'robot_data/booster_k1'
    robot_data.mkdir(parents=True, exist_ok=True)
    body = DATA / 'body_models/smplx/SMPLX_NEUTRAL.npz'
    if not body.is_file():
        raise FileNotFoundError(f'{body}: run ./workshop setup first.')
    motion = robot_data / f'{clip}_booster_k1.pkl'
    run([PYTHONS['gmr'], PIPELINE / 'scripts/retarget_gvhmr.py',
         '--gvhmr-result', prediction, '--robot', 'booster_k1', '--output', motion,
         '--body-models', DATA / 'body_models', '--fps', '30', '--clip-name', clip],
        log=folder / 'logs/retarget.log')
    run([PYTHONS['gmr'], PIPELINE / 'external/GMR/scripts/batch_gmr_pkl_to_csv.py',
         '--folder', robot_data], log=folder / 'logs/csv.log')
    csv = robot_data / 'csv' / f'{clip}_booster_k1.csv'
    if not csv.is_file():
        raise FileNotFoundError(f'GMR produced no CSV: {csv}')
    shutil.copy2(csv, folder / f'{clip}.csv')
    print(f'Ready: data/outputs/{clip}/. Send this folder to the workshop server for training.')



def main(argv=None):
    parser = argparse.ArgumentParser(description='Robot Learning Workshop: video → human motion → K1 motion export.')
    subs = parser.add_subparsers(dest='command', required=True)
    for name in ('setup', 'doctor', 'info', 'shell'):
        subs.add_parser(name)
    for name, help_text in (
        ('convert', 'GVHMR only: video → human motion at 30 fps.'),
        ('process', 'GVHMR + GMR: video → K1 motion at 30 fps.'),
    ):
        p = subs.add_parser(name, help=help_text)
        p.add_argument('video')
        p.add_argument('--clip', type=clip_name)
    p = subs.add_parser('retarget', help='Use an existing trusted 30 fps GVHMR result.')
    p.add_argument('prediction')
    p.add_argument('--clip', required=True, type=clip_name)
    args = parser.parse_args(argv)
    for directory in ('inputs', 'outputs', 'cache', 'home', 'body_models'):
        (DATA / directory).mkdir(parents=True, exist_ok=True)
    if args.command == 'setup':
        run(['/opt/gvhmr/bin/gvhmr', 'auth', 'smpl'])
        run(['/opt/gvhmr/bin/gvhmr', 'info'])
    elif args.command == 'doctor':
        if NATIVE:
            run([PYTHONS['gvhmr'], '-m', 'pip', 'check'])
            run([ROOT / '.venv/bin/gvhmr', 'info'])
            return
        doctor()
    elif args.command == 'info':
        run([PYTHONS['gvhmr'].parent / 'gvhmr', 'info'])
    elif args.command == 'shell':
        os.execvp('/bin/bash', ['/bin/bash'])
    elif args.command == 'convert':
        convert(args.video, args.clip)
    elif args.command == 'process':
        process(args.video, args.clip)
    elif args.command == 'retarget':
        retarget(args.prediction, args.clip)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        sys.exit(1)
