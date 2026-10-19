# Robot Learning Workshop

Turn a video into human and robot motion with **GVHMR + GMR**. Training runs on our servers.

## 1. Create two accounts

Register at **[SMPL-X](https://smpl-x.is.tue.mpg.de/)** and **[SMPL](https://smpl.is.tue.mpg.de/)**. Accept the terms and keep both logins ready. Setup downloads the models for you.

## 2. Download the workshop

```bash
git clone https://github.com/ATR-Lab/robot-learning-workshop.git
cd robot-learning-workshop
```

## 3. Choose your setup

### Windows or Ubuntu · Docker

Install **Docker** and the NVIDIA GPU support for your system: [Windows instructions](https://docs.docker.com/desktop/features/gpu/) · [Ubuntu instructions](docs/docker.md).

On Windows, run the commands below in your **Ubuntu WSL 2 terminal** with Docker Desktop running.

```bash
./setup.sh
```

Enter your SMPL-X and SMPL logins when asked. First setup downloads large files.

Put your video in `data/inputs/clip.mp4`, then run:

```bash
./workshop process data/inputs/clip.mp4
```

### Mac · Native installation

No Docker needed. Follow the **[Mac instructions](docs/macos.md)**.

## 4. Send your results

Start with a short video of one person, full body visible, with a stationary camera. Results appear in `data/outputs/clip/`. Follow the workshop team's instructions to send that clip's results for server training.

Videos, models and credentials stay local and are excluded from Git. To get new scripts, run `git pull`.

**Status:** Docker still needs validation on an NVIDIA machine before the workshop. [Technical details and credits](docs/setup-details.md).
