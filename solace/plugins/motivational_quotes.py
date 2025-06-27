"""Plugin providing a random motivational quote."""

from __future__ import annotations

import random
from typing import Dict, Callable

QUOTES = [
    "Keep going, you're doing great!",
    "Every day is a chance to improve.",
    "Stay positive and work hard.",
]


def register(cmd_map: Dict[str, Callable[[str], None]]) -> None:
    """Register the /motivate command."""

    def cmd_motivate(_: str) -> None:
        print(random.choice(QUOTES))

    cmd_map["motivate"] = cmd_motivate
