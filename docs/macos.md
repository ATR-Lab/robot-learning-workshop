# Mac requirements

Use **Apple Silicon** and **macOS 14+**. Install [Homebrew](https://brew.sh) if Python 3.12 is not installed; setup installs Python 3.12 through Homebrew automatically. No Docker or NVIDIA driver is needed.

[Return to the README](../README.md) and run `./setup.sh`. It installs GVHMR, MuJoCo, FFmpeg and the K1 model, then asks for your SMPL/SMPL-X logins.

Already installed with another Python? Rerun `./setup.sh`. It saves incompatible environments under `data/environment-backups/` and creates separate Python 3.12 environments for GVHMR and MuJoCo. Existing data and saved logins are kept. Use `./gvhmr` and `./sim` to select the correct environment automatically, even when another venv is active.

The README shows the three workflow steps and optional activation commands. For MuJoCo only, use `./setup.sh --sim-only`; no SMPL accounts are needed.

Use `./workshop convert data/inputs/clip.mp4` for automatic video preparation and conversion, `./workshop demo` for the included cartwheel, and `./workshop play <policy.onnx>` for your policy. These commands also work on the Docker setup. GMR → CSV still requires the NVIDIA/Linux server.
