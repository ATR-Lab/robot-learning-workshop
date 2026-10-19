# Robot Learning Workshop

**Your video → human motion → robot motion**  
Powered by GVHMR + GMR. Training happens on workshop servers.

### ① Register

Create accounts at **[SMPL-X](https://smpl-x.is.tue.mpg.de/)** and **[SMPL](https://smpl.is.tue.mpg.de/)**. Accept the terms. Setup downloads the models after login.

### ② Download

```bash
git clone https://github.com/ATR-Lab/robot-learning-workshop.git
cd robot-learning-workshop
```

### ③ Choose your setup

| Windows / Ubuntu · NVIDIA GPU | Mac · Apple Silicon |
| :--- | :--- |
| Install [Docker + GPU support](docs/docker.md), then run `./setup.sh`. | Follow the [native Mac setup](docs/macos.md). No Docker needed. |

### ④ Run

Put a short, stationary-camera video in `data/inputs/clip.mp4`.

**Docker**
```bash
./workshop process data/inputs/clip.mp4
```

**Mac** · activate your environment first
```bash
gvhmr demo data/inputs/clip.mp4 -s --no-render -o data/outputs
```

Results: **`data/outputs/clip/`**. Send the clip's results to the workshop team for server processing and training.

---

**Update:** `git pull` · **Privacy:** videos, models and credentials stay out of Git.  
**Preview:** Docker GPU validation is pending. [Details & credits](docs/setup-details.md).
