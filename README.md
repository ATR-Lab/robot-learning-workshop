# Robot Learning Workshop

**Video → human motion (GVHMR) → K1 motion (GMR) → server training → policy in MuJoCo.**

### Install once

**Mac:** [Python 3.12, Apple Silicon, macOS 14+](docs/macos.md). **Ubuntu / Windows WSL:** [Docker + NVIDIA setup](docs/docker.md).
For video conversion, register at [SMPL-X](https://smpl-x.is.tue.mpg.de/) and [SMPL](https://smpl.is.tue.mpg.de/) and accept their terms. Setup asks for these logins.

```bash
git clone https://github.com/ATR-Lab/robot-learning-workshop.git
cd robot-learning-workshop
./setup.sh
```

Run all commands below from `robot-learning-workshop/`. Setup creates the `data/` folders. For MuJoCo only, use `./setup.sh --sim-only`; no SMPL accounts or NVIDIA GPU needed.

### 1 · Convert video → human motion (GVHMR)

Save your video as **`data/inputs/clip.mp4`**: one person, full body visible, stationary camera, 30 fps.

**Mac** — activate the video environment:
```bash
source .venv/bin/activate
gvhmr demo data/inputs/clip.mp4 -s --no-render -o data/outputs
```
Output: `data/outputs/clip/hmr4d_results.pt`.

**Ubuntu / Windows WSL** — Docker handles the environment:
```bash
./workshop convert data/inputs/clip.mp4
```
Output: `data/outputs/clip/gvhmr/hmr4d_results.pt`.

### 2 · Retarget human motion → Booster K1 (GMR)

**On the NVIDIA Docker setup**, use the output from step 1:
```bash
./workshop retarget data/outputs/clip/gvhmr/hmr4d_results.pt --clip clip
```
Output: `data/outputs/clip/clip.csv` and a robot-motion `.pkl`.

**Mac:** send `data/outputs/clip/hmr4d_results.pt` to the workshop team; they run GMR on the server. If retargeting a Mac result in your own NVIDIA setup, copy it to `data/inputs/hmr4d_results.pt` and substitute that path in the command above.

Send the clip's output folder to the team for **policy training**. They return a policy bundle. The motion `.pt`/`.csv` from these steps is not a trained policy.

### 3 · Run a trained policy in MuJoCo

Save the **complete policy ZIP** from the workshop team as **`data/policies/k1.zip`**. Keep it zipped. The current player needs the ONNX, matching settings, reference motion and robot model together.

**Mac** — activate the simulation environment:
```bash
source .venv-sim/bin/activate
./sim play data/policies/k1.zip
```
A MuJoCo window opens. **Enter** restarts; **Space** pauses.

**Ubuntu / Windows WSL:**
```bash
./sim --docker play data/policies/k1.zip
```
Open **http://localhost:8080** and click **Play**. **Reset** restarts.

A complete bundle **folder** or a **direct ZIP download URL** also works instead of `data/policies/k1.zip`.

### Example

If you have the supplied cartwheel folder in Downloads, run on Mac:
```bash
./sim play ~/Downloads/Booster-K1-Cartwheel-MuJoCo
```
K1 starts standing, performs a cartwheel and returns to standing. This example passed the headless Mac check. **The example bundle and a demo input video are not included in this repository**; get the bundle from the workshop team, or use your own video for step 1.

**Update:** `git pull` · [More details](docs/setup-details.md) · Docker inference and the simulation container still need runtime validation. Videos, licensed models and private policy bundles stay out of Git.
