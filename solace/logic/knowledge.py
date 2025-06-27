import json
from pathlib import Path
from typing import Iterable
from getpass import getpass

from ..settings_manager import SETTINGS
from ..utils.crypto_manager import encrypt_data, decrypt_data

from ..utils.datetime import ts_to_filename
from ..utils.storage import KNOWLEDGE_DIR, update_tags_index


def save_entry(topic: str, timestamp: str, type_: str, content: str,
               tags: Iterable[str] | None = None,
               private: bool = False,
               password: str | None = None) -> Path:
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
    use_enc = SETTINGS.get("encryption_enabled", False) or private
    if use_enc:
        if password is None:
            password = getpass("Encryption password: ")
        token = encrypt_data(json_text, password)
        fname = fname.with_suffix('.solace')
        with fname.open('w', encoding='utf-8') as f:
            json.dump({"version": 1, "data": token}, f)
    else:
        fname = fname.with_suffix('.json')
        with fname.open('w', encoding='utf-8') as f:
            f.write(json_text)
    update_tags_index(tags, fname)
    return fname


def load_entry(path: Path, password: str | None = None) -> dict:
    """Load a knowledge entry from ``path``."""
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
        from ..utils.keys import get_key
        from ..utils.encryption import decrypt_bytes
        key = get_key()
        data = decrypt_bytes(path.read_bytes(), key).decode("utf-8")
    else:
        data = path.read_text(encoding="utf-8")
    return json.loads(data)


def migrate_unencrypted(password: str) -> int:
    """Encrypt old unencrypted knowledge entries."""
    count = 0
    for path in KNOWLEDGE_DIR.glob('*.json'):
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            continue
        save_entry(
            data.get('topic', ''),
            data.get('timestamp', ''),
            data.get('type', ''),
            data.get('content', ''),
            data.get('tags', []),
            private=True,
            password=password,
        )
        path.unlink()
        count += 1
    return count
