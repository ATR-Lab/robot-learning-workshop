# Docker setup

## Windows

Install the NVIDIA Windows driver and [Docker Desktop with WSL 2 GPU support](https://docs.docker.com/desktop/features/gpu/). Enable Docker Desktop integration with your Ubuntu WSL distro. Run workshop commands inside that Ubuntu terminal with Docker Desktop running. Do not install a Linux NVIDIA display driver inside WSL.

## Ubuntu

Use an NVIDIA GPU. Install these in order:

1. [NVIDIA driver](https://www.nvidia.com/en-us/drivers/).
2. [Docker Engine and Compose](https://docs.docker.com/engine/install/ubuntu/).
3. [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html). Complete its Docker configuration step too.

Check that these commands work:

```bash
nvidia-smi
docker info
```

Then, from the workshop folder:

```bash
./setup.sh
```

Enter your SMPL-X and SMPL logins when prompted. Setup builds the container and checks GPU access. Models and results stay in `data/` between runs.

Setup also builds the CPU MuJoCo image. Play a trained policy with `./sim --docker play "POLICY_ZIP_OR_URL"`, then open **http://localhost:8080** and press **Play**. Local ZIPs must be inside this repository (for example `data/policies/k1.zip`). To install simulation only, use `./setup.sh --sim-only`; this needs Docker but no NVIDIA GPU or SMPL accounts.

[Back to the workshop](../README.md).
