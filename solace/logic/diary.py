from pathlib import Path
from typing import Iterable, List
import json

from getpass import getpass

from ..settings_manager import SETTINGS
from ..utils.crypto_manager import encrypt_data, decrypt_data
from ..utils.datetime import ts_to_filename
from ..utils.storage import DIARY_DIR, update_tags_index


def save_entry(title: str, timestamp: str, mood: str, content: str,
               tags: Iterable[str] | None = None,
               private: bool = False,
               password: str | None = None) -> Path:
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
    use_enc = SETTINGS.get("encryption_enabled", False) or private
    if use_enc:
        if password is None:
            password = getpass("Encryption password: ")
        token = encrypt_data(text, password)
        fname = fname.with_suffix('.solace')
        with fname.open('w', encoding='utf-8') as f:
            json.dump({"version": 1, "data": token}, f)
    else:
        fname = fname.with_suffix('.txt')
        with fname.open('w', encoding='utf-8') as f:
            f.write(text)
    update_tags_index(tags, fname)
    return fname


def load_entry(path: Path, password: str | None = None) -> dict:
    """Load a diary entry from ``path``."""
    if path.suffix == '.solace':
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
            enc = obj.get("data", "")
            if password is None:
                password = getpass("Encryption password: ")
            data = decrypt_data(enc, password)
        except Exception:
            raise ValueError(f"Failed to decrypt {path.name}")
    elif path.suffix == '.enc':
        from ..utils.keys import get_key  # legacy
        from ..utils.encryption import decrypt_bytes
        key = get_key()
        data = decrypt_bytes(path.read_bytes(), key).decode("utf-8")
    else:
        data = path.read_text(encoding="utf-8")
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


def migrate_unencrypted(password: str) -> int:
    """Encrypt legacy plain-text diary entries."""
    count = 0
    for path in DIARY_DIR.glob('*.txt'):
        entry = load_entry(path)
        save_entry(
            entry.get('title', ''),
            entry.get('timestamp', ''),
            entry.get('mood', ''),
            entry.get('content', ''),
            entry.get('tags', []),
            private=True,
            password=password,
        )
        path.unlink()
        count += 1
    return count
