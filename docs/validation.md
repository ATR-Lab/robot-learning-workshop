# Validation · 2026-10-21

Test machine: **Ubuntu 24.04 x86_64, Quadro RTX 6000 24 GB, NVIDIA driver 570.211.01, Docker 29.8.0, Compose 5.5.1, NVIDIA Container Toolkit 1.20.0**. Existing driver/runtime configuration was retained; other users' containers were not restarted.

| Check | Result |
| :--- | :--- |
| GPU in `docker run --rm --gpus all ubuntu:24.04 nvidia-smi` | Passed |
| Build workshop and simulation images | Passed |
| Rerun `./setup.sh --deps-only` | Passed; no account prompts |
| `./workshop doctor` | Both stage environments passed CUDA and dependency checks; GMR imported successfully |
| `./workshop info` | Both body models and the four required inference checkpoints available in persistent `data/` paths |
| Full `./workshop process` on upstream tennis sample | Passed: 312 frames at 30 fps → K1 motion → CSV |
| Separate `convert` rerun and `retarget` commands | Passed; existing preprocessing reused for identical input; both CSVs have 312 rows × 29 finite values |
| MuJoCo cartwheel, native Linux and Docker headless | Completed 10.24 seconds without falling |
| Docker browser viewer | HTTP 200; automatically selected 8081 because 8080 was occupied |
| Docker video rendering | Valid 320×240 MP4, 513 frames |
| Script tests | 25 passed on Mac and workstation |

The workshop image uses Python 3.11 and Torch 2.7.0+cu128. GVHMR and GMR keep separate stage packages and share that pinned Torch/CUDA stack. Simulation uses Python 3.12, MuJoCo 3.16.0 and ONNX Runtime 1.31.0. Image sizes reported by Docker: approximately **11.1 GB workshop + 1.0 GB simulation**, excluding model files and build/download cache. The **60 GB free-space allowance** in the guide includes build headroom, about 6 GB of model files and outputs; it is not a measured minimum.

## Reproduce

Install [Docker + NVIDIA prerequisites](docker.md), clone the repository, then run:

```bash
./setup.sh --deps-only
./workshop auth
mkdir -p data/inputs
curl -fL https://raw.githubusercontent.com/zju3dv/GVHMR/ee960bb6e2ea2d381aa97f08e9b71ef320b624b1/docs/example_video/tennis.mp4 -o data/inputs/tennis.mp4
./workshop convert data/inputs/tennis.mp4
./workshop retarget data/outputs/tennis/gvhmr/hmr4d_results.pt --clip tennis
./workshop demo --check
```

Human motion: `data/outputs/tennis/gvhmr/hmr4d_results.pt`; CSV: `data/outputs/tennis/tennis.csv`. For the combined conversion/retargeting command: `./workshop process data/inputs/tennis.mp4`.

## Scope and limits

- GPU inference and retargeting were also checked directly on the workstation as diagnostics, independently of the Docker run. The published Linux workflow remains Docker.
- Existing licensed body-model files and checkpoint files were reused for these runs. The auth command routing is tested, but fresh MPI account registration/password validation was not repeated. Users must register and accept terms on both sites themselves.
- Mac environments/launchers, dependency checks and cartwheel playback were tested. 2026-10-24, Apple Silicon: `./setup.sh` installed GVHMR, GMR and MuJoCo natively; an 8-second 1280×720 shadowboxing clip ran through `convert` (about 3 minutes on the Apple GPU, with `_pose.mp4`) and `retarget` (seconds, with `_k1.mp4` and `_compare.mp4`).
- Windows/WSL2 instructions follow the linked official documentation; Windows execution has not been tested. Expected risk: GPU EGL rendering inside the container; the CUDA motion steps should run. Videos fall back to CPU rendering (Mesa llvmpipe) automatically; that fallback was verified on the workstation with `WORKSHOP_SOFTWARE_GL=1` (all three videos, 2m15s vs 1m39s for the 8-second clip).
- Missing-frame metadata has a decoded-frame-count fallback, tested with a fragmented MP4 and the zero-count case. The original `dance.mp4` from the reported failure was not available for testing.
- A successful pipeline check verifies execution and output structure; motion quality depends on the input video and policy.

Test logs and participant outputs stay under ignored `data/outputs/`; no credentials or licensed body models are published in Git.
