"""Offline fuzzy memory search over journal and knowledge entries."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from typing import Iterable, List

from journal import JournalEntry

MONTH_MAP = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sept": 9,
    "sep": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}


@dataclass
class MemoryHit:
    entry: JournalEntry
    score: float
    matched_date: bool = False


def _extract_date_hint(query: str) -> str | None:
    query = query.lower()
    iso_match = re.search(r"(\d{4}-\d{2}-\d{2})", query)
    if iso_match:
        return iso_match.group(1)

    tokens = re.split(r"\s+", query)
    for idx, token in enumerate(tokens):
        clean = token.strip(",.?!")
        if clean in MONTH_MAP and idx + 1 < len(tokens):
            day_token = tokens[idx + 1].strip(",.?!")
            if day_token.isdigit():
                day = int(day_token)
                month = MONTH_MAP[clean]
                year = datetime.now().year
                return f"{year:04d}-{month:02d}-{day:02d}"
    return None


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _score_text(query: str, text: str) -> float:
    return SequenceMatcher(None, _normalise(query), _normalise(text)).ratio()


def search_entries(query: str, entries: Iterable[JournalEntry], *, limit: int = 5) -> List[MemoryHit]:
    query = query.strip()
    if not query:
        return []
    date_hint = _extract_date_hint(query)
    hits: List[MemoryHit] = []
    for entry in entries:
        score = _score_text(query, entry.content)
        if entry.tags:
            score = max(score, _score_text(query, " ".join(entry.tags)))
        matched_date = False
        if date_hint and entry.date == date_hint:
            matched_date = True
            score += 0.15
        if score < 0.15:
            continue
        hits.append(MemoryHit(entry=entry, score=score, matched_date=matched_date))
    hits.sort(key=lambda hit: hit.score, reverse=True)
    return hits[:limit]


__all__ = ["MemoryHit", "search_entries"]
