"""Run a K1 tracking policy (BeyondMimic, ONNX) in plain MuJoCo. No Isaac Lab or torch.

  ./sim play cartwheel                         # native window (mjpython on Mac)
  ./sim play cartwheel --web                   # browser viewer
  ./sim play cartwheel --record data/cartwheel.mp4
  ./sim play cartwheel --check                 # headless metrics and completion check

Viewer keys: Enter = reset to the start, Space = pause. Double-click the robot, then Ctrl + right-drag pushes it.
The blue see-through robot is the reference motion. Hide it with --no-ghost.

Try:
  --friction 0.6     slippery floor (the grids tested 0.6 / 0.9 / 1.2)
  --delay 8          actuator delay in 5 ms physics steps (training randomized 2..8)
  --pose positive    start a bit tilted (+0.05 rad roll/pitch, +0.1 yaw, +0.03 rad on every joint)

Physics and observations follow the project's own MuJoCo check (readiness_v5/scripts/evaluate_policy.py):
200 Hz physics, 50 Hz policy, PD torques computed here with the trained gains, torque-speed limits and a fixed
actuator delay, written to qfrc_applied (the MJCF motors are bypassed).
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import mujoco
import numpy as np
import onnxruntime as ort

p = argparse.ArgumentParser()
p.add_argument("--policy", required=True, help="directory containing config.json")
mode = p.add_mutually_exclusive_group()
mode.add_argument("--record", help="write an mp4 instead of opening the viewer (requires ffmpeg)")
mode.add_argument("--check", action="store_true", help="headless run, print metrics, fail if unsuccessful")
mode.add_argument("--web", action="store_true", help="browser viewer; no display or GPU required")
p.add_argument("--host", default="0.0.0.0" if os.environ.get("SIM_DOCKER") else "127.0.0.1")
p.add_argument("--port", type=int, default=8080)
p.add_argument("--json", help="also write the metrics to this json file")
p.add_argument("--friction", type=float, default=0.9)
p.add_argument("--delay", type=int, default=5, help="actuator delay in physics steps (default: 25 ms)")
p.add_argument("--pose", default="nominal", choices=["nominal", "positive", "negative"])
p.add_argument("--hold", type=float, default=None, help="seconds to keep tracking the last frame after the clip")
p.add_argument("--no-ghost", action="store_true", help="do not draw the reference robot")
p.add_argument("--width", type=int, default=1280)
p.add_argument("--height", type=int, default=720)
p.add_argument("--label", default=None, help="caption burned into the video")
args = p.parse_args()
if args.delay < 0 or args.friction < 0 or (args.hold is not None and args.hold < 0):
    p.error("delay, friction and hold must be non-negative")
if args.width < 64 or args.height < 64 or args.width % 2 or args.height % 2:
    p.error("video width/height must be even and at least 64 pixels")


# ---------- quaternion helpers (MuJoCo order w, x, y, z) ----------
def quat_to_mat(q):
    w, x, y, z = q / np.linalg.norm(q)
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


def quat_mul(a, b):
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return np.array([
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
    ])


def axis_quat(axis, angle):
    q = np.zeros(4)
    q[0] = np.cos(angle / 2)
    q[1 + axis] = np.sin(angle / 2)
    return q


def yaw_of(q):
    r = quat_to_mat(q)
    return np.arctan2(r[1, 0], r[0, 0])


# ---------- load policy folder ----------
pdir = Path(args.policy)
cfg = json.loads((pdir / "config.json").read_text())
if cfg["obs_dim"] not in (119, 125, 128) or len(cfg["joint_names"]) != 22:
    p.error("supported K1 tracking exports have 22 joints and 119, 125 or 128 observations")
if not np.isclose(cfg["policy_dt"], cfg["sim_dt"] * cfg["decimation"]):
    p.error("policy_dt must equal sim_dt × decimation")
policy = ort.InferenceSession(str(pdir / cfg["onnx"]), providers=["CPUExecutionProvider"])
in_name = policy.get_inputs()[0].name
if policy.get_inputs()[0].shape[-1] != cfg["obs_dim"] or policy.get_outputs()[0].shape[-1] != 22:
    p.error("ONNX observation/action dimensions do not match config.json")
with np.load(pdir / cfg["motion"], allow_pickle=False) as archive:
    motion = {k: v for k, v in archive.items()}
xml = str((pdir / cfg["robot_xml"]).resolve())
hold = cfg["hold_seconds_after_motion"] if args.hold is None else args.hold

names = cfg["joint_names"]  # policy order, also the order in the motion npz
if list(motion["joint_names"]) != names:
    p.error("reference joint order differs from config.json; use the matching motion export")
bi = list(motion["body_names"]).index(cfg["anchor_body"])
T = len(motion["joint_pos"])
if not T or motion["joint_pos"].shape[1:] != (22,) or motion["joint_vel"].shape != (T, 22):
    p.error("reference motion must contain nonempty joint_pos/joint_vel arrays of shape (T, 22)")
if "fps" in motion and not np.isclose(float(motion["fps"].item()), 1 / cfg["policy_dt"]):
    p.error("reference frame rate differs from policy_dt; use the matching motion export")
steps_total = T + int(round(hold / cfg["policy_dt"]))

kp, kd = np.array(cfg["kp"]), np.array(cfg["kd"])
effort, vmax = np.array(cfg["effort_limit"]), np.array(cfg["velocity_limit"])
knee = np.minimum(np.array(cfg["knee_point_velocity"]), vmax)
scale, default = np.array(cfg["action_scale"]), np.array(cfg["default_joint_pos"])
head_idx = [names.index("AAHead_yaw"), names.index("Head_pitch")] if cfg["head_zero"] else []
obs_keep = np.arange(125) if cfg["obs_dim"] in (125, 128) else np.r_[0:44, 47:53, 56:125]
implicit_position = cfg.get("control_mode") == "implicit_position"


# ---------- MuJoCo model, set up like the training config ----------
def make_model():
    m = mujoco.MjModel.from_xml_path(xml)
    m.opt.timestep = cfg["sim_dt"]
    m.opt.gravity[:] = [0, 0, -9.81]
    m.opt.iterations = cfg.get("solver_iterations", 100)
    m.opt.integrator = mujoco.mjtIntegrator.mjINT_IMPLICITFAST
    if not implicit_position:
        m.geom_condim[:] = 3
        m.geom_friction[:] = [args.friction, 0.005, 0.0001]
    else:
        # Nominal training coefficients; --friction changes them proportionally.
        m.geom_friction[:, 0] *= args.friction / 0.9
    m.actuator_forcelimited[:] = implicit_position
    m.actuator_ctrllimited[:] = False
    m.geom_group[m.geom("ground").id] = 2  # so we can hide collision geoms (group 0) but keep the floor
    m.vis.global_.offwidth = max(args.width, 640)
    m.vis.global_.offheight = max(args.height, 480)
    return m


m = make_model()
d = mujoco.MjData(m)
jid = [m.joint(n).id for n in names]
qa = m.jnt_qposadr[jid]
va = m.jnt_dofadr[jid]
m.dof_armature[va] = cfg["armature"]
m.dof_damping[va] = 0
m.dof_frictionloss[va] = 0
limits = m.jnt_range[jid]
trunk = m.body(cfg["anchor_body"]).id
decimation = cfg["decimation"]
act_ids = np.array([m.actuator(n).id for n in names]) if implicit_position else None

ref_m = make_model()  # second copy only for drawing the reference
ref_d = mujoco.MjData(ref_m)


class Episode:
    def reset(self):
        mujoco.mj_resetData(m, d)
        z = {k: v.copy() for k, v in motion.items()}
        if cfg["start"] == "standing":
            d.qpos[:3] = [0, 0, cfg["standing_root_height"]]
            d.qpos[3:7] = [1, 0, 0, 0]
            d.qpos[qa] = default
            if args.pose != "nominal":
                s = 1 if args.pose == "positive" else -1
                q = quat_mul(axis_quat(2, s * 0.1), quat_mul(axis_quat(1, s * 0.05), axis_quat(0, s * 0.05)))
                d.qpos[3:7] = q
                d.qpos[qa] = np.clip(default + s * 0.03, limits[:, 0], limits[:, 1])
        else:  # start in the first reference frame, with its velocities
            mid, half = limits.mean(1), (limits[:, 1] - limits[:, 0]) * 0.45
            d.qpos[:3] = z["body_pos_w"][0, bi]
            d.qpos[3:7] = z["body_quat_w"][0, bi]
            d.qpos[qa] = np.clip(z["joint_pos"][0], mid - half, mid + half)
            d.qvel[:3] = z["body_lin_vel_w"][0, bi]
            d.qvel[3:6] = quat_to_mat(d.qpos[3:7]).T @ z["body_ang_vel_w"][0, bi]
            d.qvel[va] = z["joint_vel"][0]
        mujoco.mj_forward(m, d)
        if cfg["reanchor_reference_xy_yaw"]:
            # Move the reference so it starts where the robot stands (xy and yaw only). The robot is never moved.
            origin = z["body_pos_w"][0, bi].copy()
            dyaw = yaw_of(d.qpos[3:7]) - yaw_of(z["body_quat_w"][0, bi])
            align, rz = axis_quat(2, dyaw), quat_to_mat(axis_quat(2, dyaw))
            z["body_pos_w"] = (z["body_pos_w"] - origin) @ rz.T + np.array([d.qpos[0], d.qpos[1], origin[2]])
            shape = z["body_quat_w"].shape
            z["body_quat_w"] = np.array([quat_mul(align, q) for q in z["body_quat_w"].reshape(-1, 4)]).reshape(shape)
            for k in ("body_lin_vel_w", "body_ang_vel_w"):
                z[k] = z[k] @ rz.T
        self.z = z
        self.step_i = 0
        self.last = np.zeros(22, dtype=np.float32)
        self.history = [default.copy() for _ in range(args.delay)]
        self.log = dict(z=[], up=[], err=[], tq=[], spd=[])
        self.fall_time = None

    def ref_t(self):
        return min(self.step_i, T - 1)

    def obs(self):
        z, t = self.z, self.ref_t()
        rb = quat_to_mat(d.qpos[3:7])
        rr = quat_to_mat(z["body_quat_w"][t, bi])
        pos_b = rb.T @ (z["body_pos_w"][t, bi] - d.qpos[:3])
        ori_b = (rb.T @ rr)[:, :2].reshape(-1)
        vel = np.zeros(6)
        mujoco.mj_objectVelocity(m, d, mujoco.mjtObj.mjOBJ_BODY, trunk, vel, 1)  # local frame: [ang, lin]
        full = np.concatenate((z["joint_pos"][t], z["joint_vel"][t], pos_b, ori_b, vel[3:], vel[:3],
                               d.qpos[qa] - default, d.qvel[va], self.last))
        if "observation_names" in cfg:
            parts = dict(command=np.r_[z["joint_pos"][t], z["joint_vel"][t]],
                         motion_anchor_pos_b=pos_b, motion_anchor_ori_b=ori_b,
                         base_lin_vel=d.sensor("imu_lin_vel").data.copy(),
                         base_ang_vel=d.sensor("imu_ang_vel").data.copy(),
                         joint_pos=d.qpos[qa] - default, joint_vel=d.qvel[va], actions=self.last,
                         projected_gravity=rb.T @ np.array([0., 0., -1.]))
            values = []
            for name, scale_, clip_ in zip(cfg["observation_names"], cfg["observation_scales"], cfg["observation_clips"]):
                low, high = clip_
                values.append(np.clip(parts[name], -np.inf if low is None else low,
                                      np.inf if high is None else high) * np.array(scale_))
            return np.concatenate(values).astype(np.float32)
        return full[obs_keep].astype(np.float32)

    def step(self):
        """One 50 Hz policy step = 4 physics steps."""
        t = self.ref_t()
        # Log the state the policy sees (same convention as the project's evaluate_policy.py).
        self.log["z"].append(float(d.qpos[2]))
        self.log["up"].append(float(quat_to_mat(d.qpos[3:7])[2, 2]))
        self.log["err"].append(float(np.linalg.norm(d.qpos[:3] - self.z["body_pos_w"][t, bi])))
        if self.fall_time is None and d.qpos[2] < 0.25:
            self.fall_time = self.step_i * cfg["policy_dt"]
        inputs = {in_name: self.obs()[None]}
        if cfg.get("onnx_time_step"):
            inputs["time_step"] = np.array([[self.ref_t()]], dtype=np.float32)
        action = policy.run([policy.get_outputs()[0].name], inputs)[0][0]
        self.last = action.astype(np.float32)
        target = default + scale * action
        if cfg["head_zero"]:
            target[head_idx] = 0.0
        for _ in range(decimation):
            self.history.append(target.copy())
            delayed = self.history.pop(0)
            qd = d.qvel[va]
            cap = np.clip(effort * (vmax - np.abs(qd)) / np.maximum(vmax - knee, 1e-6), 0, effort)
            tau = np.clip(kp * (delayed - d.qpos[qa]) - kd * qd, -cap, cap)
            if implicit_position:
                m.actuator_forcerange[act_ids] = np.column_stack((-cap, cap))
                d.ctrl[act_ids] = delayed
            else:
                d.ctrl[:] = 0
                d.qfrc_applied[:] = 0
                d.qfrc_applied[va] = tau
            mujoco.mj_step(m, d)
            torque = d.actuator_force[act_ids] if implicit_position else tau
            self.log["tq"].append(np.abs(torque) / effort)
            self.log["spd"].append(np.abs(qd) / vmax)
        if not np.isfinite(d.qpos).all():
            raise RuntimeError("MuJoCo state became non-finite")
        self.step_i += 1

    def done(self):
        return self.step_i >= steps_total

    def ref_qpos(self):
        z, t = self.z, self.ref_t()
        q = np.zeros(m.nq)
        q[:3] = z["body_pos_w"][t, bi]
        q[3:7] = z["body_quat_w"][t, bi]
        q[qa] = z["joint_pos"][t]
        return q

    def metrics(self):
        L = self.log
        tq = np.array(L["tq"])
        sat = tq > 0.9 + 1e-6  # time each joint spends above 90% of its torque limit
        longest = 0
        for j in range(sat.shape[1]):
            run = 0
            for v in sat[:, j]:
                run = run + 1 if v else 0
                longest = max(longest, run)
        up = np.array(L["up"])
        return dict(
            policy=cfg["name"], friction=args.friction, delay_ms=args.delay * cfg["sim_dt"] * 1000, pose=args.pose,
            seconds=round(len(L["z"]) * cfg["policy_dt"], 2),
            fell=self.fall_time is not None, fall_time_s=self.fall_time,
            went_upside_down=bool(up.min() < -0.5), min_upright=round(float(up.min()), 3),
            final_upright=round(float(up[-1]), 4), min_trunk_height_m=round(min(L["z"]), 3),
            final_trunk_height_m=round(L["z"][-1], 3),
            mean_root_error_m=round(float(np.mean(L["err"])), 3), max_root_error_m=round(float(max(L["err"])), 3),
            final_root_error_m=round(L["err"][-1], 3),
            peak_torque_fraction=round(float(tq.max()), 3), longest_torque_over_90pct_ms=longest * cfg["sim_dt"] * 1000,
            peak_speed_fraction=round(float(np.max(L["spd"])), 3),
            completed=bool(self.fall_time is None and up.min() < -0.5 and up[-1] > 0.8),
        )


ep = Episode()
ep.reset()

ghost_opt = mujoco.MjvOption()
ghost_opt.geomgroup[:] = 0
ghost_opt.geomgroup[cfg.get("visual_group", 1)] = 1
main_opt = mujoco.MjvOption()
main_opt.geomgroup[cfg.get("collision_group", 0)] = 0


def add_ghost(scn):
    if args.no_ghost:
        return
    ref_d.qpos[:] = ep.ref_qpos()
    mujoco.mj_forward(ref_m, ref_d)
    n0 = scn.ngeom
    mujoco.mjv_addGeoms(ref_m, ref_d, ghost_opt, mujoco.MjvPerturb(), mujoco.mjtCatBit.mjCAT_DYNAMIC, scn)
    for i in range(n0, scn.ngeom):
        scn.geoms[i].rgba[:] = [0.25, 0.6, 1.0, 0.3]


def print_metrics():
    r = ep.metrics()
    print(json.dumps(r, indent=1), flush=True)
    if args.json:
        path = Path(args.json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(r, indent=1) + "\n")
    if cfg.get("kind") in ("dance", "tracking"):
        verdict = f"FELL at {r['fall_time_s']:.2f} s" if r["fell"] else "no fall"
    else:
        verdict = "COMPLETED the cartwheel" if r["completed"] else (
        f"FELL at {r['fall_time_s']:.2f} s" if r["fell"] else "did not complete (no fall, check upright values)")
    print(f"{cfg['name']}: {verdict}", flush=True)
    return not r["fell"] if cfg.get("kind") in ("dance", "tracking") else r["completed"]


if args.web:
    import viser
    from mjviser import ViserMujocoScene

    server = viser.ViserServer(host=args.host, port=args.port)
    server.scene.set_up_direction("+z")
    scene = ViserMujocoScene(server, m, num_envs=1)
    scene.camera_tracking_enabled = False
    scene.geom_groups_visible = [bool(v) for v in main_opt.geomgroup]
    server.gui.add_markdown(f"## Booster K1 · {cfg['name']}\nMuJoCo simulation. Press Play to start.")
    play = server.gui.add_checkbox("Play", initial_value=False)
    reset = server.gui.add_button("Reset")
    status = server.gui.add_markdown("Ready")
    state = {"reset": False}

    @reset.on_click
    def request_reset(_):
        state["reset"] = True

    @server.on_client_connect
    def set_camera(client):
        client.camera.position = (2.0, -3.0, 1.7)
        client.camera.look_at = (0.0, 0.0, 0.5)

    scene.update_from_mjdata(d)
    print(f"Open http://localhost:{args.port} and press Play. Ctrl+C stops the server.", flush=True)
    try:
        while True:
            started = time.perf_counter()
            if state["reset"]:
                ep.reset()
                state["reset"] = False
                play.value = False
                status.content = "Ready"
            if play.value and not ep.done():
                ep.step()
                if ep.done():
                    success = print_metrics()
                    status.content = "Finished" if success else "Check failed — see terminal metrics"
                    play.value = False
            scene.update_from_mjdata(d)
            time.sleep(max(0.001, cfg["policy_dt"] - (time.perf_counter() - started)))
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
    sys.exit(0)


if args.record or args.check:
    if args.check:
        while not ep.done():
            ep.step()
        sys.exit(0 if print_metrics() else 1)
    from PIL import Image, ImageDraw, ImageFont

    W, H = args.width, args.height
    r = mujoco.Renderer(m, H, W)
    cam = mujoco.MjvCamera()
    cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    cam.distance, cam.elevation = 2.6, -10.0
    # Look at the robot from the side the cartwheel travels across.
    travel = ep.z["body_pos_w"][T - 1, bi, :2] - ep.z["body_pos_w"][0, bi, :2]
    cam.azimuth = np.degrees(np.arctan2(travel[1], travel[0])) + 90.0
    look = d.qpos[:3].copy()
    look[2] = 0.45
    try:
        font = ImageFont.load_default(size=max(16, H // 30))
    except TypeError:
        font = ImageFont.load_default()
    label = args.label or f"K1 cartwheel, policy {cfg['name']} in MuJoCo"
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        p.error("video recording requires ffmpeg on PATH; install it or use --web / --check")
    out = Path(args.record)
    out.parent.mkdir(parents=True, exist_ok=True)
    fps = round(1 / cfg["policy_dt"])
    proc = subprocess.Popen([ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                             "-crf", "20", "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE)

    def frame():
        look[:2] = 0.9 * look[:2] + 0.1 * d.qpos[:2]  # smooth follow of the trunk
        cam.lookat[:] = look
        r.update_scene(d, camera=cam, scene_option=main_opt)
        add_ghost(r.scene)
        img = Image.fromarray(r.render())
        dr = ImageDraw.Draw(img)
        t = ep.step_i * cfg["policy_dt"]
        txt = f"{label}\nt = {t:5.2f} s   friction {args.friction}   delay {args.delay * 5} ms"
        if not args.no_ghost:
            txt += "\nblue = reference motion"
        if ep.fall_time is not None:
            txt += f"\nFELL at {ep.fall_time:.2f} s"
        dr.multiline_text((16, 12), txt, fill=(255, 255, 255), font=font, stroke_width=2, stroke_fill=(0, 0, 0))
        proc.stdin.write(np.asarray(img).tobytes())

    frame()
    while not ep.done():
        ep.step()
        frame()
    proc.stdin.close()
    if proc.wait():
        raise RuntimeError("ffmpeg failed to encode the video")
    success = print_metrics()
    print("wrote", out)
    sys.exit(0 if success else 1)

# ---------- interactive window (needs mjpython on macOS) ----------
import mujoco.viewer  # noqa: E402

state = dict(paused=False, reset=False)


def key(k):
    if k in (257, 335, 259):  # Enter, keypad Enter, Backspace
        state["reset"] = True
    elif k == 32:  # Space
        state["paused"] = not state["paused"]


print(__doc__.split("Try:")[0])
with mujoco.viewer.launch_passive(m, d, key_callback=key) as v:
    v.opt.geomgroup[:] = main_opt.geomgroup
    v.cam.distance, v.cam.elevation = 2.8, -12.0
    travel = ep.z["body_pos_w"][T - 1, bi, :2] - ep.z["body_pos_w"][0, bi, :2]
    v.cam.azimuth = np.degrees(np.arctan2(travel[1], travel[0])) + 90.0
    v.cam.lookat[:] = [*(0.5 * travel + d.qpos[:2]), 0.45]
    reported = False
    while v.is_running():
        t0 = time.perf_counter()
        with v.lock():
            if state["reset"]:
                ep.reset()
                state["reset"], reported = False, False
                print("reset")
            if not state["paused"]:
                ep.step()  # after the clip it keeps tracking the last frame (standing)
            v.user_scn.ngeom = 0
            add_ghost(v.user_scn)
        if not reported and ep.step_i >= steps_total:
            print_metrics()
            print("Press Enter to run it again.")
            reported = True
            state["paused"] = True
        v.sync()
        time.sleep(max(0.0, cfg["policy_dt"] - (time.perf_counter() - t0)))
