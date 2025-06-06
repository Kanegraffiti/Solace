from pathlib import Path
from typing import Iterable, List

from ..utils.datetime import ts_to_filename
from ..utils.encryption import encrypt_bytes, decrypt_bytes
from ..utils.keys import get_key
from ..utils.storage import DIARY_DIR, update_tags_index


def save_entry(title: str, timestamp: str, mood: str, content: str,
               tags: Iterable[str] | None = None, private: bool = False) -> Path:
    """Save a diary entry. Returns the file path."""
    DIARY_DIR.mkdir(parents=True, exist_ok=True)
    tags = list(tags or [])
    fname = DIARY_DIR / ts_to_filename(timestamp)
    header = [
        f"Title: {title}",
        f"Date: {timestamp}",
        f"Mood: {mood}",
        f"Tags: {' '.join(tags)}" if tags else "Tags:",
        "-------------------------",
        "",
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
        fname = fname.with_suffix('.txt')
        with fname.open('w', encoding='utf-8') as f:
            f.write(text)
    update_tags_index(tags, fname)
    return fname


def load_entry(path: Path, key: bytes | None = None) -> dict:
    """Load a diary entry from ``path``."""
    if path.suffix == '.enc':
        key = key or get_key()
        data = decrypt_bytes(path.read_bytes(), key).decode('utf-8')
    else:
        data = path.read_text(encoding='utf-8')
    lines = data.splitlines()
    meta = {
        'title': '',
        'timestamp': '',
        'mood': '',
        'tags': [],
    }
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith('Title:'):
            meta['title'] = line[6:].strip()
        elif line.startswith('Date:'):
            meta['timestamp'] = line[5:].strip()
        elif line.startswith('Mood:'):
            meta['mood'] = line[5:].strip()
        elif line.startswith('Tags:'):
            meta['tags'] = line[5:].split()
        elif line.startswith('-------------------------'):
            body_start = i + 1
            break
    meta['content'] = '\n'.join(lines[body_start:]).strip()
    return meta
