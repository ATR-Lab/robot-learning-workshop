"""Play a K1 reference motion (CSV) in MuJoCo: no policy and no physics, the robot is posed frame by frame.

  ./workshop motion examples/dances/gangnam_style             # Mac window, Docker browser
  ./workshop motion data/outputs/tennis/tennis.csv            # any result of ./workshop robot
  ./workshop motion examples/dances/lerobot --record data/lerobot.mp4

CSV rows: root position x y z (m), root quaternion x y z w, 22 joint angles (rad) in K1 order, at --fps.
Viewer keys: Enter = restart, Space = pause.
"""
import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('csv', help='K1 motion CSV (or a folder containing one)')
mode = p.add_mutually_exclusive_group()
mode.add_argument('--record', help='write an mp4 instead of opening the viewer (requires ffmpeg)')
mode.add_argument('--web', action='store_true', help='browser viewer; no display or GPU required')
p.add_argument('--fps', type=float, default=30.0, help='frame rate of the CSV (workshop CSVs are 30)')
p.add_argument('--host', default='0.0.0.0' if os.environ.get('SIM_DOCKER') else '127.0.0.1')
p.add_argument('--port', type=int, default=8080)
p.add_argument('--width', type=int, default=960)
p.add_argument('--height', type=int, default=720)
args = p.parse_args()

source = Path(args.csv)
if source.is_dir():
    found = sorted(source.glob('*.csv'))
    if len(found) != 1:
        p.error(f'{source} must contain exactly one .csv')
    source = found[0]
motion = np.loadtxt(source, delimiter=',', ndmin=2)
if motion.shape[1] != 29:
    p.error(f'{source}: expected 29 columns (3 position, 4 quaternion, 22 joints), found {motion.shape[1]}')
qpos = np.column_stack((motion[:, :3], motion[:, [6, 3, 4, 5]], motion[:, 7:]))  # quaternion xyzw → wxyz
name = source.stem
dt = 1 / args.fps

m = mujoco.MjModel.from_xml_path(str(ROOT / 'examples/cartwheel/robot/K1_serial.xml'))
m.geom_group[m.geom('ground').id] = 2  # hide collision geoms (group 0), keep the floor
m.vis.global_.offwidth = max(m.vis.global_.offwidth, args.width)
m.vis.global_.offheight = max(m.vis.global_.offheight, args.height)
d = mujoco.MjData(m)
show = mujoco.MjvOption()
show.geomgroup[0] = 0


def pose(frame):
    d.qpos[:] = qpos[frame]
    mujoco.mj_forward(m, d)


# Camera in front of the robot: its average heading over the first second.
w, x, y, z = qpos[:max(1, int(args.fps)), 3:7].T
yaw = np.arctan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
front = np.arctan2(np.sin(yaw).mean(), np.cos(yaw).mean())
azimuth = np.degrees(front) + 180.0
print(f'{name}: {len(qpos)} frames, {len(qpos) * dt:.1f} s at {args.fps:g} fps', flush=True)

if args.record:
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        p.error('video recording requires ffmpeg on PATH')
    out = Path(args.record)
    out.parent.mkdir(parents=True, exist_ok=True)
    renderer = mujoco.Renderer(m, args.height, args.width)
    cam = mujoco.MjvCamera()
    cam.distance, cam.elevation, cam.azimuth = 2.6, -10.0, azimuth
    encoder = subprocess.Popen([ffmpeg, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                                '-s', f'{args.width}x{args.height}', '-r', f'{args.fps:g}', '-i', '-',
                                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(out)],
                               stdin=subprocess.PIPE)
    look = qpos[0, :3].copy()
    for frame in range(len(qpos)):
        pose(frame)
        look[:2] = 0.9 * look[:2] + 0.1 * qpos[frame, :2]  # smooth follow of the trunk
        cam.lookat[:] = (look[0], look[1], 0.45)
        renderer.update_scene(d, camera=cam, scene_option=show)
        encoder.stdin.write(renderer.render().tobytes())
    encoder.stdin.close()
    renderer.close()
    if encoder.wait():
        sys.exit('ffmpeg failed to encode the video')
    print('wrote', out)
    sys.exit(0)

if args.web:
    import viser
    from mjviser import ViserMujocoScene

    server = viser.ViserServer(host=args.host, port=args.port)
    server.scene.set_up_direction('+z')
    scene = ViserMujocoScene(server, m, num_envs=1)
    scene.camera_tracking_enabled = False
    scene.geom_groups_visible = [bool(v) for v in show.geomgroup]
    server.gui.add_markdown(f'## Booster K1 · {name}\nReference motion (no policy). Press Play.')
    play = server.gui.add_checkbox('Play', initial_value=False)
    loop = server.gui.add_checkbox('Loop', initial_value=True)
    restart = server.gui.add_button('Restart')
    state = {'frame': 0}

    @restart.on_click
    def _(_):
        state['frame'] = 0

    @server.on_client_connect
    def _(client):
        client.camera.position = (qpos[0, 0] + 3.0 * np.cos(front), qpos[0, 1] + 3.0 * np.sin(front), 1.5)
        client.camera.look_at = (qpos[0, 0], qpos[0, 1], 0.5)

    pose(0)
    scene.update_from_mjdata(d)
    public_port = os.environ.get('SIM_PUBLIC_PORT', str(args.port))
    print(f'Open http://localhost:{public_port} and press Play. Ctrl+C stops the server.', flush=True)
    try:
        while True:
            started = time.perf_counter()
            if play.value:
                state['frame'] += 1
                if state['frame'] >= len(qpos):
                    state['frame'] = 0 if loop.value else len(qpos) - 1
                    play.value = loop.value
            pose(state['frame'])
            scene.update_from_mjdata(d)
            time.sleep(max(0.001, dt - (time.perf_counter() - started)))
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
    sys.exit(0)

# ---------- interactive window (needs mjpython on macOS) ----------
import mujoco.viewer  # noqa: E402

state = dict(frame=0, paused=False)


def key(k):
    if k in (257, 335, 259):  # Enter, keypad Enter, Backspace
        state['frame'] = 0
    elif k == 32:  # Space
        state['paused'] = not state['paused']


print('Enter = restart, Space = pause. The motion loops.', flush=True)
pose(0)
with mujoco.viewer.launch_passive(m, d, key_callback=key) as viewer:
    viewer.opt.geomgroup[:] = show.geomgroup
    viewer.cam.distance, viewer.cam.elevation, viewer.cam.azimuth = 2.8, -12.0, azimuth
    viewer.cam.lookat[:] = (qpos[0, 0], qpos[0, 1], 0.45)
    while viewer.is_running():
        started = time.perf_counter()
        with viewer.lock():
            pose(state['frame'])
            if not state['paused']:
                state['frame'] = (state['frame'] + 1) % len(qpos)
        viewer.sync()
        time.sleep(max(0.0, dt - (time.perf_counter() - started)))
