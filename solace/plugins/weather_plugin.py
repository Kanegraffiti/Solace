"""Simple weather plugin returning a static response."""

from __future__ import annotations

from typing import Dict, Callable


def register(cmd_map: Dict[str, Callable[[str], None]]) -> None:
    """Register the /weather command."""

    def cmd_weather(_: str) -> None:
        print("Weather is calm and sunny.")

    cmd_map["weather"] = cmd_weather
