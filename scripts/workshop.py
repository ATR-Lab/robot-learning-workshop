"""Workshop CLI. All heavy libraries execute in their own Python environments."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path('/workspace')
DATA = ROOT / 'data'
PIPELINE = Path('/opt/pipeline')
BOOSTER = PIPELINE / 'external/booster'
TRAIN = BOOSTER / 'booster_train'
ASSETS = BOOSTER / 'booster_assets'
PYTHONS = {name: Path('/opt') / name / 'bin/python' for name in ('gvhmr', 'gmr', 'train')}


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


def data_file(value):
    path = Path(value).resolve()
    if not path.is_relative_to(DATA.resolve()):
        raise ValueError('Put the input inside this repository’s data/ directory.')
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def licensed():
    if os.environ.get('ACCEPT_EULA') != 'Y':
        raise RuntimeError('Review the licenses in README, then set ACCEPT_EULA=Y in .env.')


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
    # AppLauncher is initialized by the training/conversion commands, not here.
    run([PYTHONS['train'], '-c', 'from importlib.metadata import version; '
         'print("Isaac Sim", version("isaacsim")); print("Isaac Lab", version("isaaclab"))'])


def process(video, clip):
    video = data_file(video)
    inferred = re.sub(r'[^A-Za-z0-9_]', '_', video.stem)
    if not inferred or not inferred[0].isalpha():
        inferred = 'clip_' + inferred
    clip = clip_name(clip or inferred[:48])
    folder = DATA / 'outputs' / clip
    folder.mkdir(parents=True, exist_ok=True)
    staged = folder / 'input.mp4'
    run(['ffmpeg', '-y', '-i', video, '-an', '-vf', 'fps=30', '-c:v', 'libx264', staged],
        log=folder / 'logs/resample.log')
    prediction = folder / 'gvhmr/hmr4d_results.pt'
    prediction.parent.mkdir(parents=True, exist_ok=True)
    run([PYTHONS['gvhmr'], ROOT / 'scripts/recover.py', staged, prediction],
        log=folder / 'logs/gvhmr.log')
    retarget(prediction, clip)


def install_motion(clip):
    source = DATA / 'outputs' / clip / f'{clip}.npz'
    if not source.is_file():
        raise FileNotFoundError(f'{source}: run process or retarget first.')
    destination = ASSETS / 'motions/K1'
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination / source.name)


def retarget(prediction, clip):
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
    # The pinned Booster converter uses --output_name (newer revisions use --output_file).
    converter = TRAIN / 'scripts/csv_to_npz.py'
    text = converter.read_text()
    flag = '--output_file' if re.search(r'add_argument\(\s*[\'\"]--output_file[\'\"]', text) else '--output_name'
    run([PYTHONS['train'], converter, '--headless', '--input_file', csv,
         '--input_fps', '30', flag, folder / f'{clip}.npz', '--output_fps', '50'],
        cwd=TRAIN, log=folder / 'logs/npz.log')
    install_motion(clip)
    print(f'Ready: data/outputs/{clip}/. Train with: ./workshop train {clip}')


def train(clip, num_envs, max_iterations):
    install_motion(clip)
    folder = DATA / 'outputs' / clip
    run([PYTHONS['gmr'], PIPELINE / 'scripts/make_task.py', '--clip', clip,
         '--output-root', DATA / 'outputs', '--force'], log=folder / 'logs/task.log')
    task_root = TRAIN / 'source/booster_train/booster_train/tasks/manager_based/beyond_mimic/robots/k1'
    markers = [json.loads(p.read_text()) for p in task_root.rglob('.expressive_motion_generated.json')]
    tasks = [m for m in markers if m.get('clip') == clip and m.get('robot') == 'booster_k1']
    if len(tasks) != 1:
        raise RuntimeError(f'Expected one generated task for {clip}, found {len(tasks)}')
    logs = DATA / 'outputs/training'
    logs.mkdir(parents=True, exist_ok=True)
    target = TRAIN / 'logs'
    if not target.exists():
        target.symlink_to(logs, target_is_directory=True)
    elif not target.is_symlink() or target.resolve() != logs.resolve():
        raise RuntimeError(f'{target} must point to {logs}; refusing to hide existing logs.')
    run([PYTHONS['train'], TRAIN / 'scripts/rsl_rl/train.py', '--task', tasks[0]['gym_id'],
         '--headless', '--device', 'cuda:0', '--logger', 'tensorboard',
         '--num_envs', num_envs, '--max_iterations', max_iterations], cwd=TRAIN,
        log=folder / 'logs/train.log')


def positive(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError('Must be positive.')
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description='Robot Learning Workshop: video → K1 motion → training.')
    subs = parser.add_subparsers(dest='command', required=True)
    for name in ('setup', 'doctor', 'info', 'shell'):
        subs.add_parser(name)
    p = subs.add_parser('process', help='Process a stationary-camera video at 30 fps.')
    p.add_argument('video')
    p.add_argument('--clip', type=clip_name)
    p = subs.add_parser('retarget', help='Use an existing trusted 30 fps GVHMR result.')
    p.add_argument('prediction')
    p.add_argument('--clip', required=True, type=clip_name)
    p = subs.add_parser('train', help='Train a generated Booster K1 task.')
    p.add_argument('clip', type=clip_name)
    p.add_argument('--num-envs', type=positive, default=1024)
    p.add_argument('--max-iterations', type=positive, default=10000)
    args = parser.parse_args(argv)
    licensed()
    for directory in ('inputs', 'outputs', 'cache', 'home', 'body_models'):
        (DATA / directory).mkdir(parents=True, exist_ok=True)
    if args.command == 'setup':
        run(['/opt/gvhmr/bin/gvhmr', 'auth', 'smpl'])
        run(['/opt/gvhmr/bin/gvhmr', 'info'])
    elif args.command == 'doctor':
        doctor()
    elif args.command == 'info':
        run(['/opt/gvhmr/bin/gvhmr', 'info'])
    elif args.command == 'shell':
        os.execvp('/bin/bash', ['/bin/bash'])
    elif args.command == 'process':
        process(args.video, args.clip)
    elif args.command == 'retarget':
        retarget(args.prediction, args.clip)
    elif args.command == 'train':
        train(args.clip, args.num_envs, args.max_iterations)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        sys.exit(1)
