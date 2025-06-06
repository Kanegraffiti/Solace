import json
from pathlib import Path
from typing import List, Dict

from ..config import ENABLE_TAGGING
from ..utils.datetime import ts_to_filename

BASE_DIR = Path(__file__).resolve().parents[2] / 'storage' / 'notes'


def add_note(text: str, timestamp: str, tags: List[str] | None = None, important: bool = False) -> Path:
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    tags = tags or []
    meta = {'timestamp': timestamp, 'tags': tags, 'important': important}
    fname = BASE_DIR / f"{ts_to_filename(timestamp)}.txt"
    with fname.open('w', encoding='utf-8') as f:
        f.write(json.dumps(meta) + '\n')
        f.write(text)
    return fname


def load_notes() -> List[Dict]:
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    notes: List[Dict] = []
    for fpath in sorted(BASE_DIR.glob('*.txt')):
        with fpath.open('r', encoding='utf-8') as f:
            first = f.readline().strip()
            try:
                meta = json.loads(first)
            except json.JSONDecodeError:
                meta = {'timestamp': fpath.stem}
            text = f.read().strip()
        meta['text'] = text
        notes.append(meta)
    return notes


def search_notes(query: str) -> List[Dict]:
    notes = load_notes()
    q = query.lower()
    results = []
    for n in notes:
        text = n.get('text', '').lower()
        tags = [t.lower() for t in n.get('tags', [])]
        if q.startswith('#'):
            if q[1:] in tags:
                results.append(n)
        elif q in text or any(q in t for t in tags):
            results.append(n)
    return results
