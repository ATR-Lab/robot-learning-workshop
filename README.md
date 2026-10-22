# Robot Learning Workshop

**Your video → human motion → robot motion. Training happens on workshop servers.**

[Watch the K1 cartwheel reference video](docs/examples/cartwheel_final_29999.mp4). A complete runnable [cartwheel example](examples/cartwheel) is included: policy, reference motion, K1 model and CSVs.

### ① Register

For video conversion, create **two separate accounts** at **[SMPL-X](https://smpl-x.is.tue.mpg.de/)** and **[SMPL](https://smpl.is.tue.mpg.de/)**. Accept the terms on both sites. You will enter both logins in step ④.

### ② Download

```bash
git clone https://github.com/ATR-Lab/robot-learning-workshop.git
cd robot-learning-workshop
```

### ③ Install dependencies

| Windows / Ubuntu · NVIDIA GPU | Mac · Apple Silicon |
| :--- | :--- |
| Install [Docker + GPU support](docs/docker.md). | Install [Homebrew](docs/macos.md) if needed. No Docker needed. |

`setup.sh` chooses automatically: **Mac → local `.venv` (GVHMR) and `.venv-sim` (MuJoCo); Linux / Windows WSL → Docker containers (GVHMR, GMR → CSV, MuJoCo).** Mac users use a workshop server for GMR → CSV. Docker keeps the dependencies inside containers instead of local Python environments.

Allow **20 GB free on Mac / 60 GB for Docker** as planning allowances, plus space for videos and outputs. Models alone are about **6 GB**. Check Docker's storage disk too (Windows: Docker Desktop/WSL storage). Old environment backups also use space.

Install **GVHMR, GMR (Docker only), MuJoCo and their dependencies**:
```bash
./setup.sh --deps-only
```

No Docker login or container shell is needed. Run commands in your normal terminal; on Windows, use Ubuntu/WSL. Docker users do not activate a venv.

**Already installed?** Run `git pull`, then `./setup.sh --deps-only` again. On Mac it installs Python 3.12 if needed and repairs both environments; incompatible old environments are saved under `data/environment-backups/`. Inputs, outputs and saved logins are kept. Plain `./setup.sh` still combines installation and authentication for compatibility.

Run all commands below from this repository's folder.

### ④ Sign in · SMPL-X and SMPL

**Before GVHMR**, have both accounts from step ① ready:
```bash
./workshop auth
./workshop info
```
Answer **yes for SMPL-X and yes for SMPL**, then enter each account's username/password. Body models download after login; inference checkpoints download on the first video run. Allow several minutes. Missing training datasets/DPVO in `info` are normal for this static-camera workflow.

**Log in again / change accounts:** rerun `./workshop auth`. Passwords are entered in the terminal and stored locally; do not put them in chat or Git. This is body-model authentication, not a Docker login. MuJoCo-only users can skip accounts: `./setup.sh --sim-only` → `./workshop demo`.

### ⑤ Convert video · GVHMR

Finish **both SMPL-X and SMPL logins above** before this step. For login/download failures, rerun `./workshop auth`; do not reinstall the environments.

Put a short video in `data/inputs/clip.mp4`: one person, full body visible, stationary camera. Or use [GVHMR's human tennis clip](https://raw.githubusercontent.com/zju3dv/GVHMR/ee960bb6e2ea2d381aa97f08e9b71ef320b624b1/docs/example_video/tennis.mp4). The cartwheel video above is a robot result, not a GVHMR input.

**Same command on Mac and Docker** — selects the environment, converts to 30 fps and checks decoded frames automatically:
```bash
./workshop convert data/inputs/clip.mp4
```

Human motion: **`data/outputs/clip/gvhmr/hmr4d_results.pt`** on both setups. For `dance.mp4`, the folder is `data/outputs/dance/`. Logs are in its `logs/` directory. Replacing the input saves old results under `previous-*/` instead of reusing stale motion; those backups use extra disk space.

### ⑥ Retarget to K1 + export CSV · GMR

**Docker** — use the result from step ⑤:
```bash
./workshop retarget data/outputs/clip/gvhmr/hmr4d_results.pt --clip clip
```

Result: **`data/outputs/clip/clip.csv`**. Mac users send their `.pt` to the workshop team for this step. The team trains a policy on the server.

### ⑦ Run policy · MuJoCo

**Try the included cartwheel first** — no separate downloads:
```bash
./workshop demo
```
Mac opens the viewer; Docker prints the browser URL → **Play** (normally **http://localhost:8080**; on Linux it selects the next free port if busy).

Save the workshop policy as **`data/policies/policy.onnx`**. Setup prepares K1 automatically; the workshop ONNX supplies its settings and motion.

**Same command on Mac and Docker:**
```bash
./workshop play data/policies/policy.onnx
```
Mac: **Enter** restarts; **Space** pauses. Docker: open the printed browser URL and press **Play**. To choose a port: `SIM_PORT=8081 ./workshop demo`.

Mac launchers select their own Python 3.12 environment automatically. For manual use: `source .venv/bin/activate` for GVHMR or `source .venv-sim/bin/activate` for MuJoCo. After rerunning setup, deactivate/reactivate any old terminal environment before using bare `gvhmr`.

[More policy details](docs/setup-details.md#mujoco-policy-playback). Your own trained policies are provided separately.

**Update:** `git pull` · **Privacy:** inputs, models and private policies stay out of Git. [Workstation test results and platform limits](docs/validation.md).
