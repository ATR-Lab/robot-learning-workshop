"""Run in the GMR environment: render a GMR K1 motion (.pkl) to mp4, optionally beside the input video."""
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
renderer = mj.Renderer(model, height=height, width=width)
camera = mj.MjvCamera()
camera.distance, camera.elevation, camera.azimuth = 2.5, -10.0, 90.0  # facing the robot's front

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
print(f'K1 video: {args.output} ({len(root_pos)} frames at {fps:g} fps)')

if args.beside:
    subprocess.run(['ffmpeg', '-nostdin', '-y', '-v', 'error', '-i', args.beside, '-i', args.output,
                    '-filter_complex', f'[0:v]scale=-2:{height}[a];[1:v]scale=-2:{height}[b];[a][b]hstack',
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-shortest',
                    args.compare_output], check=True)
    print(f'Side by side: {args.compare_output}')
