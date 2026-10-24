# Robot Learning Workshop

Video → human motion with **GVHMR** → grounded **Booster K1** motion with **GMR**.
Training runs on the workshop servers. This container prepares and exports motion only.

## Before you start

Register separately at **[SMPL-X](https://smpl-x.is.tue.mpg.de/)** and **[SMPL](https://smpl.is.tue.mpg.de/)**, accept their terms, and keep both logins ready. The software downloads and places the models after login.

```bash
git clone https://github.com/ATR-Lab/robot-learning-workshop.git
cd robot-learning-workshop
```

## Option 1 · Docker on Windows or Ubuntu

Use an NVIDIA GPU. On **Ubuntu**, install the [NVIDIA driver](https://www.nvidia.com/en-us/drivers/), [Docker Engine and Compose](https://docs.docker.com/engine/install/ubuntu/), and [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html), including its Docker configuration step.

On **Windows**, install the NVIDIA Windows driver and [Docker Desktop with WSL 2](https://docs.docker.com/desktop/features/wsl/). Enable integration with your Ubuntu WSL distro, and run all workshop commands inside its Ubuntu terminal. Do not install a Linux NVIDIA display driver inside WSL. See [Docker GPU prerequisites](https://docs.docker.com/desktop/features/gpu/).

Check `nvidia-smi` and `docker info`, then run:

```bash
./setup.sh
```

Setup builds the images, checks CUDA, asks for **both SMPL-X and SMPL** logins and downloads the models and a sample video. Repeat `./workshop auth` to change accounts. No host Python/Conda is needed. Allow **60 GB free** as a first-install planning allowance, including images/cache, about 6 GB of models, and outputs. Check the Docker storage disk too. Credentials and models stay in ignored `data/`; do not share that folder wholesale. See the [step-by-step Docker/Toolkit/runtime installation](docker.md).

## Option 2 · macOS (Apple Silicon)

Runs both steps natively: GVHMR on the Apple GPU, GMR in its own environment. Follow [the Mac instructions](macos.md). Docker is not required for this option. Training runs on the workshop servers.

## Use Docker

Put a short video in `data/inputs/clip.mp4`: one person, full body visible, stationary camera.

```bash
./workshop body data/inputs/clip.mp4
./workshop robot clip
```

Results are in `data/outputs/clip/`: human-motion `gvhmr/hmr4d_results.pt`, robot-motion `robot_data/booster_k1/clip_booster_k1.pkl`, `clip.csv`, staged video and logs. Send **only this clip's output folder** to the workshop server using the organizer's transfer instructions. The server handles training-format conversion and policy training.

To run both steps together, use `./workshop process data/inputs/clip.mp4`.

Already recovered motion on your Mac? Copy the trusted 30 fps result into `data/` and run:

```bash
./workshop robot data/my-result/hmr4d_results.pt --clip clip
```

Other commands:

```bash
./workshop doctor           # GPU and dependency checks
./workshop check            # ✓/✗ models needed for conversion
./workshop download         # missing checkpoints + sample video
./workshop info             # full GVHMR status
./workshop shell            # container shell
```

## Update

Run `git pull`, then `./setup.sh`. It keeps inputs, outputs, saved logins and downloaded models. Data persists between containers. GVHMR and GMR have separate stage packages and share one pinned Torch/CUDA installation to avoid duplicating several GB. Organizers can distribute a tested image using `WORKSHOP_IMAGE=registry/image:version ./setup.sh --deps-only`; no prebuilt image is published yet.

## MuJoCo policy playback

`./setup.sh` installs MuJoCo and the K1 model in its own environment/image. `./setup.sh --sim-only` installs just the player. Save a workshop export as `data/policies/policy.onnx`, then run:

```bash
# Mac
./sim play data/policies/policy.onnx
# Ubuntu / Windows WSL
./sim --docker play data/policies/policy.onnx
```

Docker uses http://localhost:8080 (**Play**, **Reset**); Mac opens the native viewer (**Enter** resets, **Space** pauses). Add `--web` on Mac for the browser, or `--check` for a headless no-fall check. A direct ONNX/ZIP URL or a policy folder also works.

**Current workshop exports:** the mjlab tracking ONNX contains the reference motion and metadata. The player reads joint order, gains, action scale and observations automatically. K1 resources and timing/motor defaults come from the [pinned training source](https://github.com/IntelligentRoboticsLab/booster_mjlab/tree/d92e11395d961096d639446c0a8a176f12bb51da/src/booster_mjlab/robots/booster_k1). Unsupported layouts fail explicitly; unrelated ONNX files and raw training `.pt`/`.pth` checkpoints cannot be substituted.

**Older exports:** keep `config.json`, the matching reference and robot folder together. You can point to the ONNX within that original folder; the player finds its sidecars. Bundles stay in ignored `data/policies/`; downloaded Python scripts are never executed. No body-model accounts, Isaac Lab, ROS or CUDA are needed for playback.

The complete cartwheel example is included in Git:

```bash
./sim play examples/cartwheel
```

Other exports on the organizer's Mac (download separately):

```bash
# Legacy cartwheel: uses the supplied settings and reference beside the ONNX
./sim play ~/Downloads/Booster-K1-Cartwheel-MuJoCo/policies/final_29999/policy.onnx
# Current workshop export: motion and settings are inside the ONNX
./sim play ~/Downloads/policy-7c5a3e31/policy.onnx
```

The cartwheel performs a standing start, cartwheel and standing finish. The second file is an iteration-0 export used to verify the format; it falls in simulation and is not a trained demo. For sharing a legacy bundle: `./sim import ~/Downloads/Booster-K1-Cartwheel-MuJoCo --name cartwheel`, then `./sim pack cartwheel --output data/exports/booster-k1-cartwheel.zip`. See [Booster's MuJoCo instructions](https://docs.booster.tech/docs/developer-guide/open-source/booster-deploy/) and [MuJoCo's Mac launcher documentation](https://mujoco.readthedocs.io/en/stable/python.html#passive-viewer).

The supplied `final_29999` export completes its 10.24 s headless Mac and Ubuntu/Docker checks and returns upright without falling on MuJoCo 3.16.0. Docker rendering and the browser endpoint were also checked. See [validation results](validation.md).

## Mac and status

On Apple Silicon, keep using native GVHMR for Apple GPU acceleration; Docker on Mac does not provide CUDA. This Docker setup targets Linux + NVIDIA, including Ubuntu under WSL 2.

The full **Ubuntu + NVIDIA Docker pipeline is validated** on the tennis sample: GVHMR → GMR → CSV. The native Mac pipeline (both steps with videos) was run on a shadowboxing clip; Windows/WSL2 remains unverified. See the [tested versions, commands and limits](validation.md).

## More commands and troubleshooting

| Command | What it does |
| :--- | :--- |
| `./workshop body data/inputs/x.mp4` | Step 1 · video → body pose: `data/outputs/x/gvhmr/hmr4d_results.pt` + `x_pose.mp4` (Mac and Docker) |
| `./workshop robot x` | Step 2 · body pose → K1 CSV + videos. A `.pt` path also works; add `--clip NAME` if it is not in `data/outputs/<name>/gvhmr/` |
| `./workshop process data/inputs/x.mp4` | Both of the above. Add `--no-video` to any of the three to skip videos. `convert`/`retarget` are old names for `body`/`robot` and still work |
| `./workshop motion <csv or folder>` | Play a K1 motion CSV without a policy (Mac window, Docker browser; `--record x.mp4`). 8 dances in `examples/dances` |
| `./workshop download` | Missing checkpoints + sample video, then the ✓ check |
| `./workshop info` | Full GVHMR status. DPVO and data packs (3dpw, amass, …) stay ✗: not needed. Ignore its `gvhmr download` hint; use `./workshop download` |
| `./setup.sh --deps-only` | Install without logins or downloads |
| `./setup.sh --sim-only` | MuJoCo player only; no accounts or NVIDIA GPU needed, then `./workshop demo` |
| `SIM_PORT=8081 ./workshop demo` | Choose the browser port (Linux picks the next free port if 8080 is busy). Over SSH: `ssh -L 8081:localhost:8081 user@server` |

- **Outputs** are named after the video: `dance.mp4` → `data/outputs/dance/`, logs in its `logs/`. Replacing a video keeps the old results under `previous-*/`, which uses extra disk space.
- **Mac environments:** launchers pick their own Python 3.12 automatically. For manual use: `source .venv/bin/activate` (GVHMR) or `source .venv-sim/bin/activate` (MuJoCo). Old incompatible environments are saved in `data/environment-backups/`.
- **Start over (Linux):** Docker writes some `data/` files as root, so plain `rm -rf` fails. Use `docker run --rm -v "$PWD":/w ubuntu:24.04 rm -rf /w/data` and `docker rmi robot-learning-workshop:dev robot-learning-workshop-sim:dev`.

## Credits

[Expressive Motion](https://github.com/ATR-Lab/expressive-motion) provides ground alignment and the K1 export pipeline (pinned at `a66e910d53da0d90eae845d35aad7c9eb2ae4a04`, with its GMR submodule). GVHMR pip fork: `1.6.1` (archived). Dependency snapshots are saved by `doctor`; transitive dependencies are not fully locked yet.

[GVHMR](https://github.com/zju3dv/GVHMR/blob/main/LICENSE) and SMPL/SMPL-X have research/non-commercial terms. Models and weights are downloaded for each participant and excluded from Git and the image. Upstream licenses apply. Only load trusted `.pt`/`.pkl` files.
