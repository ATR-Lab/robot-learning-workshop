#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")"
ROOT="$PWD"
source "$ROOT/scripts/python-env.sh"
[[ $# -eq 0 || ( $# -eq 1 && ( "$1" == --sim-only || "$1" == --deps-only ) ) ]] || { echo 'Usage: ./setup.sh [--deps-only | --sim-only]' >&2; exit 1; }
mkdir -p data/inputs data/outputs data/policies
if [[ "$(uname -s)" == Darwin ]]; then
    ./sim setup
    [[ "${1:-}" != --sim-only ]] || exit 0
    if ! command -v ffmpeg >/dev/null || ! command -v ffprobe >/dev/null; then
        brew_cmd="$(command -v brew || true)"
        [[ -n "$brew_cmd" || ! -x /opt/homebrew/bin/brew ]] || brew_cmd=/opt/homebrew/bin/brew
        [[ -n "$brew_cmd" ]] || { echo 'Install Homebrew (https://brew.sh), then rerun ./setup.sh to install FFmpeg.' >&2; exit 1; }
        "$brew_cmd" install ffmpeg
        export PATH="$("$brew_cmd" --prefix)/bin:$PATH"
    fi
    WORKSHOP_PYTHON="$ROOT/.venv-sim/bin/python"
    ensure_python312_env "$ROOT/.venv"
    .venv/bin/python -m pip install 'setuptools<81' wheel 'numpy==1.26.4'
    .venv/bin/python -m pip install --no-build-isolation chumpy==0.70
    .venv/bin/python -m pip install 'gvhmr[preproc]==1.6.1'
    .venv/bin/python -m pip check
    # Step 2 (GMR): the same pinned pipeline as the Docker image, in its own environment.
    commit="$(sed -n 's/^ARG EXPRESSIVE_COMMIT=//p' Dockerfile)"
    if [[ "$(git -C .pipeline rev-parse HEAD 2>/dev/null)" != "$commit" ]]; then
        [[ -d .pipeline/.git ]] || git clone https://github.com/ATR-Lab/expressive-motion.git .pipeline
        git -C .pipeline fetch -q origin
        git -C .pipeline checkout -q "$commit"
        git -C .pipeline submodule update --init --recursive external/GMR
    fi
    ensure_python312_env "$ROOT/.venv-gmr"
    .venv-gmr/bin/python -m pip install 'setuptools<81' wheel toml cython 'numpy==1.26.4'
    .venv-gmr/bin/python -m pip install --no-build-isolation chumpy==0.70
    .venv-gmr/bin/python -m pip install --no-build-isolation -e .pipeline/external/GMR 'numpy==1.26.4'
    .venv-gmr/bin/python -m pip check
    if [[ "${1:-}" == --deps-only ]]; then
        echo 'Dependencies ready. Before conversion, run: ./workshop auth (SMPL-X and SMPL accounts).'
        exit 0
    elif [[ -f "${XDG_CONFIG_HOME:-$HOME/.config}/gvhmr/smpl_credentials.toml" ]]; then
        echo 'Keeping saved SMPL/SMPL-X logins. To change them: ./gvhmr auth smpl --no-fetch'
    else
        .venv/bin/gvhmr auth smpl
    fi
    ./workshop download
    echo 'Ready. Next: ./workshop body data/inputs/tennis.mp4, then ./workshop robot tennis'
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
if [[ "${1:-}" == --deps-only ]]; then
    echo 'Dependencies ready. Before conversion, run: ./workshop auth (SMPL-X and SMPL accounts).'
    exit 0
fi
# A saved login is enough: download fetches any missing body models with it.
if [[ -f data/home/.config/gvhmr/smpl_credentials.toml ]]; then
    echo 'Keeping saved SMPL/SMPL-X logins. To change them: ./workshop auth'
    ./workshop download
else
    ./workshop auth
fi
echo 'Ready. Next: ./workshop body data/inputs/tennis.mp4, then ./workshop robot tennis'
