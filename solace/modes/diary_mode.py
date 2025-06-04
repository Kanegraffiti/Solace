from ..utils.storage import load_entries, save_entries
from ..logic.emotion import detect_mood


def add_entry(text: str):
    mood = detect_mood(text)
    entries = load_entries()
    entries.append({'text': text, 'mood': mood})
    save_entries(entries)
    return mood
