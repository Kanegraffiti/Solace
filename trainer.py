"""Self-contained training and knowledge extraction utilities."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from solace.configuration import ensure_storage_dirs, get_storage_path, load_config

CONFIG = load_config()
ensure_storage_dirs(CONFIG)

TRAINING_ROOT = get_storage_path(CONFIG, "training")
BOOKS_DIR = TRAINING_ROOT / "books"
INDEX_FILE = TRAINING_ROOT / "index.json"
SESSIONS_DIR = TRAINING_ROOT / "sessions"

LANGUAGE_MAP = {
    "python": ["python", "py"],
    "bash": ["bash", "shell", "sh"],
    "html": ["html", "hypertext"],
    "javascript": ["javascript", "js"],
    "css": ["css", "styles"],
}


@dataclass
class KnowledgeSnippet:
    language: str
    category: str
    text: str
    source: str

    def serialise(self) -> Dict[str, str]:
        return asdict(self)


def _detect_language(block: str) -> Optional[str]:
    block_lower = block.lower()
    for lang, keywords in LANGUAGE_MAP.items():
        if any(keyword in block_lower for keyword in keywords):
            return lang
    return None


def _extract_snippets(text: str, source: str) -> Iterable[KnowledgeSnippet]:
    sections = re.split(r"\n{2,}", text)
    for section in sections:
        cleaned = section.strip()
        if not cleaned:
            continue
        language = _detect_language(cleaned)
        if not language:
            continue
        if re.search(r"^\s*(def |class |function |var |let |const )", cleaned, re.IGNORECASE | re.MULTILINE):
            yield KnowledgeSnippet(language, "example", cleaned, source)
        elif "error" in cleaned.lower():
            yield KnowledgeSnippet(language, "error", cleaned, source)
        elif "tip" in cleaned.lower() or "remember" in cleaned.lower():
            yield KnowledgeSnippet(language, "tip", cleaned, source)


def rebuild_index() -> List[KnowledgeSnippet]:
    BOOKS_DIR.mkdir(parents=True, exist_ok=True)
    snippets: List[KnowledgeSnippet] = []
    for book in BOOKS_DIR.glob("*.txt"):
        text = book.read_text(encoding="utf-8", errors="ignore")
        for snippet in _extract_snippets(text, source=book.name):
            snippets.append(snippet)
    INDEX_FILE.write_text(json.dumps([s.serialise() for s in snippets], indent=2), encoding="utf-8")
    return snippets


def load_index() -> List[KnowledgeSnippet]:
    if not INDEX_FILE.exists():
        return rebuild_index()
    try:
        data = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return rebuild_index()
    snippets = []
    for item in data:
        snippets.append(
            KnowledgeSnippet(
                language=item.get("language", "unknown"),
                category=item.get("category", "example"),
                text=item.get("text", ""),
                source=item.get("source", "unknown"),
            )
        )
    return snippets


def record_session(topic: str, notes: str, *, tags: Optional[List[str]] = None) -> Path:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    payload = {
        "topic": topic,
        "notes": notes,
        "tags": tags or [],
        "timestamp": timestamp,
    }
    path = SESSIONS_DIR / f"session-{timestamp}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def query(language: str, prompt: str, *, limit: int = 5) -> List[KnowledgeSnippet]:
    language = language.lower()
    snippets = load_index()
    matches: List[KnowledgeSnippet] = []
    for snippet in snippets:
        if snippet.language != language:
            continue
        if prompt.lower() in snippet.text.lower():
            matches.append(snippet)
    return matches[:limit]


def teach(language: str, content: str, *, category: str = "example") -> KnowledgeSnippet:
    snippet = KnowledgeSnippet(language=language, category=category, text=content, source="manual")
    snippets = load_index()
    snippets.append(snippet)
    INDEX_FILE.write_text(json.dumps([s.serialise() for s in snippets], indent=2), encoding="utf-8")
    return snippet


__all__ = [
    "KnowledgeSnippet",
    "LANGUAGE_MAP",
    "rebuild_index",
    "load_index",
    "record_session",
    "query",
    "teach",
]
