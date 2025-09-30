#!/usr/bin/env bash
# Cross-platform installation helper for Solace.
#
# The script creates a virtual environment, installs required packages
# and registers a handy `solace` alias so the CLI can be launched from
# any directory.  It supports Linux, macOS, Termux and Windows via WSL.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
PYTHON_BIN="${PYTHON:-python3}"

info() { printf '\033[1;34m[info]\033[0m %s\n' "$*"; }
success() { printf '\033[1;32m[success]\033[0m %s\n' "$*"; }

create_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        info "Creating virtual environment in $VENV_DIR"
        "$PYTHON_BIN" -m venv "$VENV_DIR"
    else
        info "Virtual environment already exists"
    fi
}

install_packages() {
    info "Installing Python dependencies"
    # shellcheck disable=SC1090
    source "$VENV_DIR/bin/activate"
    python -m pip install --upgrade pip
    if [ -f "$PROJECT_DIR/requirements.txt" ]; then
        pip install -r "$PROJECT_DIR/requirements.txt"
    fi
    deactivate
}

shell_rc_candidates() {
    local candidates=("$HOME/.bashrc" "$HOME/.zshrc")
    if grep -qi microsoft /proc/version 2>/dev/null; then
        candidates+=("$HOME/.bash_profile")
    fi
    if [ -n "${TERMUX_VERSION:-}" ] || [ -d "$HOME/.termux" ]; then
        mkdir -p "$HOME/.termux/boot"
        candidates+=("$HOME/.termux/boot/solace_alias.sh")
    fi
    printf '%s\n' "${candidates[@]}"
}

add_alias() {
    local target="$1"
    local python_exec="$VENV_DIR/bin/python"
    local alias_line="alias solace=\"$python_exec $PROJECT_DIR/main.py\""

    mkdir -p "$(dirname "$target")"
    touch "$target"
    if grep -Fq "$alias_line" "$target"; then
        info "Alias already present in $target"
        return
    fi
    {
        echo ""
        echo "# Added by the Solace installer"
        echo "$alias_line"
    } >>"$target"
    success "Added solace alias to $target"
}

main() {
    info "Setting up Solace in $PROJECT_DIR"
    create_venv
    install_packages

    for rc in $(shell_rc_candidates); do
        add_alias "$rc"
    done

    success "Installation complete! Open a new terminal or source your shell rc file to use 'solace'."
}

main "$@"
