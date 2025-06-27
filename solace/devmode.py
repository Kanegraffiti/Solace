"""Developer mode utilities for seeding sample data."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from .modes.diary_mode import add_entry
from .logic.notes import add_note
from .logic.todo import add_task

DEV_FLAG = Path("devmode.txt")
MARK_FILE = Path("storage/.dev_seeded")


def enabled(args: list[str]) -> bool:
    """Return True if developer mode is requested."""
    return "--dev" in args or DEV_FLAG.exists()


def populate() -> None:
    """Create dummy diary entries, notes and todos if not already present."""
    if MARK_FILE.exists():
        return
    now = datetime.now()
    for i in range(5):
        ts = (now - timedelta(days=i)).strftime("%Y-%m-%d %H:%M")
        add_entry(f"[DEV] Diary entry {i}", ts, ["dev"], False, False)
    for i in range(10):
        ts = (now - timedelta(days=i)).strftime("%Y-%m-%d %H:%M")
        add_note(f"Dev note {i}", "Example note content", ts, ["dev"], False)
    for i in range(5):
        ts = (now - timedelta(days=i)).strftime("%Y-%m-%d %H:%M")
        add_task(f"Dev task {i}", ts, False)
    MARK_FILE.parent.mkdir(parents=True, exist_ok=True)
    MARK_FILE.write_text("seeded")
