"""Store recent code-related queries and results."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

HISTORY_FILE = Path(__file__).resolve().parents[2] / "storage" / "code_history.json"
MAX_ENTRIES = 5


def _load() -> List[Dict]:
    if not HISTORY_FILE.exists():
        return []
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _save(data: List[Dict]) -> None:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(data[-MAX_ENTRIES:], indent=2), encoding="utf-8")


def add_entry(prompt: str, code: str, explanation: str, language: str) -> None:
    """Add a new history entry."""
    entry = {
        "prompt": prompt,
        "code": code,
        "explanation": explanation,
        "language": language,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    data = _load()
    data.append(entry)
    _save(data)


def find_similar(prompt: str) -> Optional[Dict]:
    """Return the most similar past entry to ``prompt`` if any."""
    tokens = set(prompt.lower().split())
    best = None
    best_score = 0
    for item in _load():
        item_tokens = set(item.get("prompt", "").lower().split())
        score = len(tokens & item_tokens)
        if score > best_score:
            best_score = score
            best = item
    return best
