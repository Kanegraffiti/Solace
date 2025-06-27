import json
from pathlib import Path

from ..utils.storage import load_entries, save_entries
from ..logic.emotion import detect_mood
from ..utils.datetime import ts_to_filename
from getpass import getpass

from ..settings_manager import SETTINGS
from ..utils.crypto_manager import encrypt_data


def add_entry(text: str, timestamp: str, tags=None, important=False, private=False):
    mood = detect_mood(text)
    entries = load_entries()
    entries.append({'text': text, 'mood': mood, 'timestamp': timestamp, 'tags': tags or [], 'important': important, 'private': private})
    save_entries(entries)

    # also save individual file for quick retrieval
    diary_dir = Path(__file__).resolve().parents[2] / 'storage' / 'diary'
    diary_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        'timestamp': timestamp,
        'tags': tags or [],
        'important': important,
        'mood': mood,
    }
    fname = diary_dir / ts_to_filename(timestamp)
    use_enc = SETTINGS.get("encryption_enabled", False) or private
    if use_enc:
        data = json.dumps(meta) + '\n' + text
        password = getpass("Encryption password: ")
        token = encrypt_data(data, password)
        fname = fname.with_suffix('.solace')
        with fname.open('w', encoding='utf-8') as f:
            json.dump({"version": 1, "data": token}, f)
    else:
        fname = fname.with_suffix('.txt')
        with fname.open('w', encoding='utf-8') as f:
            f.write(json.dumps(meta) + '\n')
            f.write(text)

    return mood
