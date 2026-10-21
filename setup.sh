#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")"
[[ $# -eq 0 || ( $# -eq 1 && "$1" == --sim-only ) ]] || { echo 'Usage: ./setup.sh [--sim-only]' >&2; exit 1; }
if [[ "$(uname -s)" == Darwin ]]; then
    ./sim setup
    [[ "${1:-}" != --sim-only ]] || exit 0
    .venv-sim/bin/python -m venv .venv
    .venv/bin/python -m pip install 'setuptools<81' wheel 'numpy==1.26.4'
    .venv/bin/python -m pip install --no-build-isolation chumpy==0.70
    .venv/bin/python -m pip install 'gvhmr[preproc]==1.6.1'
    .venv/bin/gvhmr auth smpl
    .venv/bin/gvhmr info
    exit 0
fi
if [[ "${1:-}" == --sim-only ]]; then
    exec ./sim --docker setup
fi
[[ "$(uname -s)-$(uname -m)" == Linux-x86_64 ]] || { echo 'Docker workflow requires x86_64 Linux + NVIDIA RTX. See README for Mac.' >&2; exit 1; }
command -v nvidia-smi >/dev/null || { echo 'Install the NVIDIA driver first; see README.' >&2; exit 1; }
nvidia-smi
command -v docker >/dev/null || { echo 'Install Docker Engine, Compose and NVIDIA Container Toolkit; see README.' >&2; exit 1; }
docker info >/dev/null
docker compose version >/dev/null
if [[ -n "${WORKSHOP_IMAGE:-}" ]]; then
    docker compose pull workshop
    docker compose build sim
else
    docker compose build
fi
./workshop doctor
./workshop setup
