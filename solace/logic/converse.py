import json
import re
from pathlib import Path

# path to bundled seed conversations
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
        return "I'm not sure how to respond to that, but I'm here for you."

    message_tokens = set(_tokenize(message))
    best_score = 0
    best_reply = None

    for ex in examples:
        prompt = ex.get('prompt', '')
        if prompt.lower() in message.lower():
            return ex.get('response', '')

    for ex in examples:
        prompt_tokens = set(_tokenize(ex.get('prompt', '')))
        overlap = len(prompt_tokens & message_tokens)
        if overlap > best_score:
            best_score = overlap
            best_reply = ex.get('response', '')

    if best_score > 0 and best_reply:
        return best_reply
    return "I'm not sure how to respond to that, but I'm here for you."


def offline_reply(message: str, *, name: str = "Friend") -> str:
    """Respond locally without pretending to be a person or network service."""
    text = message.strip()
    lowered = text.lower()
    if not text:
        return "I'm here. What would you like to write or talk through?"
    if any(word in lowered for word in ("suicide", "kill myself", "self harm", "hurt myself")):
        return (
            "I'm glad you told me. I can't provide emergency help: please contact local emergency services "
            "or a crisis line now, and reach out to someone you trust who can stay with you."
        )
    if any(word in lowered for word in ("sad", "upset", "lonely", "overwhelmed", "anxious")):
        return "That sounds difficult. Would it help to name what happened and what you need most right now?"
    if lowered in {"hi", "hello", "hey"} or lowered.startswith(("hi ", "hello ", "hey ")):
        return f"Hello, {name}. I'm here with you. What's on your mind?"
    if text.endswith("?"):
        if any(word in lowered for word in ("weather", "news", "price", "score")):
            return "I don't have live information offline. I can help you record a plan or reason from facts you provide."
        seeded = get_reply(text)
        if not seeded.startswith("I'm not sure"):
            return seeded
        return "I don't know that reliably offline yet. I can still help you reason through it or save your thoughts."
    return "I hear you. What feels most important about that?"
