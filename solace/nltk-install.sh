#!/bin/bash

install_pkg() {
    pkg="$1"
    echo "Installing $pkg ..."
    pip install --quiet "$pkg" && echo "$pkg installed" || echo "$pkg failed to install"
}

install_pkg nltk
install_pkg markdown
install_pkg docutils
install_pkg pdfplumber
install_pkg ebooklib
install_pkg beautifulsoup4
# Optional dependency disabled for now
# install_pkg pypdfium2

if ping -c 1 google.com > /dev/null 2>&1; then
python - <<'PY'
import nltk
nltk.download('punkt')
PY
else
    echo "No internet, skipping nltk.download"
fi
