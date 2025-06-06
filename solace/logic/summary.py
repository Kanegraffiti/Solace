from __future__ import annotations

import json

from ..utils.storage import DIARY_DIR
from .codegen import BASE_DIR, LANGUAGES
from .importer import DATA_FILE  # for imported knowledge
from .fallback import count_fallbacks


def count_diary_entries() -> int:
    if not DIARY_DIR.exists():
        return 0
    return len(list(DIARY_DIR.glob('*')))


def count_examples() -> int:
    total = 0
    for lang in LANGUAGES:
        path = BASE_DIR / lang / 'examples.json'
        if path.exists():
            try:
                total += len(json.loads(path.read_text(encoding='utf-8')))
            except json.JSONDecodeError:
                continue
    return total


def count_imported_facts() -> int:
    if not DATA_FILE.exists():
        return 0
    try:
        data = json.loads(DATA_FILE.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        return 0
    return len(data.get('facts', []))


def get_summary() -> dict[str, int]:
    return {
        'diary': count_diary_entries(),
        'examples': count_examples(),
        'knowledge': count_imported_facts(),
        'fallbacks': count_fallbacks(),
    }
