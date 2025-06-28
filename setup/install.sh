#!/usr/bin/env bash

# install.sh - Installer for Solace
# Creates a virtual environment, installs dependencies with retries
# and sets up a global 'solace' command.

set -e
trap 'echo "Installation failed" >&2' ERR

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$REPO_DIR")"
VENV_DIR="$REPO_DIR/.venv"
PIP="$VENV_DIR/bin/pip"
PYTHON="$VENV_DIR/bin/python"

# Detect environment
ENV_TYPE="linux"
if command -v termux-info >/dev/null 2>&1; then
    ENV_TYPE="termux"
elif [[ "$(uname -o 2>/dev/null)" =~ Msys|Cygwin ]] || [[ "$(uname -s)" == *NT* ]]; then
    ENV_TYPE="windows"
fi

echo "Detected environment: $ENV_TYPE"

install_system_packages() {
    case "$ENV_TYPE" in
        linux)
            if command -v apt-get >/dev/null 2>&1; then
                echo "Installing system packages..."
                sudo apt-get update
                sudo apt-get install -y python3 python3-pip espeak portaudio19-dev ffmpeg
            fi
            ;;
        termux)
            echo "Installing system packages..."
            pkg update -y
            pkg install -y python git espeak portaudio ffmpeg
            ;;
        *)
            echo "Ensure Python 3 is installed on your system." ;;
    esac
}

install_system_packages

echo "Creating virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

# Check network connectivity
ONLINE=true
if ! ping -c1 8.8.8.8 >/dev/null 2>&1; then
    ONLINE=false
    echo "You are offline. Falling back to local wheels if available..."
fi

pip_install() {
    local pkg="$1"
    local attempt=1
    local delay=2
    while [ $attempt -le 3 ]; do
        if $ONLINE; then
            if $PIP install "$pkg" --timeout 120 --no-cache-dir; then
                return 0
            fi
        else
            local wheel
            wheel=$(ls "$REPO_DIR"/wheels/${pkg}-*.whl 2>/dev/null | head -n 1)
            if [ -n "$wheel" ]; then
                if $PIP install "$wheel" --no-cache-dir; then
                    return 0
                fi
            fi
            echo "Offline and wheel for $pkg not found." >&2
            return 1
        fi
        echo "Retrying $pkg in $delay seconds..." >&2
        sleep $delay
        delay=$((delay * 2))
        attempt=$((attempt + 1))
    done
    echo "Failed to install $pkg" >&2
    return 1
}

# Required packages
REQUIRED=(nltk docutils beautifulsoup4 ebooklib networkx pyttsx3 sounddevice speechrecognition cryptography)

OPTIONAL_PACKAGES=()
read -rp "Do you want to enable Markdown + PDF Support? (y/N) " ans
if [[ "$ans" =~ ^[Yy]$ ]]; then
    OPTIONAL_PACKAGES+=(markdown pdfplumber)
fi

for pkg in "${REQUIRED[@]}" "${OPTIONAL_PACKAGES[@]}"; do
    echo "Installing $pkg..."
    pip_install "$pkg"
done

read -rp "Install extra training datasets for conversation? (y/N) " ans
if [[ "$ans" =~ ^[Yy]$ ]]; then
    if $ONLINE; then
        $PYTHON - <<'PY'
import nltk
for pkg in ["punkt","averaged_perceptron_tagger","wordnet","stopwords"]:
    nltk.download(pkg)
PY
    else
        echo "Cannot download datasets without internet connection." >&2
    fi
fi

LAUNCHER_SETUP="$REPO_DIR/setup_cli.py"
chmod +x "$REPO_DIR/solace.sh"
echo "Setting up launcher script..."
$PYTHON "$LAUNCHER_SETUP"
echo "Installation complete."

read -rp "Restart your shell now to enable the 'solace' command? [y/N] " ans
if [[ "$ans" =~ ^[Yy]$ ]]; then
    exec "$SHELL" -l
else
    echo "Restart your terminal later to use the 'solace' command."
fi
