#!/usr/bin/env bash
# Cross-platform installation helper for Solace.
#
# Creates a project-local virtual environment, installs dependencies there, and
# delegates launcher/config setup to install.py. On Termux this produces a real
# command in $PREFIX/bin, so `solace` works immediately from any directory.
#
# Termux is handled specially because pip cannot reliably build every native
# Python dependency on Android. In particular, cryptography uses Rust/maturin
# and needs Termux-specific linking patches. We therefore install Termux's
# packaged python-cryptography build and expose it to the project venv. Termux
# ships pip as a separate python-pip package, and python-cryptography's package
# setup currently expects the pip3 executable to exist, so python-pip must be
# installed first.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
PYTHON_BIN="${PYTHON:-python3}"

info() { printf '\033[1;34m[info]\033[0m %s\n' "$*"; }
success() { printf '\033[1;32m[success]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$*"; }

is_termux() {
    [ -n "${TERMUX_VERSION:-}" ] || [[ "${PREFIX:-}" == *com.termux* ]]
}

python_minor() {
    "$1" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null
}

venv_needs_rebuild() {
    [ -x "$VENV_DIR/bin/python" ] || return 0

    local system_version venv_version
    system_version="$(python_minor "$PYTHON_BIN" || true)"
    venv_version="$(python_minor "$VENV_DIR/bin/python" || true)"
    if [ -z "$system_version" ] || [ "$system_version" != "$venv_version" ]; then
        warn "Existing venv uses Python ${venv_version:-unknown}; system Python is ${system_version:-unknown}."
        return 0
    fi

    if is_termux && ! grep -Eq '^include-system-site-packages = true$' "$VENV_DIR/pyvenv.cfg" 2>/dev/null; then
        warn "Existing Termux venv cannot see Android-patched system Python packages."
        return 0
    fi

    return 1
}

prepare_termux_python() {
    if ! command -v pkg >/dev/null 2>&1; then
        printf 'Termux package manager `pkg` was not found.\n' >&2
        exit 1
    fi

    if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
        printf 'Python was not found. Install it with `pkg install python` and retry.\n' >&2
        exit 1
    fi

    # Termux deliberately packages pip separately from Python. This must happen
    # before python-cryptography because that package's post-install script uses
    # the pip3 executable. A Python upgrade may remove an old pip executable,
    # which is exactly the state this installer needs to repair automatically.
    info "Ensuring Termux's standalone python-pip package is installed"
    pkg install -y python-pip

    if ! command -v pip3 >/dev/null 2>&1 || ! "$PYTHON_BIN" -m pip --version >/dev/null 2>&1; then
        printf 'Termux python-pip installed but pip3 is still unavailable. Run `pkg reinstall python-pip` and retry.\n' >&2
        exit 1
    fi

    info "Installing Termux's Android-patched python-cryptography package"
    if ! pkg install -y python-cryptography; then
        warn "python-cryptography did not configure cleanly; retrying after python-pip setup"
        pkg install -y python-cryptography
    fi

    if ! "$PYTHON_BIN" -c 'from cryptography.fernet import Fernet' >/dev/null 2>&1; then
        printf 'Termux python-cryptography installed but cannot be imported. Run `pkg upgrade` and retry.\n' >&2
        exit 1
    fi
}

create_venv() {
    if [ -d "$VENV_DIR" ] && venv_needs_rebuild; then
        info "Rebuilding disposable virtual environment for the current Python"
        rm -rf "$VENV_DIR"
    fi

    if [ ! -d "$VENV_DIR" ]; then
        if is_termux; then
            info "Creating Termux virtual environment with system package access"
            "$PYTHON_BIN" -m venv --system-site-packages "$VENV_DIR"
        else
            info "Creating virtual environment in $VENV_DIR"
            "$PYTHON_BIN" -m venv "$VENV_DIR"
        fi
    else
        info "Virtual environment already exists and is compatible"
    fi
}

install_python_dependencies() {
    info "Updating pip inside the Solace virtual environment"
    "$VENV_DIR/bin/python" -m pip install --upgrade pip

    if is_termux; then
        info "Installing Termux-safe Solace CLI dependencies"
        "$VENV_DIR/bin/python" -m pip install -r "$PROJECT_DIR/requirements-termux.txt"

        # Fail early with a useful message instead of discovering a broken
        # native dependency only when Solace starts.
        "$VENV_DIR/bin/python" - <<'PY'
from cryptography.fernet import Fernet
import networkx
import nltk
import rich
import textual
print("Termux core dependency check passed.")
PY
        info "Skipping optional web/voice native stacks on Termux during the core install"
        return
    fi

    info "Installing Python dependencies"
    if [ -f "$PROJECT_DIR/requirements.txt" ]; then
        "$VENV_DIR/bin/python" -m pip install -r "$PROJECT_DIR/requirements.txt"
    fi
    if [ -f "$PROJECT_DIR/requirements-extra.txt" ]; then
        "$VENV_DIR/bin/python" -m pip install -r "$PROJECT_DIR/requirements-extra.txt"
    fi
}

if is_termux; then
    prepare_termux_python
fi

create_venv
install_python_dependencies

info "Creating Solace launchers and configuration"
"$VENV_DIR/bin/python" "$PROJECT_DIR/install.py" --skip-deps "$@"

success "Installation complete. Run 'solace' to start Solace."
