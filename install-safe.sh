#!/bin/bash
# Install required Python packages with retries and timeouts

REQ_FILE="requirements.txt"

if command -v termux-info >/dev/null 2>&1; then
    PLATFORM="Termux"
else
    PLATFORM="Linux"
fi

echo "Detected $PLATFORM environment"

while read -r pkg; do
    [ -z "$pkg" ] && continue
    echo "Installing $pkg..."
    pip install --timeout=120 --no-cache-dir "$pkg" && \
        echo "$pkg installed." || \
        echo "Warning: $pkg failed to install."
done < "$REQ_FILE"

if [ -f "requirements-extra.txt" ]; then
    echo "Optional packages listed in requirements-extra.txt were skipped."
fi
