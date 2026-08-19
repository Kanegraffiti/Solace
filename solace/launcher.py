"""Supported launcher for Solace.

This module layers optional local-Qwen support and the startup mini-manual over
the existing root CLI without changing its deterministic journal/memory logic.
Installers point the ``solace`` command here.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

# When this file is launched directly from an installed wrapper, add the repo
# root so the historical root ``main.py`` remains importable.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rich.panel import Panel  # noqa: E402
from rich.table import Table  # noqa: E402

import main as core  # noqa: E402
from solace.local_llm import run_qwen, runtime_status  # noqa: E402
from solace.user_manual import (  # noqa: E402
    MANUAL_TEXT,
    set_startup_manual,
    startup_manual_enabled,
)


def _show_manual() -> None:
    core.console.print(Panel(MANUAL_TEXT, title="Solace · quick start", border_style="cyan"))


def _handle_manual(args: str) -> None:
    action = args.strip().lower()
    if action in {"off", "hide", "disable"}:
        set_startup_manual(False)
        core.console.print(
            "[green]Startup manual hidden.[/] Use [bold]/manual[/bold] anytime, "
            "or [bold]/manual on[/bold] to restore it on startup."
        )
        return
    if action in {"on", "show", "enable"}:
        set_startup_manual(True)
        core.console.print("[green]Startup manual restored.[/]")
        _show_manual()
        return
    if action == "status":
        state = "on" if startup_manual_enabled() else "off"
        core.console.print(f"Startup manual: [bold]{state}[/bold]")
        return
    if action:
        core.console.print("[yellow]Usage: /manual [on|off|status][/]")
        return
    _show_manual()


def _handle_qwen(args: str) -> None:
    prompt = args.strip()
    if prompt.lower() == "status":
        ready, message = runtime_status()
        style = "green" if ready else "yellow"
        core.console.print(Panel(message, title="Qwen status", border_style=style))
        return

    if not prompt and core.PROMPT_DEFAULTS_ONLY:
        core.console.print("[yellow]Provide a prompt when scripting /qwen.[/]")
        return

    ready, message = runtime_status()
    if not ready:
        core.console.print(Panel(message, title="Qwen unavailable", border_style="yellow"))
        return

    core.console.print(
        "[dim]Opening local Qwen. Use /exit or Ctrl+C inside Qwen to return to Solace.[/]"
    )
    try:
        run_qwen(prompt or None, interactive=not bool(prompt))
    except KeyboardInterrupt:
        core.console.print("\n[yellow]Qwen stopped.[/]")
    except (OSError, RuntimeError, ValueError) as exc:
        core.console.print(Panel(str(exc), title="Qwen error", border_style="red"))
        return

    if prompt:
        core._log_event("qwen", prompt[:80])


def _extended_help(_: str) -> None:
    core._ORIGINAL_HELP_HANDLER("")
    table = Table(title="Local AI & startup help", show_header=True)
    table.add_column("Command")
    table.add_column("Description")
    table.add_row("/qwen <prompt>", "Open the local Qwen coder with an initial prompt")
    table.add_row("/qwen", "Open an interactive local Qwen chat")
    table.add_row("/qwen status", "Check the llama.cpp runtime and Qwen model paths")
    table.add_row("/manual", "Show the tiny startup manual now")
    table.add_row("/manual off", "Hide the manual on future starts")
    table.add_row("/manual on", "Restore the manual on future starts")
    core.console.print(table)


def _register_extensions() -> None:
    if not hasattr(core, "_ORIGINAL_HELP_HANDLER"):
        core._ORIGINAL_HELP_HANDLER = core.COMMANDS["help"]
    core.COMMANDS["help"] = _extended_help
    core.COMMANDS["manual"] = _handle_manual
    core.COMMANDS["qwen"] = _handle_qwen


def _is_scripted(argv: Sequence[str]) -> bool:
    scripted_flags = {"-c", "--command", "--command-file"}
    return any(arg in scripted_flags or arg.startswith("--command=") for arg in argv)


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    _register_extensions()
    if not _is_scripted(args) and startup_manual_enabled():
        _show_manual()
    core.main(args)


if __name__ == "__main__":
    main()
