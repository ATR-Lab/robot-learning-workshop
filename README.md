# Robot Learning Workshop

Video → human motion with **GVHMR** → grounded **Booster K1** motion with **GMR**.
Training runs on the workshop servers. This container prepares and exports motion only.

## Install before the workshop

1. Use **x86_64 Linux + an NVIDIA GPU** for Docker. Install the [NVIDIA driver](https://www.nvidia.com/en-us/drivers/), [Docker Engine and Compose](https://docs.docker.com/engine/install/ubuntu/), and [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html). Follow the toolkit's Docker configuration instructions. Check that `nvidia-smi` and `docker info` work.
2. Register at **[SMPL-X](https://smpl-x.is.tue.mpg.de/)** and **[SMPL](https://smpl.is.tue.mpg.de/)** separately, accept their terms, and have both logins ready. Setup downloads and places the models automatically.
3. Clone this repository using its GitHub Clone URL, open its folder, and run:

```bash
./setup.sh
```

Setup builds the image, checks CUDA, and prompts for the two model accounts. No host Python or Conda installation needed. Allow several GB for model downloads plus space for the Docker image. Credentials and models stay in your ignored `data/` folder; do not share that folder wholesale.

## Use

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

On Apple Silicon, keep using native GVHMR for Apple GPU acceleration; Docker on Mac does not provide CUDA. This Docker setup targets Linux + NVIDIA.

**Initial implementation: the image and full pipeline still need validation on an NVIDIA machine before the workshop.** Local orchestration tests do not exercise inference or retargeting.

## Credits

[Expressive Motion](https://github.com/ATR-Lab/expressive-motion) provides ground alignment and the K1 export pipeline (pinned at `a66e910d53da0d90eae845d35aad7c9eb2ae4a04`, with its GMR submodule). GVHMR pip fork: `1.6.1` (archived). Dependency snapshots are saved by `doctor`; transitive dependencies are not fully locked yet.

[GVHMR](https://github.com/zju3dv/GVHMR/blob/main/LICENSE) and SMPL/SMPL-X have research/non-commercial terms. Models and weights are downloaded for each participant and excluded from Git and the image. Upstream licenses apply. Only load trusted `.pt`/`.pkl` files.
