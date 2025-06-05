from pathlib import Path
import json
import re

DATA_FILE = Path(__file__).resolve().parents[2] / 'data' / 'convo_seed.json'


def _load_examples():
    try:
        with DATA_FILE.open('r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    return data.get('examples', [])


def _tokenize(text: str):
    return re.findall(r"\w+", text.lower())


def get_reply(message: str) -> str:
    """Return a conversational reply based on keyword matching."""
    examples = _load_examples()
    if not examples:
        return "I'm still learning. Try teaching me this in /mode teach."

    message_tokens = set(_tokenize(message))
    best_score = 0
    best_reply = None

    for ex in examples:
        prompt_tokens = set(_tokenize(ex.get('prompt', '')))
        overlap = len(prompt_tokens & message_tokens)
        if overlap > best_score:
            best_score = overlap
            best_reply = ex.get('response', '')

    if best_score > 0 and best_reply:
        return best_reply
    return "I'm still learning. Try teaching me this in /mode teach."
