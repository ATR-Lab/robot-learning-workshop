# Robot Learning Workshop

**Your video → human motion → robot motion. Training happens on workshop servers.**

[Watch the K1 cartwheel reference video](docs/examples/cartwheel_final_29999.mp4) — an example MuJoCo result.

### ① Register

For video conversion, create accounts at **[SMPL-X](https://smpl-x.is.tue.mpg.de/)** and **[SMPL](https://smpl.is.tue.mpg.de/)**. Accept the terms. Setup asks for these logins and downloads the models.

### ② Download

```bash
git clone https://github.com/ATR-Lab/robot-learning-workshop.git
cd robot-learning-workshop
```

### ③ Choose your setup

| Windows / Ubuntu · NVIDIA GPU | Mac · Apple Silicon |
| :--- | :--- |
| Install [Docker + GPU support](docs/docker.md). | Install [Python 3.12](docs/macos.md). No Docker needed. |

Then, on either setup:
```bash
./setup.sh
```

No Docker login or container shell is needed. Run commands in your normal terminal; on Windows, use Ubuntu/WSL. Docker users do not activate a venv.

Run all commands below from this repository's folder.

### ④ Convert video · GVHMR

Put a short **30 fps** video in `data/inputs/clip.mp4`: one person, full body visible, stationary camera.
For a Docker test, [download GVHMR's tennis clip](https://raw.githubusercontent.com/zju3dv/GVHMR/ee960bb6e2ea2d381aa97f08e9b71ef320b624b1/docs/example_video/tennis.mp4) and save it at that path; Docker converts its 60 fps to 30 fps. The cartwheel video above is a robot result, not a GVHMR input.

**Mac**
```bash
source .venv/bin/activate
gvhmr demo data/inputs/clip.mp4 -s --no-render -o data/outputs
```

**Docker**
```bash
./workshop convert data/inputs/clip.mp4
```

Human motion: Mac → `data/outputs/clip/hmr4d_results.pt`; Docker → `data/outputs/clip/gvhmr/hmr4d_results.pt`.

### ⑤ Retarget to K1 + export CSV · GMR

**Docker** — use the result from step ④:
```bash
./workshop retarget data/outputs/clip/gvhmr/hmr4d_results.pt --clip clip
```

Result: **`data/outputs/clip/clip.csv`**. Mac users send their `.pt` to the workshop team for this step. The team trains a policy on the server.

### ⑥ Run policy · MuJoCo

Save the workshop policy as **`data/policies/policy.onnx`**. Setup prepares K1 automatically; the workshop ONNX supplies its settings and motion.

**Mac**
```bash
source .venv-sim/bin/activate
./sim play data/policies/policy.onnx
```
**Enter** restarts; **Space** pauses.

**Docker**
```bash
./sim --docker play data/policies/policy.onnx
```
Open **http://localhost:8080** and press **Play**.

[Example policies and more details](docs/setup-details.md#mujoco-policy-playback). Policy weights are provided separately.

**Update:** `git pull` · **Privacy:** inputs, models and private policies stay out of Git. Docker runtime validation is pending.
