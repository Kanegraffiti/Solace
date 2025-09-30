"""Simple knowledge trainer for Solace."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

BASE_DIR = Path(__file__).resolve().parent
MEMORY_DIR = BASE_DIR / "memory"
KNOWLEDGE_FILE = MEMORY_DIR / "knowledge.json"


def _ensure_storage() -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    if not KNOWLEDGE_FILE.exists():
        KNOWLEDGE_FILE.write_text("[]", encoding="utf-8")


def load_knowledge() -> List[Dict[str, str]]:
    _ensure_storage()
    try:
        return json.loads(KNOWLEDGE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def save_knowledge(entries: List[Dict[str, str]]) -> None:
    _ensure_storage()
    KNOWLEDGE_FILE.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def record(rule: str, example: str | None = None, *, tags: List[str] | None = None) -> Dict[str, str]:
    """Persist a newly learned rule into the knowledge base."""
    entry = {
        "rule": rule.strip(),
        "example": (example or "").strip(),
        "tags": tags or [],
    }
    data = load_knowledge()
    data.append(entry)
    save_knowledge(data)
    return entry
