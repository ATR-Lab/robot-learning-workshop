"""Workshop CLI. All heavy libraries execute in their own Python environments."""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request

NATIVE = os.environ.get('WORKSHOP_NATIVE') == '1'
ROOT = Path(__file__).resolve().parents[1] if NATIVE else Path('/workspace')
DATA = ROOT / 'data'
PIPELINE = Path('/opt/pipeline')
PYTHONS = {name: Path('/opt') / name / 'bin/python' for name in ('gvhmr', 'gmr')}
if NATIVE:
    PYTHONS['gvhmr'] = ROOT / '.venv/bin/python'
SAMPLE = ('https://raw.githubusercontent.com/zju3dv/GVHMR/ee960bb6e2ea2d381aa97f08e9b71ef320b624b1/'
          'docs/example_video/tennis.mp4')


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
        shown = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        raise FileNotFoundError(f'No file at {shown}. Copy your video there first, or get the sample:\n'
                                f'  curl -fL {SAMPLE} -o data/inputs/tennis.mp4')
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


def gvhmr(*args):
    run([PYTHONS['gvhmr'].parent / 'gvhmr', *args])


def info():
    gvhmr('info')
    # GVHMR's own hint says `gvhmr download`, which only exists inside the environment.
    print('\nWorkshop needs: body_models/smplx + smpl and the demo checkpoints (gvhmr, hmr2, vitpose, yolo).\n'
          'Missing checkpoints: ./workshop download  ·  DPVO and the data packs are not needed.', flush=True)


def check():
    try:
        run([PYTHONS['gvhmr'], ROOT / 'scripts/ready.py'])
    except subprocess.CalledProcessError:
        raise RuntimeError('Not ready yet: fix the ✗ items above, then rerun ./setup.sh.') from None


def download():
    """Everything after login: body models, checkpoints, the sample video, then a short readiness check."""
    run([PYTHONS['gvhmr'], ROOT / 'scripts/body_models.py'])
    gvhmr('download', 'demo')
    sample = DATA / 'inputs/tennis.mp4'
    if not sample.is_file():
        print('Downloading sample video → data/inputs/tennis.mp4', flush=True)
        partial = sample.with_suffix('.part')
        urllib.request.urlretrieve(SAMPLE, partial)
        partial.replace(sample)
    check()


def convert(video, clip, record=True):
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
    with video.open('rb') as source:
        digest = hashlib.file_digest(source, 'sha256').hexdigest()
    signature = folder / 'source.sha256'
    if not signature.exists() or signature.read_text().strip() != digest:
        artifacts = [folder / name for name in ('gvhmr', 'robot_data', f'{clip}.csv', 'input.mp4', 'logs',
                                                f'{clip}_pose.mp4', f'{clip}_k1.mp4', f'{clip}_compare.mp4')]
        if any(path.exists() for path in artifacts):
            backup = Path(tempfile.mkdtemp(prefix='previous-', dir=folder))
            for path in artifacts:
                if path.exists():
                    shutil.move(path, backup / path.name)
            print(f'Input changed; previous results saved in {backup}', flush=True)
    run(['ffmpeg', '-nostdin', '-y', '-v', 'error', '-xerror', '-i', video,
         '-map', '0:v:0', '-an', '-vf', 'fps=30', '-c:v', 'libx264',
         '-pix_fmt', 'yuv420p', '-movflags', '+faststart', staged],
        log=folder / 'logs/resample.log')
    signature.write_text(digest + '\n')
    prediction = folder / 'gvhmr/hmr4d_results.pt'
    prediction.parent.mkdir(parents=True, exist_ok=True)
    recover = [PYTHONS['gvhmr'], ROOT / 'scripts/recover.py', staged, prediction]
    if record:
        recover.append(folder / f'{clip}_pose.mp4')
    run(recover, log=folder / 'logs/gvhmr.log')
    print(f'Body pose: data/outputs/{clip}/gvhmr/hmr4d_results.pt'
          + (f' + {clip}_pose.mp4' if record else '')
          + f'. Next: ./workshop retarget {clip}')
    return prediction, clip


def process(video, clip, record=True):
    if NATIVE:
        raise RuntimeError('On Mac use ./workshop convert <video>; GMR → CSV runs on the NVIDIA/Linux server.')
    prediction, clip = convert(video, clip, record)
    retarget(prediction, clip, record)


def pose_result(value, clip):
    """A clip name (tennis) means data/outputs/tennis/gvhmr/hmr4d_results.pt."""
    path = Path(value)
    if path.suffix != '.pt' and len(path.parts) == 1:
        clip = clip or clip_name(value)
        path = DATA / 'outputs' / value / 'gvhmr/hmr4d_results.pt'
        if not path.is_file():
            raise FileNotFoundError(f'No body pose for {value!r}. Run first: ./workshop convert data/inputs/{value}.mp4')
    elif clip is None:
        if path.parent.name != 'gvhmr':
            raise ValueError('Add --clip NAME to choose the output folder for this .pt file.')
        clip = clip_name(path.resolve().parent.parent.name)
    return data_file(path), clip


def retarget(prediction, clip, record=True):
    prediction, clip = pose_result(prediction, clip)
    if NATIVE:
        raise RuntimeError('GMR → CSV requires the NVIDIA/Linux workshop server. '
                           f'Copy the .pt there and run ./workshop retarget <path-to-pt> --clip {clip}')
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
    made = [f'{clip}.csv']
    if record:
        render = [PYTHONS['gmr'], ROOT / 'scripts/render_motion.py', motion, folder / f'{clip}_k1.mp4']
        made.append(f'{clip}_k1.mp4')
        if (folder / 'input.mp4').is_file():
            render += ['--beside', folder / 'input.mp4', '--compare-output', folder / f'{clip}_compare.mp4']
            made.append(f'{clip}_compare.mp4')
        run(render, log=folder / 'logs/render.log')
    print(f"Ready: data/outputs/{clip}/ — {', '.join(made)}. Send this folder to the workshop server for training.")



def main(argv=None):
    parser = argparse.ArgumentParser(description='Robot Learning Workshop: video → human motion → K1 motion export.')
    subs = parser.add_subparsers(dest='command', required=True)
    for name, help_text in (
        ('setup', 'Same as auth.'),
        ('auth', 'SMPL-X + SMPL logins, then everything download does.'),
        ('download', 'Body models (saved logins), checkpoints (about 6 GB), sample video, then check.'),
        ('check', 'Short ✓/✗ list of the models conversion needs.'),
        ('doctor', 'Check GPU and Python environments.'),
        ('info', 'Full GVHMR status (DPVO and data packs are not needed).'),
        ('shell', 'Open a shell inside the workshop container.'),
    ):
        subs.add_parser(name, help=help_text)
    for name, help_text in (
        ('convert', 'Step 1 · GVHMR: video → body pose (+ <clip>_pose.mp4).'),
        ('process', 'Steps 1 + 2: video → body pose → K1 motion.'),
    ):
        p = subs.add_parser(name, help=help_text)
        p.add_argument('video')
        p.add_argument('--clip', type=clip_name)
        p.add_argument('--no-video', dest='record', action='store_false', help='skip the result videos')
    p = subs.add_parser('retarget', help='Step 2 · GMR: body pose → K1 CSV (+ <clip>_k1.mp4, <clip>_compare.mp4).')
    p.add_argument('prediction', help='clip name from step 1 (e.g. tennis) or a trusted 30 fps hmr4d_results.pt')
    p.add_argument('--clip', type=clip_name)
    p.add_argument('--no-video', dest='record', action='store_false', help='skip the result videos')
    args = parser.parse_args(argv)
    for directory in ('inputs', 'outputs', 'cache', 'home', 'body_models'):
        (DATA / directory).mkdir(parents=True, exist_ok=True)
    if args.command in ('setup', 'auth'):
        gvhmr('auth', 'smpl')
        download()
    elif args.command == 'download':
        download()
    elif args.command == 'check':
        check()
    elif args.command == 'doctor':
        if NATIVE:
            run([PYTHONS['gvhmr'], '-m', 'pip', 'check'])
            gvhmr('info')
            return
        doctor()
    elif args.command == 'info':
        info()
    elif args.command == 'shell':
        os.execvp('/bin/bash', ['/bin/bash'])
    elif args.command == 'convert':
        convert(args.video, args.clip, args.record)
    elif args.command == 'process':
        process(args.video, args.clip, args.record)
    elif args.command == 'retarget':
        retarget(args.prediction, args.clip, args.record)

if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        sys.exit(1)
