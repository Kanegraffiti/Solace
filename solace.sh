#!/usr/bin/env bash
# Solace command launcher

if [[ "$1" == "-h" || "$1" == "--help" ]]; then
cat <<'HELP'
Solace - Offline-first Diary, Code Tutor, and Knowledge Manager
Usage: solace [options]

Starts the Solace command-line interface.

Options:
  -h, --help   Show this help message
HELP
exit 0
fi

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
exec "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/main.py" "$@"
