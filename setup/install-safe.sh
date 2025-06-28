#!/bin/bash
# Resilient installation of Python requirements

REQ_FILE="$(dirname "$0")/../requirements.txt"
LOCAL_DIR=""

if [ "$1" = "--local-dir" ] && [ -n "$2" ]; then
    LOCAL_DIR="$2"
fi

. "$(dirname "$0")/install-utils.sh"
check_prereqs

echo "Detected $(command -v termux-info >/dev/null 2>&1 && echo Termux || echo Linux) environment"

touch "$FAILED_LOG"

while read -r pkg; do
    [ -z "$pkg" ] && continue
    install_pkg "$pkg" "$LOCAL_DIR"
done < "$REQ_FILE"

if [ -f "$FAILED_LOG" ]; then
    cp "$FAILED_LOG" "$FAILED_LOG.tmp"
    > "$FAILED_LOG"
    while read -r pkg; do
        [ -z "$pkg" ] && continue
        install_pkg "$pkg" "$LOCAL_DIR"
    done < "$FAILED_LOG.tmp"
    rm "$FAILED_LOG.tmp"
fi

if [ -f "$(dirname "$0")/../requirements-extra.txt" ]; then
    echo "Optional packages listed in requirements-extra.txt were skipped."
fi
