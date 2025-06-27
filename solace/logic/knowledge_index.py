"""Simple indexed storage for taught code snippets and query results."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

INDEX_FILE = Path(__file__).resolve().parents[2] / "storage" / "knowledge_index.json"


def _load() -> List[Dict]:
    if not INDEX_FILE.exists():
        return []
    try:
        return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _save(data: List[Dict]) -> None:
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    INDEX_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def add_entry(topic: str, language: str, explanation: str, code: str, tags: List[str] | None = None) -> None:
    """Add a knowledge entry for later recall."""
    entry = {
        "topic": topic,
        "language": language,
        "explanation": explanation,
        "code": code,
        "tags": tags or [],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    data = _load()
    data.append(entry)
    _save(data)


def get_all() -> List[Dict]:
    """Return all stored knowledge entries."""
    data = _load()
    for item in data:
        item.setdefault("text", f"{item.get('code','')}\n{item.get('explanation','')}")
    return data
