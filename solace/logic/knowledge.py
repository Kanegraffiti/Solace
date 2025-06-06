import json
from pathlib import Path
from typing import Iterable

from ..utils.datetime import ts_to_filename
from ..utils.encryption import encrypt_bytes, decrypt_bytes
from ..utils.keys import get_key
from ..utils.storage import KNOWLEDGE_DIR, update_tags_index


def save_entry(topic: str, timestamp: str, type_: str, content: str,
               tags: Iterable[str] | None = None, private: bool = False) -> Path:
    """Save a knowledge entry as a JSON file."""
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    tags = list(tags or [])
    fname = KNOWLEDGE_DIR / ts_to_filename(timestamp)
    data = {
        'topic': topic,
        'timestamp': timestamp,
        'type': type_,
        'tags': tags,
        'content': content,
    }
    json_text = json.dumps(data, indent=2)
    if private:
        key = get_key()
        enc = encrypt_bytes(json_text.encode('utf-8'), key)
        fname = fname.with_suffix('.enc')
        with fname.open('wb') as f:
            f.write(enc)
    else:
        fname = fname.with_suffix('.json')
        with fname.open('w', encoding='utf-8') as f:
            f.write(json_text)
    update_tags_index(tags, fname)
    return fname


def load_entry(path: Path, key: bytes | None = None) -> dict:
    """Load a knowledge entry from ``path``."""
    if path.suffix == '.enc':
        key = key or get_key()
        data = decrypt_bytes(path.read_bytes(), key).decode('utf-8')
    else:
        data = path.read_text(encoding='utf-8')
    return json.loads(data)
