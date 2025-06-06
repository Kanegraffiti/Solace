import json
from pathlib import Path

from ..utils.storage import load_entries, save_entries
from ..logic.emotion import detect_mood
from ..utils.datetime import ts_to_filename
from ..utils.encryption import encrypt_bytes
from ..utils.keys import get_key


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
    if private:
        data = json.dumps(meta) + '\n' + text
        enc = encrypt_bytes(data.encode('utf-8'), get_key())
        fname = fname.with_suffix('.enc')
        with fname.open('wb') as f:
            f.write(enc)
    else:
        fname = fname.with_suffix('.txt')
        with fname.open('w', encoding='utf-8') as f:
            f.write(json.dumps(meta) + '\n')
            f.write(text)

    return mood
