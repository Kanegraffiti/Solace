#!/data/data/com.termux/files/usr/bin/bash

set -euo pipefail

LLAMA="${SOLACE_LLAMA_CLI:-$HOME/llama.cpp/build/bin/llama-cli}"
MODEL="${SOLACE_QWEN_MODEL:-$HOME/models/qwen2.5-coder-1.5b/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf}"
CONTEXT="${SOLACE_QWEN_CONTEXT:-2048}"
THREADS="${SOLACE_QWEN_THREADS:-4}"
TOKENS="${SOLACE_QWEN_TOKENS:-512}"

fail() {
    printf 'Qwen is not ready: %s\n\n' "$1" >&2
    printf 'From the Solace repository run:\n  bash scripts/setup-qwen-termux.sh\n' >&2
    exit 1
}

[ -x "$LLAMA" ] || fail "llama-cli was not found at $LLAMA"
[ -f "$MODEL" ] || fail "the model was not found at $MODEL"

if [ "$#" -gt 0 ]; then
    exec "$LLAMA" \
        -m "$MODEL" \
        -c "$CONTEXT" \
        -t "$THREADS" \
        -n "$TOKENS" \
        -p "$*"
fi

exec "$LLAMA" \
    -m "$MODEL" \
    -c "$CONTEXT" \
    -t "$THREADS" \
    -cnv
