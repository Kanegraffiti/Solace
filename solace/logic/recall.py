import json
from pathlib import Path
from typing import List, Dict

from .notes import load_notes

DIARY_DIR = Path(__file__).resolve().parents[2] / 'storage' / 'diary'


def _load_diary_entries() -> List[Dict]:
    DIARY_DIR.mkdir(parents=True, exist_ok=True)
    entries: List[Dict] = []
    for fpath in sorted(DIARY_DIR.glob('*.txt')):
        with fpath.open('r', encoding='utf-8') as f:
            first = f.readline().strip()
            try:
                meta = json.loads(first)
            except json.JSONDecodeError:
                meta = {'timestamp': fpath.stem}
            text = f.read().strip()
        meta['text'] = text
        entries.append(meta)
    return entries


def search(query: str) -> List[Dict]:
    q = query.lower()
    results: List[Dict] = []
    for item in _load_diary_entries() + load_notes():
        text = item.get('text', '').lower()
        tags = [t.lower() for t in item.get('tags', [])]
        if q.startswith('#'):
            if q[1:] in tags:
                results.append(item)
        elif q in text or any(q in t for t in tags):
            results.append(item)
    results.sort(key=lambda x: x.get('timestamp', ''))
    return results
