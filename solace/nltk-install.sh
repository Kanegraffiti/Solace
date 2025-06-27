#!/bin/bash
# Resilient installer for NLTK and related packages

LOCAL_DIR=""
if [ "$1" = "--local-dir" ] && [ -n "$2" ]; then
    LOCAL_DIR="$2"
fi

SCRIPT_DIR="$(dirname "$0")/.."
. "$SCRIPT_DIR/install-utils.sh"
check_prereqs

if ping -c1 8.8.8.8 > /dev/null 2>&1; then
    ONLINE=1
else
    ONLINE=0
fi

if [ "$ONLINE" -eq 0 ] && [ -z "$LOCAL_DIR" ]; then
    echo "No internet detected and no local dir provided. Skipping nltk.download"
fi

declare -a PKGS=(nltk docutils ebooklib beautifulsoup4)
read -r -p "Install large PDF/Markdown support? (y/n) " yn
if [[ "$yn" =~ ^[Yy]$ ]]; then
    PKGS+=(markdown pdfplumber)
fi

for pkg in "${PKGS[@]}"; do
    install_pkg "$pkg" "$LOCAL_DIR"
done

python - <<'PY'
import nltk
nltk.download('punkt')
PY

