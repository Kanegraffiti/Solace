"""Startup mini-manual and preference helpers for Solace."""

from __future__ import annotations

from typing import Any, Optional

from solace.configuration import load_config, save_config

MANUAL_TEXT = """[bold]The tiny Solace manual[/bold]

• Plain text → save a diary entry.
• /chat <message> → talk with Solace's local memory/knowledge companion.
• /qwen <prompt> → ask the local Qwen coder model; /qwen alone opens Qwen chat.
• /search <query> → find journal memories.
• /code bash <topic> → get a deterministic Bash recipe.
• /help → see every Solace command.

Hide this panel on future starts: [bold]/manual off[/bold]
Show it whenever you want: [bold]/manual[/bold]
Restore it on startup: [bold]/manual on[/bold]
"""


def startup_manual_enabled(config: Optional[dict[str, Any]] = None) -> bool:
    """Return whether the mini-manual should appear at interactive startup."""

    cfg = load_config() if config is None else config
    return bool(cfg.get("ui", {}).get("show_startup_manual", True))


def set_startup_manual(enabled: bool) -> dict[str, Any]:
    """Persist the mini-manual startup preference."""

    config = load_config()
    config.setdefault("ui", {})["show_startup_manual"] = bool(enabled)
    save_config(config)
    return config


__all__ = ["MANUAL_TEXT", "set_startup_manual", "startup_manual_enabled"]
