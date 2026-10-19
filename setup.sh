#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")"
[[ "$(uname -s)-$(uname -m)" == Linux-x86_64 ]] || { echo 'Docker workflow requires x86_64 Linux + NVIDIA RTX. See README for Mac.' >&2; exit 1; }
command -v nvidia-smi >/dev/null || { echo 'Install the NVIDIA driver first; see README.' >&2; exit 1; }
nvidia-smi
command -v docker >/dev/null || { echo 'Install Docker Engine, Compose and NVIDIA Container Toolkit; see README.' >&2; exit 1; }
docker info >/dev/null
docker compose version >/dev/null
if [[ -n "${WORKSHOP_IMAGE:-}" ]]; then
    docker compose pull
else
    docker compose build
fi
./workshop doctor
./workshop setup
