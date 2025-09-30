"""Persona mimic helper that mirrors the user's journal tone."""
from __future__ import annotations

import random
from collections import Counter
from typing import List

from journal import latest_entries

GREETING_CHOICES = [
    "It's your Solace echo speaking.",
    "Hey, I'm the version of you built from your notes.",
    "Your journaling twin checking in.",
]


def _collect_keywords(entries: List[dict]) -> List[str]:
    words: List[str] = []
    for entry in entries:
        for word in entry.get("text", "").split():
            cleaned = word.strip().strip(".,!?;:()[]{}\"'")
            if len(cleaned) < 4:
                continue
            words.append(cleaned.lower())
    return words


def reply(prompt: str) -> str:
    """Generate a short reply using the recent journal tone."""
    entries = latest_entries(10)
    if not entries:
        return "I need a few journal entries to learn your voice first."

    keywords = _collect_keywords(entries)
    counts = Counter(keywords)
    trending = ", ".join(word for word, _ in counts.most_common(3)) or "thoughts"

    intro = random.choice(GREETING_CHOICES)
    bridge = prompt.strip() or "what's on your mind"
    sample = random.choice(entries)
    snippet = sample.get("text", "").split(". ")[0]

    return (
        f"{intro}\n"
        f"I can hear how often you mention {trending}.\n"
        f"In your recent note you said: '{snippet}'.\n"
        f"So about {bridge}, I'd say stay true to that energy."
    )
