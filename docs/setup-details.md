# Robot Learning Workshop

Video → human motion with **GVHMR** → grounded **Booster K1** motion with **GMR**.
Training runs on the workshop servers. This container prepares and exports motion only.

## Before you start

Register separately at **[SMPL-X](https://smpl-x.is.tue.mpg.de/)** and **[SMPL](https://smpl.is.tue.mpg.de/)**, accept their terms, and keep both logins ready. The software downloads and places the models after login.

```bash
git clone https://github.com/ATR-Lab/robot-learning-workshop.git
cd robot-learning-workshop
```

## Option 1 · Docker on Windows or Ubuntu

Use an NVIDIA GPU. On **Ubuntu**, install the [NVIDIA driver](https://www.nvidia.com/en-us/drivers/), [Docker Engine and Compose](https://docs.docker.com/engine/install/ubuntu/), and [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html), including its Docker configuration step.

On **Windows**, install the NVIDIA Windows driver and [Docker Desktop with WSL 2](https://docs.docker.com/desktop/features/wsl/). Enable integration with your Ubuntu WSL distro, and run all workshop commands inside its Ubuntu terminal. Do not install a Linux NVIDIA display driver inside WSL. See [Docker GPU prerequisites](https://docs.docker.com/desktop/features/gpu/).

Check `nvidia-smi` and `docker info`, then run:

```bash
./setup.sh
```

Setup builds the image, checks CUDA, and asks for your SMPL/SMPL-X logins. No host Python or Conda installation needed. Allow several GB for models plus space for the Docker image. Credentials and models stay in ignored `data/`; do not share that folder wholesale.

## Option 2 · macOS (Apple Silicon)

Run GVHMR natively using the Apple GPU. Follow [the Mac instructions](macos.md). Docker is not required for this option. Retargeting and training can run on workshop servers.

## Use Docker

Put a short video in `data/inputs/clip.mp4`: one person, full body visible, stationary camera.

```bash
./workshop process data/inputs/clip.mp4
```

Results are in `data/outputs/clip/`: human-motion `gvhmr/hmr4d_results.pt`, robot-motion `robot_data/booster_k1/clip_booster_k1.pkl`, `clip.csv`, staged video and logs. Send **only this clip's output folder** to the workshop server using the organizer's transfer instructions. The server handles training-format conversion and policy training.

Already recovered motion on your Mac? Copy the trusted 30 fps result into `data/` and run:

```bash
./workshop retarget data/my-result/hmr4d_results.pt --clip clip
```

Other commands:

```bash
./workshop doctor           # GPU and dependency checks
./workshop info             # model/download status
./workshop shell            # container shell
```

## Update

Run `git pull` for new workshop scripts. Run `./workshop build` only when dependencies/Dockerfile change. Data persists between containers. Organizers can distribute a tested image using `WORKSHOP_IMAGE=registry/image:version ./setup.sh` to avoid participant builds; no prebuilt image is published yet.

## Mac and status

On Apple Silicon, keep using native GVHMR for Apple GPU acceleration; Docker on Mac does not provide CUDA. This Docker setup targets Linux + NVIDIA, including Ubuntu under WSL 2.

**Initial implementation: the image and full pipeline still need validation on an NVIDIA machine before the workshop.** Local orchestration tests do not exercise inference or retargeting. Windows/WSL 2 is also pending validation.

## Credits

[Expressive Motion](https://github.com/ATR-Lab/expressive-motion) provides ground alignment and the K1 export pipeline (pinned at `a66e910d53da0d90eae845d35aad7c9eb2ae4a04`, with its GMR submodule). GVHMR pip fork: `1.6.1` (archived). Dependency snapshots are saved by `doctor`; transitive dependencies are not fully locked yet.

[GVHMR](https://github.com/zju3dv/GVHMR/blob/main/LICENSE) and SMPL/SMPL-X have research/non-commercial terms. Models and weights are downloaded for each participant and excluded from Git and the image. Upstream licenses apply. Only load trusted `.pt`/`.pkl` files.
