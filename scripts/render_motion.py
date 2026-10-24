"""Run in the GMR environment: render a GMR robot motion (.pkl) to mp4, optionally beside the input video."""
import argparse
import pickle
import subprocess

import mujoco as mj
import numpy as np
from general_motion_retargeting.params import ROBOT_XML_DICT

parser = argparse.ArgumentParser()
parser.add_argument('motion')
parser.add_argument('output')
parser.add_argument('--beside', help='video to place on the left in a second, side-by-side mp4')
parser.add_argument('--compare-output')
parser.add_argument('--size', type=int, default=480, help='video height; width is 4:3')
parser.add_argument('--camera-from', help='GVHMR hmr4d_results.pt: film from the original camera direction')
args = parser.parse_args()

with open(args.motion, 'rb') as f:
    motion = pickle.load(f)
fps = float(motion['fps'])
root_pos = np.asarray(motion['root_pos'])
root_rot = np.asarray(motion['root_rot'])[:, [3, 0, 1, 2]]  # stored xyzw; MuJoCo wants wxyz
dof_pos = np.asarray(motion['dof_pos'])

model = mj.MjModel.from_xml_path(str(ROBOT_XML_DICT[motion.get('robot', 'booster_k1')]))
data = mj.MjData(model)
height, width = args.size, args.size * 4 // 3
model.vis.global_.offwidth = max(model.vis.global_.offwidth, width)
model.vis.global_.offheight = max(model.vis.global_.offheight, height)
renderer = mj.Renderer(model, height=height, width=width)
if args.camera_from:
    # Same viewpoint as the video: GVHMR's camera optical axis = global ∘ in-camera⁻¹ orientation.
    import torch
    from scipy.spatial.transform import Rotation as R
    pose = torch.load(args.camera_from, map_location='cpu', weights_only=False)
    world, incam = (R.from_rotvec(pose[key]['global_orient'].numpy())
                    for key in ('smpl_params_global', 'smpl_params_incam'))
    forward = (world * incam.inv()).apply([0, 0, 1]).mean(axis=0)  # y-up, as GVHMR stores it
    azimuth = np.degrees(np.arctan2(-forward[2], forward[0]))       # retargeting maps y-up (x, y, z) → z-up (x, -z, y)
else:
    # No video camera known: look at the robot's front, using its heading over the first second.
    w, x, y, z = root_rot[:max(1, int(fps))].T
    yaw = np.arctan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
    azimuth = np.degrees(np.arctan2(np.sin(yaw).mean(), np.cos(yaw).mean())) + 180.0
camera = mj.MjvCamera()
camera.distance, camera.elevation, camera.azimuth = 2.5, -10.0, azimuth

encoder = subprocess.Popen(
    ['ffmpeg', '-nostdin', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
     '-s', f'{width}x{height}', '-r', str(fps), '-i', '-',
     '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', args.output],
    stdin=subprocess.PIPE)
for frame in range(len(root_pos)):
    data.qpos[:3], data.qpos[3:7], data.qpos[7:] = root_pos[frame], root_rot[frame], dof_pos[frame]
    mj.mj_forward(model, data)
    camera.lookat[:] = (root_pos[frame][0], root_pos[frame][1], 0.5)
    renderer.update_scene(data, camera=camera)
    encoder.stdin.write(renderer.render().tobytes())
encoder.stdin.close()
renderer.close()
if encoder.wait():
    raise SystemExit('ffmpeg failed while writing ' + args.output)
print(f'Robot video: {args.output} ({len(root_pos)} frames at {fps:g} fps)')

if args.beside:
    subprocess.run(['ffmpeg', '-nostdin', '-y', '-v', 'error', '-i', args.beside, '-i', args.output,
                    '-filter_complex', f'[0:v]scale=-2:{height}[a];[1:v]scale=-2:{height}[b];[a][b]hstack',
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-shortest',
                    args.compare_output], check=True)
    print(f'Side by side: {args.compare_output}')
