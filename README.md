# Robot Learning Workshop

**Your video → human motion → K1 robot motion.** Training happens on the workshop servers.

## Quick start

Before you start: make two free accounts, at **[SMPL-X](https://smpl-x.is.tue.mpg.de/)** and at **[SMPL](https://smpl.is.tue.mpg.de/)**.
You need **[Docker + NVIDIA GPU](docs/docker.md)** (Linux; Windows WSL 2 is [untested](docs/docker.md#windows--docker-desktop--wsl2)) or a **[Mac with Apple Silicon](docs/macos.md)**.

```bash
git clone https://github.com/ATR-Lab/robot-learning-workshop.git
cd robot-learning-workshop
./setup.sh                                     # installs everything, asks for both logins
./workshop process data/inputs/tennis.mp4      # sample video → K1 motion
./workshop demo                                # watch the K1 cartwheel in simulation
```

Setup takes 20–40 minutes the first time and ends with **`Ready`**. `process` saves in **`data/outputs/tennis/`**: `tennis.csv` (K1 motion) plus videos: `tennis_pose.mp4` (body pose), `tennis_k1.mp4` (K1) and `tennis_compare.mp4` (video beside the K1). Compare with the [expected result](examples/tennis).

## Your own video · two steps

Copy it to `data/inputs/` (one person, full body visible, camera not moving), then:

```bash
./workshop convert data/inputs/dance.mp4       # 1. video → body pose     → dance_pose.mp4
./workshop retarget dance                      # 2. body pose → K1 robot   → dance.csv, dance_k1.mp4, dance_compare.mp4
```

Results are in `data/outputs/dance/`. `./workshop process data/inputs/dance.mp4` runs both steps. Videos are on by default; add **`--no-video`** to any of these commands to skip them.

Send the `data/outputs/dance/` folder to the workshop team; they train the policy. Both steps run on Docker and natively on a Mac.

## Run a policy

```bash
./workshop play data/policies/policy.onnx
```

Mac opens a viewer (**Enter** restart, **Space** pause). Docker prints a browser link, normally **http://localhost:8080** → **Play**.

## If something goes wrong

| Problem | Fix |
| :--- | :--- |
| Setup shows ✗ or a download failed | Run `./setup.sh` again; it keeps what is done |
| Wrong SMPL login | `./workshop auth` |
| Is everything ready? | `./workshop check` |
| Update to the latest version | `git pull`, then `./setup.sh` |
| A video step fails (e.g. on Windows WSL 2) | Add `--no-video` |
| All commands | `./workshop --help` |

Disk space: about **60 GB** with Docker, **20 GB** on Mac. Passwords stay on your computer; never put them in chat or Git.

**Play with the real tools** (GVHMR, GMR, MuJoCo options, other robots): [advanced guide](docs/advanced.md).

**More:** [setup details and troubleshooting](docs/setup-details.md) · [Docker install](docs/docker.md) · [Mac](docs/macos.md) · [tennis example result](examples/tennis) · [cartwheel example](examples/cartwheel) ([video](docs/examples/cartwheel_final_29999.mp4)) · [test results](docs/validation.md)
