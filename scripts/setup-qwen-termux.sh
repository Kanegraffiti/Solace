#!/data/data/com.termux/files/usr/bin/bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LLAMA_DIR="${SOLACE_LLAMA_DIR:-$HOME/llama.cpp}"
MODEL_DIR="${SOLACE_QWEN_MODEL_DIR:-$HOME/models/qwen2.5-coder-1.5b}"
MODEL="$MODEL_DIR/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
MODEL_URL="https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/resolve/main/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
MODEL_SHA256="cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046"
BUILD_JOBS="${QWEN_BUILD_JOBS:-2}"

info() { printf '\033[1;34m[info]\033[0m %s\n' "$*"; }
success() { printf '\033[1;32m[success]\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m[error]\033[0m %s\n' "$*" >&2; exit 1; }

if [ -z "${PREFIX:-}" ] || [[ "$PREFIX" != *com.termux* ]]; then
    fail "This helper is intentionally limited to Termux."
fi

case "$BUILD_JOBS" in
    ''|*[!0-9]*) fail "QWEN_BUILD_JOBS must be a positive integer." ;;
    0) fail "QWEN_BUILD_JOBS must be at least 1." ;;
esac

info "Installing/confirming Termux build tools"
pkg install -y git cmake clang curl

if [ ! -d "$LLAMA_DIR/.git" ]; then
    if [ -e "$LLAMA_DIR" ]; then
        fail "$LLAMA_DIR exists but is not a git checkout. Move it aside or set SOLACE_LLAMA_DIR."
    fi
    info "Cloning llama.cpp"
    git clone --depth 1 https://github.com/ggml-org/llama.cpp.git "$LLAMA_DIR"
else
    info "Using existing llama.cpp checkout at $LLAMA_DIR (not modifying its branch or pulling updates)"
fi

info "Configuring llama.cpp Release build"
cmake -S "$LLAMA_DIR" -B "$LLAMA_DIR/build" -DCMAKE_BUILD_TYPE=Release

info "Building llama-cli with $BUILD_JOBS parallel job(s)"
cmake --build "$LLAMA_DIR/build" \
    --config Release \
    -j"$BUILD_JOBS" \
    --target llama-cli

LLAMA_BIN="$LLAMA_DIR/build/bin/llama-cli"
[ -x "$LLAMA_BIN" ] || fail "Build completed but llama-cli was not found at $LLAMA_BIN"

mkdir -p "$MODEL_DIR"
if [ ! -f "$MODEL" ]; then
    info "Downloading Qwen2.5-Coder-1.5B-Instruct Q4_K_M (about 1.12 GB)"
    PART="$MODEL.part"
    rm -f "$PART"
    curl -fL --retry 3 --retry-delay 2 "$MODEL_URL" -o "$PART"

    info "Verifying model SHA-256"
    python - "$PART" "$MODEL_SHA256" <<'PY'
import hashlib
import sys
from pathlib import Path

path = Path(sys.argv[1])
expected = sys.argv[2].lower()
digest = hashlib.sha256()
with path.open("rb") as handle:
    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
        digest.update(chunk)
actual = digest.hexdigest()
if actual != expected:
    raise SystemExit(f"checksum mismatch: expected {expected}, got {actual}")
print(f"checksum OK: {actual}")
PY
    mv "$PART" "$MODEL"
else
    info "Model already exists at $MODEL; leaving it untouched"
fi

QWEN_LAUNCHER="$PREFIX/bin/qwen"
cat > "$QWEN_LAUNCHER" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec bash "$PROJECT_DIR/scripts/qwen.sh" "\$@"
EOF
chmod 700 "$QWEN_LAUNCHER"

success "Qwen is ready"
printf '\nRuntime: %s\nModel:   %s\nCommand: qwen\n' "$LLAMA_BIN" "$MODEL"
printf 'Inside Solace: /qwen status, /qwen <prompt>, or /qwen\n'
