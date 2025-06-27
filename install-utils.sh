#!/bin/bash
# Helper functions for resilient pip installation

PROGRESS_FILE="install-progress.json"
FAILED_LOG="failed.log"

trap "echo Aborted" EXIT

check_prereqs() {
    command -v python >/dev/null 2>&1 || { echo "python is required. Please install Python."; exit 1; }
    command -v pip >/dev/null 2>&1 || { echo "pip is required. Please install pip."; exit 1; }
}

get_status() {
    local pkg="$1"
    python - "$PROGRESS_FILE" "$pkg" <<'PY'
import json, sys, os
f=sys.argv[1]; pkg=sys.argv[2]
if os.path.exists(f):
    try:
        with open(f) as fp:
            data=json.load(fp)
        print(data.get(pkg, ""))
    except Exception:
        pass
PY
}

update_progress() {
    local pkg="$1"
    local status="$2"
    python - "$PROGRESS_FILE" "$pkg" "$status" <<'PY'
import json, sys, os
f=sys.argv[1]; pkg=sys.argv[2]; status=sys.argv[3]
data={}
if os.path.exists(f):
    try:
        with open(f) as fp:
            data=json.load(fp)
    except Exception:
        data={}
data[pkg]=status
with open(f, 'w') as fp:
    json.dump(data, fp, indent=2)
PY
}

manual_download() {
    local pkg="$1"
    local url=$(curl -fsSL "https://pypi.org/simple/$pkg/" | grep -o 'https://files.pythonhosted.org/[^"']*\.whl' | head -n 1)
    if [ -n "$url" ]; then
        echo "Downloading $pkg wheel with curl..."
        if curl -L "$url" -o "/tmp/$pkg.whl" && pip install "/tmp/$pkg.whl" --no-cache-dir --progress-bar on; then
            echo "✅ $pkg installed from wheel"
            sed -i "/^$pkg$/d" "$FAILED_LOG" 2>/dev/null
            update_progress "$pkg" "installed"
            return 0
        fi
    fi
    return 1
}

install_pkg() {
    local pkg="$1"
    local local_dir="$2"

    local status=$(get_status "$pkg")
    if [ "$status" = "installed" ]; then
        echo "✅ $pkg already installed."
        return 0
    fi

    if pip show "$pkg" >/dev/null 2>&1; then
        echo "✅ $pkg already installed."
        update_progress "$pkg" "installed"
        return 0
    fi

    if [ -n "$local_dir" ] && [ -f "$local_dir/$pkg.whl" ]; then
        echo "🔧 Installing $pkg from $local_dir/$pkg.whl"
        if pip install "$local_dir/$pkg.whl" --no-cache-dir --progress-bar on; then
            echo "✅ Done"
            update_progress "$pkg" "installed"
            return 0
        fi
    fi

    local attempt=1
    local delay=2
    while [ $attempt -le 5 ]; do
        echo "🔧 Installing $pkg... (attempt $attempt)"
        if pip install "$pkg" --retries 5 --timeout 15 --no-cache-dir --prefer-binary --progress-bar on; then
            echo "✅ Done"
            update_progress "$pkg" "installed"
            sed -i "/^$pkg$/d" "$FAILED_LOG" 2>/dev/null
            return 0
        else
            echo "⚠️ Retrying..."
            update_progress "$pkg" "retrying"
            sleep $delay
            delay=$((delay * 2))
        fi
        attempt=$((attempt + 1))
    done
    echo "❌ Failed $pkg"
    echo "$pkg" >> "$FAILED_LOG"
    update_progress "$pkg" "failed"
    manual_download "$pkg"
    return 1
}
