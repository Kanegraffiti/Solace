#!/usr/bin/env bash
# Cross-platform installation helper for Solace.
#
# Creates a project-local virtual environment, installs dependencies there, and
# delegates launcher/config setup to install.py. On Termux this produces a real
# command in $PREFIX/bin, so `solace` works immediately from any directory.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
PYTHON_BIN="${PYTHON:-python3}"

info() { printf '\033[1;34m[info]\033[0m %s\n' "$*"; }
success() { printf '\033[1;32m[success]\033[0m %s\n' "$*"; }

if [ ! -d "$VENV_DIR" ]; then
    info "Creating virtual environment in $VENV_DIR"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
else
    info "Virtual environment already exists"
fi

info "Installing Python dependencies"
"$VENV_DIR/bin/python" -m pip install --upgrade pip
if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    "$VENV_DIR/bin/python" -m pip install -r "$PROJECT_DIR/requirements.txt"
fi
if [ -f "$PROJECT_DIR/requirements-extra.txt" ]; then
    "$VENV_DIR/bin/python" -m pip install -r "$PROJECT_DIR/requirements-extra.txt"
fi

info "Creating Solace launchers and configuration"
"$VENV_DIR/bin/python" "$PROJECT_DIR/install.py" --skip-deps "$@"

success "Installation complete. Run 'solace' to start Solace."
