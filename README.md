# Robot Learning Workshop

**Your video → human motion → K1 robot motion.** Training happens on the workshop servers.

## Quick start

Before you start: make two free accounts, at **[SMPL-X](https://smpl-x.is.tue.mpg.de/)** and at **[SMPL](https://smpl.is.tue.mpg.de/)**.
You need **[Docker + NVIDIA GPU](docs/docker.md)** (Linux, or Windows: [short guide](docs/windows.md), untested) or a **[Mac with Apple Silicon](docs/macos.md)**.

```bash
git clone https://github.com/ATR-Lab/robot-learning-workshop.git
cd robot-learning-workshop
./setup.sh                                 # install everything, asks for both logins
./workshop body data/inputs/tennis.mp4     # 1. video → body pose
./workshop robot tennis                    # 2. body pose → K1 robot
./workshop demo                            # watch the K1 cartwheel in simulation
```

Setup takes 20–40 minutes the first time and ends with **`Ready`**. Results go to **`data/outputs/tennis/`**:

| Step | You get |
| :--- | :--- |
| 1 · `body` | `tennis_pose.mp4`: the body pose over the video and in 3D |
| 2 · `robot` | `tennis.csv` (K1 motion, 30 Hz), `tennis_k1.mp4` (K1), `tennis_compare.mp4` (video beside the K1) |

Compare with the [expected result](examples/tennis).

## Your own video

Copy it to `data/inputs/` (one person, full body visible, camera not moving), then the same two steps:

```bash
./workshop body data/inputs/dance.mp4      # 1. → data/outputs/dance/dance_pose.mp4
./workshop robot dance                     # 2. → dance.csv, dance_k1.mp4, dance_compare.mp4
```

Videos are on by default; add **`--no-video`** to skip them. Both steps at once: `./workshop process data/inputs/dance.mp4`.

Send the `data/outputs/dance/` folder to the workshop team; they train the policy. Both steps run on Docker and natively on a Mac.

## Run a policy

```bash
./workshop play data/policies/policy.onnx
```

Mac opens a viewer (**Enter** restart, **Space** pause). Docker prints a browser link, normally **http://localhost:8080** → **Play**.

## Watch a motion (no policy)

```bash
./workshop motion examples/dances/gangnam_style     # 8 K1 dances in examples/dances
./workshop motion data/outputs/tennis/tennis.csv    # or your own result from step 2
```

Add `--record data/x.mp4` to save a video.

## If something goes wrong

| Problem | Fix |
| :--- | :--- |
| Setup shows ✗ or a download failed | Run `./setup.sh` again; it keeps what is done |
| SMPL login refused / body models missing | `./workshop auth`; the error says which account and why |
| Is everything ready? | `./workshop check` |
| Update to the latest version | `git pull`, then `./setup.sh` |
| Videos are slow or fail (e.g. Windows WSL 2) | They switch to CPU rendering automatically; `--no-video` skips them |
| All commands | `./workshop --help` |

Disk space: about **60 GB** with Docker, **20 GB** on Mac. Passwords stay on your computer; never put them in chat or Git.

**Play with the real tools** (GVHMR, GMR, MuJoCo options, other robots): [advanced guide](docs/advanced.md).

**More:** [setup details and troubleshooting](docs/setup-details.md) · [Docker install](docs/docker.md) · [Mac](docs/macos.md) · [tennis example result](examples/tennis) · [K1 dances](examples/dances) · [cartwheel example](examples/cartwheel) ([video](docs/examples/cartwheel_final_29999.mp4)) · [test results](docs/validation.md)
