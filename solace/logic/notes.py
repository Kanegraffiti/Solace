import json
from pathlib import Path
from typing import List, Dict, Iterable

from ..utils.datetime import ts_to_filename
from ..utils.encryption import encrypt_bytes, decrypt_bytes
from ..utils.keys import get_key

BASE_DIR = Path(__file__).resolve().parents[2] / 'storage' / 'notes'


def add_note(title: str, content: str, timestamp: str, tags: Iterable[str] | None = None, private: bool = False) -> Path:
    """Save a markdown note and return its path."""
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    tags = list(tags or [])
    fname = BASE_DIR / f"{ts_to_filename(timestamp)}.md"
    header = [
        f"Title: {title}",
        f"Date: {timestamp}",
        f"Tags: {' '.join(tags)}" if tags else 'Tags:',
        "---",
        content,
    ]
    text = "\n".join(header)
    if private:
        key = get_key()
        data = encrypt_bytes(text.encode('utf-8'), key)
        fname = fname.with_suffix('.enc')
        with fname.open('wb') as f:
            f.write(data)
    else:
        with fname.open('w', encoding='utf-8') as f:
            f.write(text)
    return fname


def load_notes() -> List[Dict]:
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    notes: List[Dict] = []
    for fpath in sorted(BASE_DIR.glob('*')):
        if fpath.suffix not in {'.md', '.enc'}:
            continue
        if fpath.suffix == '.enc':
            data = decrypt_bytes(fpath.read_bytes(), get_key()).decode('utf-8')
        else:
            data = fpath.read_text(encoding='utf-8')
        lines = data.splitlines()
        meta = {'title': '', 'timestamp': '', 'tags': []}
        body_start = 0
        for i, line in enumerate(lines):
            if line.startswith('Title:'):
                meta['title'] = line[6:].strip()
            elif line.startswith('Date:'):
                meta['timestamp'] = line[5:].strip()
            elif line.startswith('Tags:'):
                meta['tags'] = line[5:].split()
            elif line.strip() == '---':
                body_start = i + 1
                break
        meta['text'] = "\n".join(lines[body_start:]).strip()
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
