#!/bin/bash

# detect internet connectivity
if ping -c1 8.8.8.8 > /dev/null 2>&1; then
    ONLINE=1
else
    ONLINE=0
fi

install_pkg() {
    local pkg="$1"
    local attempt=1
    while [ $attempt -le 5 ]; do
        echo "Installing $pkg (attempt $attempt)..."
        if pip install "$pkg" --timeout=120 --no-cache-dir --progress-bar off; then
            return 0
        fi
        attempt=$((attempt+1))
    done
    echo "SKIPPED $pkg"
}

if [ "$ONLINE" -eq 0 ]; then
    echo "No internet detected. Installing available wheels locally."
    shopt -s nullglob
    for whl in wheels/*.whl; do
        install_pkg "$whl"
    done
    shopt -u nullglob
    echo "Offline mode: skipping remote nltk.download"
    exit 0
fi

install_pkg nltk
install_pkg docutils
install_pkg ebooklib
install_pkg beautifulsoup4

read -r -p "Install large PDF/Markdown support? (y/n) " yn
if [[ "$yn" =~ ^[Yy]$ ]]; then
    install_pkg markdown
    install_pkg pdfplumber
fi

python - <<'PY'
import nltk
nltk.download('punkt')
PY
