"""Import complete K1 ONNX tracking bundles and launch the workshop MuJoCo player."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from urllib.parse import urlparse
from urllib.request import urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]
POLICIES = ROOT / 'data/policies'
MAX_BYTES = 512 * 1024 * 1024


def bundle_name(value):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,47}', value):
        raise argparse.ArgumentTypeError('Use 1–48 letters, digits, underscores or hyphens.')
    return value


def contained(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f'Bundle path escapes its folder: {relative}')
    return path


def find_config(root):
    matches = []
    for path in sorted(root.rglob('config.json')):
        cfg = json.loads(path.read_text())
        if all(key in cfg for key in ('onnx', 'motion', 'robot_xml', 'obs_dim', 'joint_names')):
            matches.append(path)
    if len(matches) != 1:
        raise ValueError('Expected one K1 tracking config.json with ONNX, reference motion and robot XML. '
                         'A raw .pt/.pth/.onnx file is insufficient; ask for the complete export bundle.')
    return matches[0]


def validate_bundle(root):
    config = find_config(root)
    cfg = json.loads(config.read_text())
    if cfg['obs_dim'] not in (119, 125) or len(cfg['joint_names']) != 22:
        raise ValueError('This player supports K1 tracking exports with 22 joints and 119/125 observations.')
    for key in ('onnx', 'motion', 'robot_xml'):
        path = contained(root, config.parent.relative_to(root) / cfg[key])
        if not path.is_file():
            raise FileNotFoundError(f'Missing {key}: {path}')
    return config


def unpack(archive, destination):
    with zipfile.ZipFile(archive) as z:
        if len(z.infolist()) > 10000 or sum(i.file_size for i in z.infolist()) > MAX_BYTES:
            raise ValueError('Policy ZIP exceeds the 512 MiB / 10,000 file limit.')
        for item in z.infolist():
            # Reject platform-dependent separators, traversal and symlinks.
            name = PurePosixPath(item.filename)
            if '\\' in item.filename or ':' in item.filename or name.is_absolute() or '..' in name.parts:
                raise ValueError(f'Unsafe ZIP path: {item.filename}')
            if stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError(f'Symlinks are not supported: {item.filename}')
            contained(destination, item.filename)
        z.extractall(destination)


def download(url, target):
    with urlopen(url, timeout=60) as response, target.open('wb') as out:
        if urlparse(response.url).scheme not in ('https', 'http'):
            raise ValueError('Policy URL must use HTTP or HTTPS.')
        total = 0
        while chunk := response.read(1024 * 1024):
            total += len(chunk)
            if total > MAX_BYTES:
                raise ValueError('Policy download exceeds 512 MiB.')
            out.write(chunk)


def is_url(source):
    return urlparse(source).scheme in ('http', 'https')


def import_bundle(source, name):
    POLICIES.mkdir(parents=True, exist_ok=True)
    destination = POLICIES / bundle_name(name)
    if destination.exists():
        raise FileExistsError(f'{destination} already exists. Choose a new --name.')
    with tempfile.TemporaryDirectory(prefix='.import-', dir=POLICIES) as tmp:
        temp = Path(tmp)
        payload = temp / 'bundle'
        payload.mkdir()
        if is_url(source):
            archive = temp / 'download.zip'
            print('Downloading policy bundle…', flush=True)
            download(source, archive)
            unpack(archive, payload)
        else:
            path = Path(source).expanduser().resolve()
            if path.is_dir():
                for item in path.rglob('*'):
                    if item.is_symlink():
                        raise ValueError(f'Symlinks are not supported in a bundle: {item}')
                shutil.copytree(path, payload, dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns('.venv*', '__pycache__', '.DS_Store'))
            elif path.is_file() and zipfile.is_zipfile(path):
                unpack(path, payload)
            else:
                raise ValueError('Use a complete policy folder or ZIP, or a direct HTTP(S) ZIP link.')
        validate_bundle(payload)
        payload.rename(destination)
    print(f'Imported {name}. Launch: ./sim play {name}')
    return destination


def resolve_source(source):
    if is_url(source):
        name = 'url_' + hashlib.sha256(source.encode()).hexdigest()[:16]
        cached = POLICIES / name
        return cached if cached.exists() else import_bundle(source, name)
    path = Path(source).expanduser()
    if path.is_dir():
        return path.resolve()
    if path.is_file() and zipfile.is_zipfile(path):
        name = 'zip_' + hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        cached = POLICIES / name
        return cached if cached.exists() else import_bundle(source, name)
    cached = POLICIES / bundle_name(source)
    if cached.is_dir():
        return cached
    raise FileNotFoundError(f'Policy {source!r} was not found. Use ./sim import SOURCE --name NAME.')


def pack_bundle(source, output):
    root = resolve_source(source).resolve()
    config = validate_bundle(root)
    cfg = json.loads(config.read_text())
    output = Path(output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    # Export data only. Keep relative paths so the robot XML still finds its meshes.
    files = {config}
    for key in ('onnx', 'motion'):
        files.add((config.parent / cfg[key]).resolve())
    robot = (config.parent / cfg['robot_xml']).resolve().parent
    files.update(p for p in robot.rglob('*') if p.is_file())
    for path in files:
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError(f'Asset is outside the bundle or is a symlink: {path}')
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for path in sorted(files):
            z.write(path, path.relative_to(root))
    print(f'Created {output}. Share this ZIP or its direct download URL with participants.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    imp = commands.add_parser('import', help='Import a policy folder, ZIP or direct ZIP URL.')
    imp.add_argument('source')
    imp.add_argument('--name', required=True, type=bundle_name)
    pack = commands.add_parser('pack', help='Make a data-only ZIP for participants.')
    pack.add_argument('source')
    pack.add_argument('--output', required=True)
    play = commands.add_parser('play', help='Run a policy name, folder or ZIP URL in MuJoCo.',
                               epilog='Player flags: --web, --check, --json FILE, --record FILE, --no-ghost.')
    play.add_argument('source')
    play.add_argument('player_args', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.command == 'import':
        import_bundle(args.source, args.name)
    elif args.command == 'pack':
        pack_bundle(args.source, args.output)
    else:
        folder = resolve_source(args.source)
        config = validate_bundle(folder)
        flags = args.player_args
        if os.environ.get('SIM_DOCKER') and not any(f in flags for f in ('--check', '--record')):
            flags = [*flags, '--web']
        python = sys.executable
        if sys.platform == 'darwin' and not any(f in flags for f in ('--check', '--record', '--web', '--help')):
            python = str(Path(sys.executable).parent / 'mjpython')
        subprocess.run([python, str(ROOT / 'scripts/play_mujoco.py'), '--policy', str(config.parent), *flags],
                       check=True)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
    except (OSError, ValueError, zipfile.BadZipFile, subprocess.CalledProcessError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        sys.exit(exc.returncode if isinstance(exc, subprocess.CalledProcessError) else 1)
