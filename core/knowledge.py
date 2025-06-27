"""Simple graph-based knowledge storage and lookup for Solace.

This module manages an indexed collection of knowledge entries. Each entry
contains a topic, optional programming language, explanation text, code snippet,
tags and a creation date. Data is persisted to a JSON file on disk.

The design is intentionally lightweight so it can run offline on low power
systems. A minimal adjacency map is used to provide graph-like relations between
topics via keywords.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional


class KnowledgeBase:
    """Store and retrieve short knowledge snippets.

    Parameters
    ----------
    path:
        Location of the JSON file used for persistence.
    """

    def __init__(self, path: str | Path = "storage/knowledge_store.json") -> None:
        self.path = Path(path)
        self.entries: List[Dict] = []
        self.index: Dict[str, List[int]] = defaultdict(list)
        if self.path.exists():
            self._load()

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------
    def _load(self) -> None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                self.entries = data
                self._rebuild_index()
        except (OSError, json.JSONDecodeError):
            self.entries = []
            self.index.clear()

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.entries, indent=2), encoding="utf-8")
        except OSError:
            # Fallback: ignore write errors
            pass

    def _rebuild_index(self) -> None:
        self.index.clear()
        for idx, entry in enumerate(self.entries):
            for kw in entry.get("tags", []):
                self.index[kw.lower()].append(idx)
            topic = entry.get("topic", "").lower()
            if topic:
                self.index[topic].append(idx)

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def add_entry(
        self,
        topic: str,
        language: str,
        explanation: str,
        code: str,
        tags: Optional[Iterable[str]] = None,
        date: Optional[str] = None,
    ) -> None:
        """Add a new knowledge entry to the store."""
        if not topic:
            raise ValueError("topic is required")
        if not explanation and not code:
            raise ValueError("either explanation or code must be provided")
        entry = {
            "topic": topic.strip(),
            "language": language.strip().lower() if language else "",
            "explanation": explanation.strip(),
            "code": code.rstrip(),
            "tags": [t.strip().lower() for t in (tags or [])],
            "date": date or datetime.now().isoformat(timespec="seconds"),
        }
        self.entries.append(entry)
        idx = len(self.entries) - 1
        for kw in entry["tags"]:
            self.index[kw].append(idx)
        self.index[entry["topic"].lower()].append(idx)
        self._save()

    def search(
        self,
        keyword: str,
        *,
        language: Optional[str] = None,
        max_results: int = 5,
    ) -> List[Dict]:
        """Return entries matching ``keyword`` and optional language."""
        if not keyword:
            return []
        keyword = keyword.strip().lower()
        idxs = self.index.get(keyword, [])
        results = []
        for i in idxs:
            entry = self.entries[i]
            if language and entry.get("language") != language.lower():
                continue
            results.append(entry)
            if len(results) >= max_results:
                break
        return results

    def all_entries(self) -> List[Dict]:
        """Return a copy of all stored entries."""
        return list(self.entries)


__all__ = ["KnowledgeBase"]

