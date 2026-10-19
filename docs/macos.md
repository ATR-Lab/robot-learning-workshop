# macOS · Apple Silicon

Install Python **3.11 or newer**, and register separately at [SMPL-X](https://smpl-x.is.tue.mpg.de/) and [SMPL](https://smpl.is.tue.mpg.de/). Accept their terms and keep both logins ready.

From the workshop repository:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install setuptools wheel
python -m pip install --no-build-isolation chumpy==0.70
python -m pip install 'gvhmr[preproc]==1.6.1'
gvhmr auth smpl
gvhmr info
```

`auth smpl` downloads the body models using your accounts; no manual file placement. Device diagnostics should show `mps` for Apple GPU acceleration. Additional weights download on first use.

Put a short, stationary-camera video with one person fully visible in `data/inputs/clip.mp4`:

```bash
mkdir -p data/inputs data/outputs
# Copy your video to data/inputs/clip.mp4, then:
gvhmr demo data/inputs/clip.mp4 -s --no-render -o data/outputs
```

For overlay videos, run without `--no-render`:

```bash
gvhmr demo data/inputs/clip.mp4 -s -o data/outputs
open data/outputs/clip
```

Send `data/outputs/clip/hmr4d_results.pt` to the workshop server using the organizer's transfer instructions. Server-side GMR prepares the robot motion; policy training also runs there. Native GMR installation is not part of these Mac instructions.

On subsequent terminal sessions, activate the environment with `source .venv/bin/activate`. No Docker or NVIDIA drivers are needed. This path was exercised with GVHMR on an Apple Silicon laptop; performance depends on the laptop and clip.
