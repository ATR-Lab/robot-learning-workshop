"""Prepare an mjlab K1 tracking ONNX using its embedded motion and metadata."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from urllib.request import urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = ROOT / 'configs/k1_mujoco.json'
MOTION_KEYS = ('joint_pos', 'joint_vel', 'body_pos_w', 'body_quat_w', 'body_lin_vel_w', 'body_ang_vel_w')
OBS_WIDTHS = dict(command=44, motion_anchor_pos_b=3, motion_anchor_ori_b=6,
                  base_lin_vel=3, base_ang_vel=3, joint_pos=22, joint_vel=22,
                  actions=22, projected_gravity=3)


def ensure_assets(directory=None):
    defaults = json.loads(DEFAULTS.read_text())
    folder = Path(directory or os.environ.get('WORKSHOP_K1_ASSETS', ROOT / 'data/assets/k1-mjlab'))
    folder.mkdir(parents=True, exist_ok=True)
    base = f"https://raw.githubusercontent.com/{defaults['repository']}/{defaults['commit']}/"
    marker = folder / 'source.json'
    reuse = marker.is_file() and json.loads(marker.read_text()).get('commit') == defaults['commit']

    def fetch(relative):
        target = folder / relative
        if reuse and target.is_file() and target.stat().st_size:
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        remote = str(Path(defaults['xml_path']).parent / relative) if relative != 'k1.xml' else defaults['xml_path']
        with urlopen(base + remote, timeout=60) as response:
            raw = response.read(16 * 1024 * 1024 + 1)
        if len(raw) > 16 * 1024 * 1024:
            raise ValueError('Robot asset exceeds 16 MiB.')
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as out:
            temp = Path(out.name)
            out.write(raw)
        temp.replace(target)

    fetch('k1.xml')
    tree = ET.parse(folder / 'k1.xml')
    meshes = []
    for mesh in tree.findall('./asset/mesh'):
        name = mesh.attrib['file']
        if Path(name).name != name:
            raise ValueError('Expected a mesh filename without directory components.')
        meshes.append('meshes/' + name)
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(fetch, meshes))
    (folder / 'source.json').write_text(json.dumps(defaults, indent=2) + '\n')
    print(f'K1 model ready: {folder}', flush=True)
    return folder


def read_export(path):
    import numpy as np
    import onnx
    from onnx import numpy_helper

    try:
        model = onnx.load(str(path), load_external_data=False)
    except Exception as exc:
        raise ValueError('Cannot read this ONNX file. Use the exported workshop policy.') from exc
    if any(x.data_location == onnx.TensorProto.EXTERNAL for x in model.graph.initializer):
        raise ValueError('Use a self-contained ONNX export; external tensor data is unsupported.')
    meta = {entry.key: entry.value for entry in model.metadata_props}
    required = ('joint_names', 'body_names', 'anchor_body_name', 'joint_stiffness',
                'joint_damping', 'default_joint_pos', 'action_scale', 'observation_names')
    missing = [key for key in required if key not in meta]
    if missing:
        raise ValueError('This ONNX has no complete mjlab tracking metadata. '
                         'For older exports keep config.json and motion.npz beside the ONNX.')
    names = meta['joint_names'].split(',')
    body_names = meta['body_names'].split(',')
    obs_names = meta['observation_names'].split(',')
    if len(names) != 22 or len(set(names)) != 22 or any(name not in OBS_WIDTHS for name in obs_names):
        raise ValueError('Unsupported joint count or observation layout; expected a K1 tracking export.')
    if meta['anchor_body_name'] not in body_names or len(set(body_names)) != len(body_names):
        raise ValueError('Reference body metadata is invalid or missing its anchor.')
    obs_dim = sum(OBS_WIDTHS[name] for name in obs_names)
    inputs = {x.name: x for x in model.graph.input}
    if set(inputs) != {'obs', 'time_step'} or inputs['obs'].type.tensor_type.shape.dim[-1].dim_value != obs_dim:
        raise ValueError('ONNX input dimensions do not match the tracking metadata.')
    histories = [float(x) for x in meta.get('observation_terms_history_length', ','.join(['0'] * len(obs_names))).split(',')]
    if len(histories) != len(obs_names) or any(x not in (0, 1) for x in histories):
        raise ValueError('Observation history longer than one frame is not supported by this player.')
    tensors = {x.name: x for x in model.graph.initializer}
    gathers = {n.output[0]: n.input[0] for n in model.graph.node if n.op_type == 'Gather'}
    if any(key not in gathers or gathers[key] not in tensors for key in MOTION_KEYS):
        raise ValueError('ONNX does not contain the expected embedded reference motion.')
    motion = {key: numpy_helper.to_array(tensors[gathers[key]]) for key in MOTION_KEYS}
    count = len(motion['joint_pos'])
    if not count or motion['joint_pos'].shape != (count, 22) or motion['joint_vel'].shape != (count, 22):
        raise ValueError('Embedded reference has invalid joint dimensions.')
    for key in MOTION_KEYS[2:]:
        width = 4 if key == 'body_quat_w' else 3
        if motion[key].shape != (count, len(body_names), width):
            raise ValueError(f'Invalid embedded motion array: {key}')
    if not all(np.isfinite(value).all() for value in motion.values()):
        raise ValueError('Embedded motion contains non-finite values.')
    return meta, names, body_names, obs_names, obs_dim, motion


def prepare_onnx(path, policies):
    import numpy as np

    path = Path(path).resolve()
    digest = hashlib.sha256(path.read_bytes() + DEFAULTS.read_bytes() + b'player-v1').hexdigest()
    defaults = json.loads(DEFAULTS.read_text())
    destination = Path(policies) / ('onnx_' + digest[:16])
    if (destination / 'config.json').is_file():
        return destination
    meta, names, body_names, obs_names, obs_dim, motion = read_export(path)

    def array(key):
        value = [float(v) for v in meta[key].split(',')]
        if len(value) != 22 or not np.isfinite(value).all():
            raise ValueError(f'Invalid joint metadata: {key}')
        return value

    motors = []
    for name in names:
        groups = [values for group, values in defaults['motors'].items() if group in name]
        if len(groups) != 1:
            raise ValueError(f'Unsupported K1 joint: {name}')
        motors.append(groups[0])
    cfg = dict(name=path.stem, kind='tracking', joint_names=names, obs_dim=obs_dim,
               observation_names=obs_names, onnx_time_step=True, control_mode='implicit_position',
               kp=array('joint_stiffness'), kd=array('joint_damping'),
               action_scale=array('action_scale'), default_joint_pos=array('default_joint_pos'),
               armature=[m[0] for m in motors], effort_limit=[m[1] for m in motors],
               velocity_limit=[m[2] for m in motors], knee_point_velocity=[m[3] for m in motors],
               policy_dt=defaults['policy_dt'], sim_dt=defaults['sim_dt'], decimation=defaults['decimation'],
               solver_iterations=defaults['solver_iterations'], default_delay=defaults['actuator_delay'],
               anchor_body=meta['anchor_body_name'], head_zero=False, start='reference',
               reanchor_reference_xy_yaw=False, hold_seconds_after_motion=0.0,
               onnx='policy.onnx', motion='motion.npz', robot_xml='robot/scene.xml',
               visual_group=2, collision_group=3)
    # Preserve the training observation transformations; unsupported layouts fail before simulation.
    count = len(obs_names)
    scales = meta.get('observation_terms_scale', ','.join(['1'] * count)).split(',')
    clips = meta.get('observation_terms_clip', ','.join(['-inf;inf'] * count)).split(',')
    if len(scales) != count or len(clips) != count:
        raise ValueError('Observation scale/clip metadata is misaligned.')
    cfg['observation_scales'] = [[float(v) for v in item.split(';')] for item in scales]
    cfg['observation_clips'] = [[float(v) for v in item.split(';')] for item in clips]
    for name, scale, bounds in zip(obs_names, cfg['observation_scales'], cfg['observation_clips']):
        if len(scale) not in (1, OBS_WIDTHS[name]) or not np.isfinite(scale).all():
            raise ValueError(f'Invalid observation scale: {name}')
        if len(bounds) != 2 or np.isnan(bounds).any() or bounds[0] > bounds[1]:
            raise ValueError(f'Invalid observation clipping bounds: {name}')
    # JSON remains portable even though unbounded clips are common in ONNX metadata.
    cfg['observation_clips'] = [[None if not np.isfinite(v) else v for v in pair] for pair in cfg['observation_clips']]
    assets = ensure_assets()
    Path(policies).mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.prepare-', dir=policies) as tmp:
        temp = Path(tmp)
        robot = temp / 'robot'
        shutil.copytree(assets, robot)
        tree = ET.parse(robot / 'k1.xml')
        root = tree.getroot()
        world = root.find('worldbody')
        ET.SubElement(world, 'geom', name='ground', type='plane', size='0 0 1',
                      rgba='0.25 0.3 0.35 1', friction='0 0 0', condim='3', solmix='1', group='0')
        for geom in root.findall('.//geom'):
            if geom.get('group') == '3':
                geom.set('contype', '1')
                geom.set('conaffinity', '1')
                geom.set('condim', '3')
                geom.set('solref', '0.01 1')
                geom.set('solmix', '0.001')
                geom.set('friction', '1 0.005 0.0001' if 'foot_collision' in geom.get('name', '') else '0.45 0.005 0.0001')
        actuator = ET.SubElement(root, 'actuator')
        for name, kp, kd, effort in zip(names, cfg['kp'], cfg['kd'], cfg['effort_limit']):
            ET.SubElement(actuator, 'position', name=name, joint=name, kp=str(kp), kv=str(kd),
                          forcelimited='true', forcerange=f'-{effort} {effort}')
        tree.write(robot / 'scene.xml')
        shutil.copy2(path, temp / 'policy.onnx')
        np.savez_compressed(temp / 'motion.npz', **motion, fps=np.array([1 / cfg['policy_dt']]),
                            joint_names=np.array(names), body_names=np.array(body_names))
        (temp / 'config.json').write_text(json.dumps(cfg, indent=2, allow_nan=False) + '\n')
        temp.rename(destination)
    print(f'Prepared ONNX automatically: {len(motion["joint_pos"])} reference frames, {obs_dim} observations.', flush=True)
    return destination


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--assets', action='store_true')
    p.add_argument('--directory')
    args = p.parse_args()
    if args.assets:
        ensure_assets(args.directory)
