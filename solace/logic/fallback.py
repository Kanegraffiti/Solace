from __future__ import annotations

from pathlib import Path
import json
from typing import List

FALLBACK_FILE = Path(__file__).resolve().parents[2] / 'storage' / 'fallback_log.json'


def log_query(command: str, query: str) -> None:
    """Append a failed query to the fallback log."""
    FALLBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {'command': command, 'query': query}
    if FALLBACK_FILE.exists():
        try:
            data: List[dict] = json.loads(FALLBACK_FILE.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            data = []
    else:
        data = []
    data.append(entry)
    FALLBACK_FILE.write_text(json.dumps(data, indent=2), encoding='utf-8')


def count_fallbacks() -> int:
    if not FALLBACK_FILE.exists():
        return 0
    try:
        data = json.loads(FALLBACK_FILE.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        return 0
    return len(data)
