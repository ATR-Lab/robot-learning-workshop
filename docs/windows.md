# Windows · quick guide (WSL 2 + Docker Desktop)

Needs an NVIDIA GPU. Not yet tested on Windows: if a step fails, send the output to the organizers.

**1. Windows, once**
- Install the latest **NVIDIA driver for Windows**. Do not install a Linux NVIDIA driver or the NVIDIA Container Toolkit inside WSL.
- PowerShell **as Administrator**:
  ```
  wsl --install -d Ubuntu
  wsl --set-default Ubuntu
  wsl -l -v
  ```
  Ubuntu must have the `*` and VERSION `2`. Restart if asked.
- Install [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/). Settings → General → **Use the WSL 2 based engine**; Resources → WSL Integration → **Ubuntu** on → Apply & restart. Keep it running.

**2. Ubuntu** (Start → Ubuntu, or `wsl -d Ubuntu`; the prompt looks like `user@PC:~$`)
```
docker run --rm --gpus all ubuntu:24.04 nvidia-smi     # must show your GPU
cd ~
git clone https://github.com/ATR-Lab/robot-learning-workshop.git
cd robot-learning-workshop
./setup.sh                                             # 20–40 min; answer yes to both SMPL logins
./workshop body data/inputs/tennis.mp4                 # 1. video → body pose
./workshop robot tennis                                # 2. body pose → K1
./workshop demo                                        # open the printed link in your Windows browser → Play
```

Results: `data/outputs/tennis/`. Open the folder in Windows: `explorer.exe data/outputs/tennis`.

**If something goes wrong**

| Problem | Fix |
| :--- | :--- |
| `wsl` opens `docker-desktop` instead of Ubuntu | `wsl --set-default Ubuntu` |
| `docker: command not found` in Ubuntu | Docker Desktop running, WSL Integration → Ubuntu on; then `wsl --shutdown` in PowerShell and reopen Ubuntu |
| `nvidia-smi` test shows no GPU | Update the Windows NVIDIA driver and Docker Desktop |
| Videos slow | Normal on WSL: they render on the CPU. `--no-video` skips them |

Keep the repository in the Ubuntu home folder (`~`), not under `/mnt/c`: it is much faster. Docker needs about 25 GB free.
