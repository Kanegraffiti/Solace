"""Local Qwen/llama.cpp integration for Solace.

The integration is intentionally conservative: it never downloads a model or
builds llama.cpp implicitly. The Termux setup helper performs those explicit
operations; this module only discovers the configured files and launches them
without a shell.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional, Sequence

DEFAULT_LLAMA_CLI = Path.home() / "llama.cpp" / "build" / "bin" / "llama-cli"
DEFAULT_QWEN_MODEL = (
    Path.home()
    / "models"
    / "qwen2.5-coder-1.5b"
    / "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
)


@dataclass(frozen=True)
class LocalModelSettings:
    """Runtime settings for a llama.cpp-compatible local GGUF model."""

    llama_cli: Path = DEFAULT_LLAMA_CLI
    model: Path = DEFAULT_QWEN_MODEL
    context: int = 2048
    threads: int = 4
    max_tokens: int = 512


def _positive_int(value: Optional[str], default: int) -> int:
    try:
        parsed = int(value or "")
    except ValueError:
        return default
    return parsed if parsed > 0 else default


QwenSettings = LocalModelSettings


def settings_from_environment(env: Optional[Mapping[str, str]] = None) -> LocalModelSettings:
    """Build settings from environment overrides and safe mobile defaults."""

    values = os.environ if env is None else env
    model_path = values.get("SOLACE_LLAMA_MODEL") or values.get("SOLACE_QWEN_MODEL")
    return LocalModelSettings(
        llama_cli=Path(values.get("SOLACE_LLAMA_CLI", str(DEFAULT_LLAMA_CLI))).expanduser(),
        model=Path(model_path or str(DEFAULT_QWEN_MODEL)).expanduser(),
        context=_positive_int(values.get("SOLACE_QWEN_CONTEXT"), 2048),
        threads=_positive_int(values.get("SOLACE_QWEN_THREADS"), 4),
        max_tokens=_positive_int(values.get("SOLACE_QWEN_TOKENS"), 512),
    )


def runtime_status(settings: Optional[LocalModelSettings] = None) -> tuple[bool, str]:
    """Return whether the configured local model is ready."""

    cfg = settings or settings_from_environment()
    missing: list[str] = []
    if not cfg.llama_cli.is_file():
        missing.append(f"llama-cli: {cfg.llama_cli}")
    elif not os.access(cfg.llama_cli, os.X_OK):
        missing.append(f"llama-cli is not executable: {cfg.llama_cli}")
    if not cfg.model.is_file():
        missing.append(f"model: {cfg.model}")

    if missing:
        detail = "\n".join(f"- {item}" for item in missing)
        return (
            False,
            "Local model is not ready. Missing:\n"
            f"{detail}\n\n"
            "On Termux, run `bash scripts/setup-qwen-termux.sh` from the Solace repo.",
        )

    return (
        True,
        "Local model is ready.\n"
        f"Model: {cfg.model}\n"
        f"Runtime: {cfg.llama_cli}\n"
        f"Context: {cfg.context} | Threads: {cfg.threads} | Max tokens: {cfg.max_tokens}",
    )


def build_command(
    prompt: Optional[str] = None,
    *,
    interactive: bool = False,
    settings: Optional[LocalModelSettings] = None,
) -> list[str]:
    """Return the llama.cpp argv for local Qwen without invoking a shell."""

    cfg = settings or settings_from_environment()
    command = [
        str(cfg.llama_cli),
        "-m",
        str(cfg.model),
        "-c",
        str(cfg.context),
        "-t",
        str(cfg.threads),
    ]

    if interactive:
        command.append("-cnv")
    else:
        command.extend(["-n", str(cfg.max_tokens)])
        if prompt:
            command.extend(["-p", prompt])
    return command


def run_local_model(
    prompt: Optional[str] = None,
    *,
    interactive: bool = False,
    settings: Optional[LocalModelSettings] = None,
) -> int:
    """Run the configured GGUF model locally and return llama.cpp's status."""

    cfg = settings or settings_from_environment()
    ready, message = runtime_status(cfg)
    if not ready:
        raise RuntimeError(message)
    if not interactive and not (prompt or "").strip():
        raise ValueError("A prompt is required unless interactive=True")

    result = subprocess.run(
        build_command(prompt, interactive=interactive, settings=cfg),
        check=False,
    )
    return int(result.returncode)


run_qwen = run_local_model


__all__: Sequence[str] = (
    "DEFAULT_LLAMA_CLI",
    "DEFAULT_QWEN_MODEL",
    "LocalModelSettings",
    "QwenSettings",
    "build_command",
    "run_local_model",
    "run_qwen",
    "runtime_status",
    "settings_from_environment",
)
