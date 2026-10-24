# Docker + NVIDIA setup

Use **x86_64 Linux + NVIDIA**, or **Ubuntu in Windows WSL2 + Docker Desktop**. Run workshop commands in the Linux/Ubuntu terminal. No Docker account or `docker login` is needed.

Allow **60 GB free** for a first full installation: images, build cache, models and outputs. This is a planning allowance, not a measured minimum. Check the project disk **and Docker's storage disk**. Models alone are about **6 GB**; videos and backups need extra space.

## Ubuntu · install Docker

Install your NVIDIA driver using Ubuntu's **Software & Updates → Additional Drivers**, then reboot. Continue when `nvidia-smi` lists your GPU. A separate host CUDA Toolkit is not required.

Skip this section if Docker Engine and Compose already work. On a new Ubuntu installation:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources > /dev/null <<EOF_DOCKER
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF_DOCKER
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

**Log out and back in**, or reconnect SSH. `docker info` must work **without sudo**. Docker-group membership grants administrator-level access through Docker; only add trusted users. If distro Docker packages conflict, follow [Docker's removal instructions](https://docs.docker.com/engine/install/ubuntu/#uninstall-old-versions) first.

## Ubuntu · install Toolkit and register NVIDIA runtime

Installing Toolkit alone is not enough: register it with Docker. On a shared workstation, coordinate the restart because it can interrupt containers.

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor --yes -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

Verify **before installing workshop dependencies**:

```bash
nvidia-smi
docker info
docker compose version
docker run --rm --gpus all ubuntu:24.04 nvidia-smi
df -h . /var/lib/docker
```

The container must list your GPU. `permission denied` on `docker.sock`: reconnect after the group change. `could not select device driver`: check Toolkit installation and runtime registration. If Docker uses a custom storage directory, check that disk instead of `/var/lib/docker` (`Docker Root Dir` in `docker info`).

## Windows · Docker Desktop + WSL2

1. Install/update the **Windows NVIDIA driver**. In administrator PowerShell: `wsl --install -d Ubuntu`, then `wsl --update`; restart if prompted.
2. Install [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/). Enable **Use the WSL 2 based engine** and **Resources → WSL Integration → Ubuntu**. Keep Desktop running.
3. In the **Ubuntu terminal**, run `docker info`, `docker compose version`, and `docker run --rm --gpus all ubuntu:24.04 nvidia-smi`.

With Docker Desktop's WSL backend, skip Ubuntu's Engine/Toolkit commands above: Desktop manages the engine and GPU integration. Do not install a Linux NVIDIA display driver inside WSL. Allocate enough storage to Docker Desktop/WSL as well as to the project. Clone into `~/robot-learning-workshop` inside Ubuntu.

## Install everything

Register first and accept the terms at **both [SMPL-X](https://smpl-x.is.tue.mpg.de/) and [SMPL](https://smpl.is.tue.mpg.de/)**. These are separate accounts/licenses; do not assume one login covers both. Then, from the cloned repository:

```bash
./setup.sh
```

This builds the separate **GVHMR, GMR and MuJoCo** images, checks the GPU, asks for both logins (answer **yes for both**), downloads the body models, the inference checkpoints (about 6 GB) and the sample `data/inputs/tennis.mp4`, and ends with a ✓ list and `Ready`. No local Python/Conda or venv activation is needed. Rerunning it keeps what is already done; to update: `git pull`, then `./setup.sh`. `./workshop check` repeats the ✓ list. `./workshop info` shows GVHMR's full table, where DPVO and the data packs stay ✗ (not needed); ignore its `gvhmr download` hint, use `./workshop download`.

**Change accounts / log in again:** rerun `./workshop auth` and configure both accounts. Credentials persist in ignored `data/home/`; inference weights in `data/checkpoints/`, body models in `data/body_models/`, and download caches in `data/cache/`. Do not share those folders wholesale. No container login or `docker login` is involved.

For MuJoCo only: `./setup.sh --sim-only`, then `./workshop demo`. No NVIDIA GPU or body-model accounts are needed for this option. Open the printed browser URL (normally port 8080; Linux auto-selects the next free port). Override with `SIM_PORT=8081 ./workshop demo`. Over SSH, forward the chosen port: `ssh -L 8081:localhost:8081 user@server`, then open http://localhost:8081 locally.

[Return to the short workflow](../README.md). Official references: [Docker Engine](https://docs.docker.com/engine/install/ubuntu/), [Docker group setup](https://docs.docker.com/engine/install/linux-postinstall/), [NVIDIA Toolkit/runtime](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html), [Windows GPU support](https://docs.docker.com/desktop/features/gpu/).
