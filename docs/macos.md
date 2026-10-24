# Mac requirements

Use **Apple Silicon** and **macOS 14+**. Install [Homebrew](https://brew.sh) if Python 3.12 is not installed; setup installs Python 3.12 through Homebrew automatically. No Docker or NVIDIA driver is needed.

[Return to the README](../README.md) and run `./setup.sh`. It installs GVHMR, MuJoCo, FFmpeg and the K1 model, asks for both logins and downloads the models and a sample video. Allow **20 GB free** as a planning allowance, plus video/output space; inference checkpoints and body models alone are about 6 GB.

**Before GVHMR:** register and accept terms separately at [SMPL-X](https://smpl-x.is.tue.mpg.de/) and [SMPL](https://smpl.is.tue.mpg.de/). `./setup.sh` asks for both: answer yes for both accounts and enter each login. Check model status with `./workshop check`. To log in again/change accounts, rerun `./workshop auth`; no reinstall is needed. Credentials stay in your local GVHMR config directory; never share them.

Already installed with another Python? Rerun `./setup.sh`. It saves incompatible environments under `data/environment-backups/` and creates separate Python 3.12 environments for GVHMR and MuJoCo. Existing data and saved logins are kept. Launchers select the correct environment automatically, even when another venv is active.

The README shows the three workflow steps and optional activation commands. For MuJoCo only, use `./setup.sh --sim-only`; no SMPL accounts are needed.

Use `./workshop convert data/inputs/clip.mp4` for automatic video preparation and conversion, `./workshop demo` for the included cartwheel, and `./workshop play <policy.onnx>` for your policy. These commands also work on the Docker setup. GMR → CSV still requires the NVIDIA/Linux server.
