"""Plugin loader for Solace."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Dict, Callable

from ..commands import COMMAND_MAP, CommandFunc

PLUGIN_PATH = Path(__file__).parent


def load_plugins() -> None:
    """Load plugins from the plugins directory."""
    for file in PLUGIN_PATH.glob("*.py"):
        if file.name == "__init__.py":
            continue
        spec = importlib.util.spec_from_file_location(file.stem, file)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore
            register = getattr(mod, "register", None)
            if callable(register):
                try:
                    register(COMMAND_MAP)
                except Exception:
                    print(f"Failed to load plugin: {file.name}")

