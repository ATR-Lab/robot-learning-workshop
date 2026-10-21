# Robot Learning Workshop

**Your video → human motion → robot motion. Training happens on workshop servers.**

### ① Register

Create accounts at **[SMPL-X](https://smpl-x.is.tue.mpg.de/)** and **[SMPL](https://smpl.is.tue.mpg.de/)**. Accept the terms. Setup downloads the models after login.

### ② Download

```bash
git clone https://github.com/ATR-Lab/robot-learning-workshop.git
cd robot-learning-workshop
```

### ③ Choose your setup

| Windows / Ubuntu · NVIDIA GPU | Mac · Apple Silicon |
| :--- | :--- |
| Install [Docker + GPU support](docs/docker.md), then run `./setup.sh`. | Follow the [native Mac setup](docs/macos.md). No Docker needed. |

Run all commands below from this repository's folder.

### ④ Convert video · GVHMR

Put a short **30 fps** video in `data/inputs/clip.mp4`: one person, full body visible, stationary camera.

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

[Example policies and more details](docs/setup-details.md#mujoco-policy-playback). Example videos/policies are not bundled in this repository.

**Update:** `git pull` · **Privacy:** inputs, models and private policies stay out of Git. Docker runtime validation is pending.
