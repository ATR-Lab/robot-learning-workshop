#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")"
ROOT="$PWD"
source "$ROOT/scripts/python-env.sh"
[[ $# -eq 0 || ( $# -eq 1 && "$1" == --sim-only ) ]] || { echo 'Usage: ./setup.sh [--sim-only]' >&2; exit 1; }
mkdir -p data/inputs data/outputs data/policies
if [[ "$(uname -s)" == Darwin ]]; then
    ./sim setup
    [[ "${1:-}" != --sim-only ]] || exit 0
    WORKSHOP_PYTHON="$ROOT/.venv-sim/bin/python"
    ensure_python312_env "$ROOT/.venv"
    .venv/bin/python -m pip install 'setuptools<81' wheel 'numpy==1.26.4'
    .venv/bin/python -m pip install --no-build-isolation chumpy==0.70
    .venv/bin/python -m pip install 'gvhmr[preproc]==1.6.1'
    .venv/bin/python -m pip check
    if [[ -f "${XDG_CONFIG_HOME:-$HOME/.config}/gvhmr/smpl_credentials.toml" ]]; then
        echo 'Keeping saved SMPL/SMPL-X logins. To change them: ./gvhmr auth smpl --no-fetch'
    else
        .venv/bin/gvhmr auth smpl
    fi
    .venv/bin/gvhmr info
    echo 'Ready. Convert: ./gvhmr demo data/inputs/clip.mp4 -s --no-render -o data/outputs'
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
if [[ -f data/home/.config/gvhmr/smpl_credentials.toml ]]; then
    echo 'Keeping saved SMPL/SMPL-X logins. To change them: ./workshop setup'
    ./workshop info
else
    ./workshop setup
fi
