#!/usr/bin/env bash
# Cross-platform installation helper for Solace.
#
# Creates a project-local virtual environment, installs dependencies there, and
# delegates launcher/config setup to install.py. On Termux this produces a real
# command in $PREFIX/bin, so `solace` works immediately from any directory.
#
# Termux is handled specially because pip cannot reliably build every native
# Python dependency on Android. In particular, cryptography uses Rust/maturin
# and needs Termux-specific linking. We therefore install Termux's packaged
# python-cryptography build and expose it to the project venv. If an earlier
# package install happened before pip3 was healthy, the package's post-install
# dependency step may have been skipped; Solace detects the missing CFFI backend
# and repairs that half-configured state before checking Android loader quirks.

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

termux_pkg_install() {
    local package="$1"

    if TERMUX_PKG_NO_MIRROR_SELECT=1 pkg install -y "$package"; then
        return 0
    fi

    printf '\nTermux could not install %s from the configured repository.\n' "$package" >&2
    printf 'Run `termux-change-repo`, choose a working main repository, then rerun `bash install.sh`.\n' >&2
    return 1
}

termux_pkg_reinstall() {
    local package="$1"

    if TERMUX_PKG_NO_MIRROR_SELECT=1 pkg reinstall -y "$package"; then
        return 0
    fi

    printf '\nTermux could not reinstall %s from the configured repository.\n' "$package" >&2
    printf 'Run `termux-change-repo`, choose a working main repository, then rerun `bash install.sh`.\n' >&2
    return 1
}

termux_cffi_ready() {
    local python_bin="$1"
    "$python_bin" -c 'import _cffi_backend' >/dev/null 2>&1
}

termux_crypto_check() {
    local python_bin="$1"
    "$python_bin" "$PROJECT_DIR/solace/termux_compat.py"
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

    # python-cryptography's Termux package installs its target Python
    # dependencies during package configuration, so pip3 must exist first.
    info "Ensuring Termux's standalone python-pip package is installed"
    termux_pkg_install python-pip

    if ! command -v pip3 >/dev/null 2>&1 || ! "$PYTHON_BIN" -m pip --version >/dev/null 2>&1; then
        printf 'Termux python-pip installed but pip3 is still unavailable. Run `pkg reinstall python-pip` and retry.\n' >&2
        exit 1
    fi

    info "Installing Termux's Android-patched python-cryptography package"
    if ! termux_pkg_install python-cryptography; then
        warn "python-cryptography did not configure cleanly; retrying after python-pip setup"
        termux_pkg_reinstall python-cryptography
    fi

    # A previous python-cryptography install may have been marked installed even
    # though its post-install pip step failed while pip3 was absent. In that
    # state cryptography exists but importing it fails with missing
    # `_cffi_backend`. Reinstalling the Termux package after pip is healthy
    # reruns its own declared target-dependency setup without compiling an
    # unrelated replacement cryptography wheel.
    if ! termux_cffi_ready "$PYTHON_BIN"; then
        warn "Termux cryptography is missing its CFFI runtime dependency; repairing package setup"
        termux_pkg_reinstall python-cryptography
    fi

    if ! termux_cffi_ready "$PYTHON_BIN"; then
        printf '\nTermux reconfigured python-cryptography but `_cffi_backend` is still unavailable.\n' >&2
        printf 'Please report the reinstall output and `termux-info`; do not run another full `pkg upgrade`.\n' >&2
        exit 1
    fi

    info "Checking Termux cryptography runtime compatibility"
    if ! termux_crypto_check "$PYTHON_BIN"; then
        printf '\nTermux python-cryptography is installed but the native module still cannot load.\n' >&2
        printf 'The traceback above is the useful diagnostic; a full `pkg upgrade` is not the recovery step.\n' >&2
        printf 'Please report that traceback together with `termux-info`.\n' >&2
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

        if ! termux_cffi_ready "$VENV_DIR/bin/python"; then
            printf 'The Solace virtual environment cannot see Termux CFFI system packages.\n' >&2
            printf 'Delete only `%s` and rerun `bash install.sh`; user data is stored outside the venv.\n' "$VENV_DIR" >&2
            exit 1
        fi

        info "Checking native cryptography from the Solace virtual environment"
        termux_crypto_check "$VENV_DIR/bin/python"

        "$VENV_DIR/bin/python" - <<'PY'
import networkx
import nltk
import rich
import textual
print("Termux core Python dependency check passed.")
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
