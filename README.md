# Robot Learning Workshop

**Your video → human motion → robot motion. Training happens on workshop servers.**

[Watch the K1 cartwheel reference video](docs/examples/cartwheel_final_29999.mp4). A complete runnable [cartwheel example](examples/cartwheel) is included: policy, reference motion, K1 model and CSVs.

### ① Register

For video conversion, create **two separate accounts** at **[SMPL-X](https://smpl-x.is.tue.mpg.de/)** and **[SMPL](https://smpl.is.tue.mpg.de/)**. Accept the terms on both sites. You will enter both logins during step ③.

### ② Download

```bash
git clone https://github.com/ATR-Lab/robot-learning-workshop.git
cd robot-learning-workshop
```

### ③ Install

| Windows / Ubuntu · NVIDIA GPU | Mac · Apple Silicon |
| :--- | :--- |
| Install [Docker + GPU support](docs/docker.md). | Install [Homebrew](docs/macos.md) if needed. No Docker needed. |

`setup.sh` chooses automatically: **Mac → local `.venv` (GVHMR) and `.venv-sim` (MuJoCo); Linux / Windows WSL → Docker containers (GVHMR, GMR → CSV, MuJoCo).** Mac users use a workshop server for GMR → CSV. Docker keeps the dependencies inside containers instead of local Python environments.

Allow **20 GB free on Mac / 60 GB for Docker** as planning allowances, plus space for videos and outputs. Models alone are about **6 GB**. Check Docker's storage disk too (Windows: Docker Desktop/WSL storage). Old environment backups also use space.

**One command installs everything.** Have both accounts from step ① ready:
```bash
./setup.sh
```

It installs **GVHMR, GMR (Docker only), MuJoCo and their dependencies**, checks the GPU, asks for your **SMPL-X and SMPL logins** (answer **yes** for both, then enter each username/password), downloads the body models and checkpoints (about 6 GB) and a sample video, `data/inputs/tennis.mp4`. Allow 20–40 minutes the first time. It ends with a ✓ list and **`Ready`**:
```
  ✓ body model smplx
  ✓ body model smpl
  ✓ checkpoint gvhmr    (also hmr2, vitpose, yolo)
Ready. Try: ./workshop process data/inputs/tennis.mp4
```

No Docker login or container shell is needed. Run commands in your normal terminal from this folder; on Windows, use Ubuntu/WSL. Docker users do not activate a venv.

**If something is ✗ or a download failed:** rerun `./setup.sh`; it keeps what is already done. **Change accounts:** `./workshop auth`. **Check again:** `./workshop check`. Passwords are entered in the terminal and stored locally; do not put them in chat or Git. MuJoCo-only users can skip accounts: `./setup.sh --sim-only` → `./workshop demo`. `./setup.sh --deps-only` installs without logins or downloads.

**Already installed?** Run `git pull`, then `./setup.sh` again. On Mac it installs Python 3.12 if needed and repairs both environments; incompatible old environments are saved under `data/environment-backups/`. Inputs, outputs and saved logins are kept.

### ④ Convert video · GVHMR

**First, the sample** (one person, full body, stationary camera):
```bash
./workshop convert data/inputs/tennis.mp4
```

**Your own video:** copy it into `data/inputs/` (e.g. `data/inputs/dance.mp4`) and run `./workshop convert data/inputs/dance.mp4`. Use one person, full body visible, stationary camera. The cartwheel video above is a robot result, not a GVHMR input. The same command works on Mac and Docker; it converts to 30 fps and checks decoded frames automatically.

Human motion: **`data/outputs/<name>/gvhmr/hmr4d_results.pt`**, named after the video (`tennis.mp4` → `data/outputs/tennis/`). Logs are in its `logs/` directory. Replacing the input saves old results under `previous-*/` instead of reusing stale motion; those backups use extra disk space.

### ⑤ Retarget to K1 + export CSV · GMR

**Docker** — use the result from step ④:
```bash
./workshop retarget data/outputs/tennis/gvhmr/hmr4d_results.pt --clip tennis
```

Result: **`data/outputs/tennis/tennis.csv`**. Both steps at once: `./workshop process data/inputs/tennis.mp4`. Mac users send their `.pt` to the workshop team for this step. The team trains a policy on the server.

### ⑥ Run policy · MuJoCo

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

**Start over (Linux):** Docker writes some `data/` files as root, so plain `rm -rf` fails. Remove the folder with `docker run --rm -v "$PWD":/w ubuntu:24.04 rm -rf /w/data`, and the images with `docker rmi robot-learning-workshop:dev robot-learning-workshop-sim:dev`. Run `./workshop --help` for all commands.

**Update:** `git pull` · **Privacy:** inputs, models and private policies stay out of Git. [Workstation test results and platform limits](docs/validation.md).
