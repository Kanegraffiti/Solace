import json
from pathlib import Path

from ..utils.storage import load_entries, save_entries
from ..logic.emotion import detect_mood
from ..utils.datetime import ts_to_filename


def add_entry(text: str, timestamp: str, tags=None, important=False):
    mood = detect_mood(text)
    entries = load_entries()
    entries.append({'text': text, 'mood': mood, 'timestamp': timestamp, 'tags': tags or [], 'important': important})
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
    fname = diary_dir / f"{ts_to_filename(timestamp)}.txt"
    with fname.open('w', encoding='utf-8') as f:
        f.write(json.dumps(meta) + '\n')
        f.write(text)

    return mood
