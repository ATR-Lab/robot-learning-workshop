# Docker requirements

**Windows:** install the NVIDIA Windows driver and [Docker Desktop with WSL 2 GPU support](https://docs.docker.com/desktop/features/gpu/). Enable integration with your Ubuntu WSL distro and keep Docker Desktop running. Use its Ubuntu terminal. Do not install a Linux display driver inside WSL.

**Ubuntu:** install the NVIDIA driver, [Docker Engine + Compose](https://docs.docker.com/engine/install/ubuntu/), and [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html), including its Docker configuration step.

[Return to the README](../README.md) and run `./setup.sh`. It builds the images, checks the GPU, and asks for your **SMPL/SMPL-X** logins. **No Docker account, `docker login`, venv activation or manual container shell is needed.**

The scripts start containers automatically; keep using the same terminal. For MuJoCo only, use `./setup.sh --sim-only`; no NVIDIA GPU or SMPL accounts are needed.
