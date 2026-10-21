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

Setup also builds the CPU MuJoCo image and downloads the K1 model. Save a workshop export as `data/policies/policy.onnx`, then run:

```bash
./sim --docker play data/policies/policy.onnx
```

Open **http://localhost:8080** and press **Play**. Motion and settings are read automatically from the ONNX. To install simulation only, use `./setup.sh --sim-only`; this needs Docker but no NVIDIA GPU or SMPL accounts. Local files must be inside this repository so the container can read them.

[Back to the workshop](../README.md).
