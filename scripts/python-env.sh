#!/usr/bin/env bash
# Shared native setup. Never inherit packages from an activated, unrelated env.
unset PYTHONHOME PYTHONPATH
export PYTHONNOUSERSITE=1

is_python312() {
    [[ -x "$1" ]] && "$1" -c 'import sys; sys.exit(sys.version_info[:2] != (3, 12))' >/dev/null 2>&1
}

select_python312() {
    local candidate brew_cmd
    if [[ -n "${SIM_PYTHON:-}" ]]; then
        candidate="$(command -v "$SIM_PYTHON" || true)"
        is_python312 "$candidate" || { echo 'SIM_PYTHON must point to Python 3.12.' >&2; return 1; }
        WORKSHOP_PYTHON="$candidate"
        return
    fi
    candidate="$(command -v python3.12 || true)"
    if is_python312 "$candidate"; then
        WORKSHOP_PYTHON="$candidate"
        return
    fi
    # Homebrew may be installed but not on PATH in a new terminal.
    brew_cmd="$(command -v brew || true)"
    for candidate in /opt/homebrew/bin/brew /usr/local/bin/brew; do
        [[ -n "$brew_cmd" ]] || { [[ ! -x "$candidate" ]] || brew_cmd="$candidate"; }
    done
    if [[ -z "$brew_cmd" ]]; then
        echo 'Install Homebrew (https://brew.sh), then rerun ./setup.sh; it will install Python 3.12 automatically.' >&2
        return 1
    fi
    candidate="$("$brew_cmd" --prefix)/opt/python@3.12/bin/python3.12"
    if ! is_python312 "$candidate"; then
        "$brew_cmd" install python@3.12
    fi
    is_python312 "$candidate" || { echo 'Python 3.12 installation failed.' >&2; return 1; }
    WORKSHOP_PYTHON="$candidate"
}

ensure_python312_env() {
    local target="$1" backup
    if is_python312 "$target/bin/python" && [[ -f "$target/pyvenv.cfg" ]]; then
        echo "Using Python 3.12: $target"
        return
    fi
    if [[ -e "$target" || -L "$target" ]]; then
        mkdir -p "$ROOT/data/environment-backups"
        backup="$(mktemp -d "$ROOT/data/environment-backups/$(basename "$target").XXXXXX")"
        mv "$target" "$backup/environment"
        echo "Saved incompatible environment to $backup/environment"
    fi
    "$WORKSHOP_PYTHON" -m venv "$target"
}
