# Robot Learning Workshop

Video → human motion (GVHMR) → Booster K1 motion (GMR) → policy training (BeyondMimic).
One Docker image contains the tools. Workshop scripts update with Git; videos, models and training results stay in `data/`.

**Status:** initial container implementation. Not yet built or validated on an RTX machine. Test one complete clip and training run before distributing to participants. No prebuilt image is published yet; the first setup builds locally and downloads large dependencies.

## Before the workshop

1. Use an **x86_64 Linux computer with NVIDIA RTX**. Recommended: 24 GB VRAM, 64 GB RAM and 150 GB free SSD space. Smaller GPUs may need fewer parallel environments.
2. Install the [NVIDIA driver](https://www.nvidia.com/en-us/drivers/), [Docker Engine + Compose](https://docs.docker.com/engine/install/ubuntu/) and [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html). Follow the toolkit guide's Docker configuration step. `nvidia-smi` and `docker info` must work for your user.
3. Register separately at **[SMPL-X](https://smpl-x.is.tue.mpg.de/)** and **[SMPL](https://smpl.is.tue.mpg.de/)** and accept their terms. Have both logins ready. The setup downloads and places the body models for you; do not send credentials to the organizer.
4. Read the [Isaac Sim EULA](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/common/licenses.html), [GVHMR license](https://github.com/zju3dv/GVHMR/blob/main/LICENSE) and the SMPL/SMPL-X terms. This workshop uses research/non-commercial assets.

## Install

Clone this repository using its GitHub Clone URL, then open its folder:

```bash
# After reviewing and accepting the applicable licenses:
printf 'ACCEPT_EULA=Y\n' > .env
./setup.sh
```

Setup builds the image, checks CUDA, and asks for your SMPL/SMPL-X logins. Models and credentials are stored only under your ignored `data/` folder. Checkpoint downloads can also happen on the first video run. No Conda or Python setup is needed on the host.

## Use

Copy a short video into `data/inputs/clip.mp4`. Start with one person fully visible and a stationary camera.

```bash
./workshop process data/inputs/clip.mp4
./workshop train clip --num-envs 1024 --max-iterations 10000
```

The first command writes recovered human motion, grounded robot motion, CSV and training NPZ under `data/outputs/clip/`. The second trains a K1 policy headlessly; logs/checkpoints are in `data/outputs/training/`. Training uses offline logging, so no W&B account is required. A successful training run does not establish hardware readiness.

```bash
./workshop doctor           # check GPU and dependencies
./workshop info             # GVHMR asset diagnostics
./workshop shell            # inspect the container
```

To reuse human motion already recovered on a Mac, copy `hmr4d_results.pt` into this repo and run:

```bash
./workshop retarget data/my-result/hmr4d_results.pt --clip clip
./workshop train clip --num-envs 1024
```

Only load `.pt`/`.pkl` files you produced or trust: these formats can contain executable Python objects.

## Updates

```bash
git pull
```

Script changes apply immediately. If Dockerfile/dependencies change, run `./workshop build`. Your `data/` remains. Organizers can publish a tested image and tell participants to export `WORKSHOP_IMAGE=registry/image:version` before `./setup.sh`, avoiding local builds.

## Mac

Keep the working native GVHMR installation for Apple GPU acceleration. The full Docker workshop, including Isaac Lab training, runs on Linux + RTX; connect from the Mac using SSH. Docker Desktop on Mac does not provide CUDA.

## Credits and versions

Uses [Expressive Motion](https://github.com/ATR-Lab/expressive-motion) at `a66e910d53da0d90eae845d35aad7c9eb2ae4a04`, including its pinned GMR and Booster submodules. GVHMR Python fork: `1.6.1`; Isaac Lab: `v2.3.2`; Isaac Sim: `5.1.0`. Dependency snapshots are written to `data/outputs/environment/` by `doctor`. The GVHMR pip fork is archived; keep this version fixed until a replacement is tested. Transitive Python dependencies are not fully locked yet.

Body models, pretrained weights, inputs and trained policies are excluded from Git and the built image. Upstream code/assets retain their own licenses. The Docker image includes Booster's BeyondMimic implementation for **K1**; other robots and mjlab require additional configuration.
