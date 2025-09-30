"""Lightweight journaling helpers for the Solace CLI."""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Dict, Iterable, List

BASE_DIR = Path(__file__).resolve().parent
MEMORY_DIR = BASE_DIR / "memory"
JOURNAL_JSON = MEMORY_DIR / "journal.json"
JOURNAL_LOG = MEMORY_DIR / "journal.log"


def _ensure_storage() -> None:
    """Create the memory directory and base files if missing."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    if not JOURNAL_JSON.exists():
        JOURNAL_JSON.write_text("[]", encoding="utf-8")
    if not JOURNAL_LOG.exists():
        JOURNAL_LOG.touch()


def load_entries() -> List[Dict[str, str]]:
    """Return all diary entries stored in ``memory/journal.json``."""
    _ensure_storage()
    try:
        return json.loads(JOURNAL_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # If the file is corrupted we return an empty list but keep the
        # unreadable file for manual inspection.
        return []


def save_entries(entries: Iterable[Dict[str, str]]) -> None:
    """Persist ``entries`` into the JSON store and append to the log."""
    _ensure_storage()
    serialisable = list(entries)
    JOURNAL_JSON.write_text(json.dumps(serialisable, indent=2), encoding="utf-8")


def add_entry(text: str, *, tags: List[str] | None = None) -> Dict[str, str]:
    """Create a journal entry containing ``text`` and optional ``tags``."""
    tags = tags or []
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "text": text.strip(),
        "tags": tags,
    }
    entries = load_entries()
    entries.append(entry)
    save_entries(entries)

    with JOURNAL_LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"[{entry['timestamp']}] {' '.join(tags)}\n{text.strip()}\n\n")
    return entry


def latest_entries(limit: int = 5) -> List[Dict[str, str]]:
    """Return the ``limit`` most recent entries (defaults to 5)."""
    entries = load_entries()
    return entries[-limit:]


def has_entries() -> bool:
    """Check whether the journal already contains user input."""
    return bool(load_entries())
