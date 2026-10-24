# Advanced · use the tools directly

`./workshop` is a thin wrapper. Underneath are three real tools you can drive yourself:

| Stage | Tool | Inside Docker |
| :--- | :--- | :--- |
| Video → body pose | [GVHMR](https://github.com/zju3dv/GVHMR) | `/opt/gvhmr` environment, `gvhmr` CLI + Python API |
| Body pose → robot | [GMR](https://github.com/YanjieZe/GMR) + ground/foot alignment | `/opt/gmr` environment, scripts in `/opt/pipeline` |
| Robot motion → picture | [MuJoCo](https://mujoco.readthedocs.io/) | in both environments |

## Get inside

```bash
./workshop shell                      # bash in the workshop container, at /workspace (= this repo)
source /opt/gvhmr/bin/activate        # GVHMR stage    · or: source /opt/gmr/bin/activate for GMR
```

Only `/workspace` is kept: this repository and its `data/` folder. The container is deleted when you exit, so **save everything under `data/`**; changes elsewhere (for example in `/opt`) are lost. Models, logins and caches are already wired up through environment variables.

Mac: no shell needed. `source .venv/bin/activate` for GVHMR or `source .venv-gmr/bin/activate` for GMR, from the repository folder. Wherever this page says `/opt/pipeline`, use `.pipeline` on a Mac; body models are where `./workshop info` shows them.

## GVHMR · video → body pose

```bash
gvhmr demo data/inputs/tennis.mp4 -s -o data/outputs/demo     # -s = static camera
```

This writes `data/outputs/demo/tennis/hmr4d_results.pt` and overlay videos: `1_incam.mp4` (body over the video), `2_global.mp4` (body in 3D) and `tennis_3_incam_global_horiz.mp4` (both). Useful options (`gvhmr demo --help` for all):

| Option | Use it for |
| :--- | :--- |
| `--camera simplevo` / `dpvo` / `dust3r` / `vggt` | Moving camera instead of `-s` |
| `--f-mm 24` | Known focal length (iPhone 1x ≈ 24, 2x ≈ 48) |
| `--recipe accurate` · `hq` · `fast` | Quality vs speed bundles (`gvhmr list recipe`) |
| `--flip-test` | Slower, slightly more accurate |
| `--skeleton` | Extra skeleton video |
| `--smplx` | Render the SMPL-X surface |
| `--render-scale 1.0` | Full-resolution overlays |
| `--no-render` | Motion only |
| `--set detector.conf=0.4` | Any config value (Hydra override) |

`gvhmr list` shows the swappable detectors, 2D-pose models and cameras. Python, from the same environment:

```python
import gvhmr
result = gvhmr.recover("data/inputs/tennis.mp4", static_camera=True, output_dir="data/outputs/py")
result.save("data/outputs/py/hmr4d_results.pt")
result.render("data/outputs/py/pose.mp4")          # view="camera" / "world" / "both"
```

## GMR · body pose → robot

```bash
source /opt/gmr/bin/activate
python /opt/pipeline/scripts/retarget_gvhmr.py \
    --gvhmr-result data/outputs/tennis/gvhmr/hmr4d_results.pt \
    --robot booster_k1 --output data/outputs/try/tennis_k1.pkl \
    --body-models data/body_models --fps 30 --clip-name tennis
python scripts/render_motion.py data/outputs/try/tennis_k1.pkl data/outputs/try/tennis_k1.mp4
```

- **Other robots:** `--list-robots` shows them (Unitree G1/H1, Booster T1, Fourier, …). For example, `--robot unitree_g1` works with the same commands, including `render_motion.py`.
- **Ground and contact settings:** `--set ground.cutoff_hz=0.5`, `--set ground.enabled=false` or `--no-ground-fix`. Defaults and all keys: `/opt/pipeline/configs/pipeline.json`.
- **IK mapping (which human joint drives which robot link, weights, scale):** `/opt/pipeline/external/GMR/general_motion_retargeting/ik_configs/smplx_to_k1.json`. Edit it inside the shell and rerun; to keep a version, copy it to `data/` because the container resets on exit.
- **CSV:** `python /opt/pipeline/external/GMR/scripts/batch_gmr_pkl_to_csv.py --folder data/outputs/try`. Columns: root position, root quaternion `x,y,z,w`, joint angles.
- **Video options:** `render_motion.py --size 720` for a larger video; `--beside input.mp4 --compare-output side.mp4` for a side-by-side.

## MuJoCo · play and record

```bash
./workshop play examples/cartwheel --record data/cartwheel.mp4   # policy → video (outside the shell)
```

The K1 model is `/opt/pipeline/external/GMR/assets/booster_k1/K1_serial.xml` (Docker) and `examples/cartwheel/robot/` (also in this repository). Load it in Python with `mujoco.MjModel.from_xml_path(...)`. `scripts/render_motion.py` is a short example of setting `qpos` frame by frame and rendering off-screen.

## Where things are

| Path (Docker) | What |
| :--- | :--- |
| `/workspace/data/checkpoints`, `/workspace/data/body_models` | GVHMR weights, SMPL/SMPL-X models |
| `/opt/gvhmr/lib/python3.11/site-packages/gvhmr` | GVHMR source |
| `/opt/pipeline/scripts/retarget_gvhmr.py` | Retargeting + ground/foot alignment |
| `/opt/pipeline/external/GMR` | GMR: robots in `assets/`, IK configs, scripts |
| `scripts/` in this repository | The `./workshop` wrapper: copy and adapt freely |
