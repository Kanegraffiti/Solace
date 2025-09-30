"""Rule based conversation mimicry using offline guides."""

from __future__ import annotations

import json
from difflib import SequenceMatcher
from typing import Dict, List

from solace.configuration import get_storage_path, load_config

CONFIG = load_config()
GUIDE_FILE = get_storage_path(CONFIG, "conversation") / "guide.json"

DEFAULT_GUIDE = [
    {"trigger": ["hello", "hi", "hey"], "response": "Hello! It's good to hear from you."},
    {"trigger": ["how are you", "you ok"], "response": "I'm feeling thoughtful and ready to listen."},
    {"trigger": ["thank you", "thanks"], "response": "Always! Let me know what else you'd like to explore."},
    {"trigger": ["help", "what can you do"], "response": "You can ask me to journal, search memories, or teach code snippets."},
]


def _load_guide() -> List[Dict[str, List[str]]]:
    GUIDE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if GUIDE_FILE.exists():
        try:
            data = json.loads(GUIDE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass
    GUIDE_FILE.write_text(json.dumps(DEFAULT_GUIDE, indent=2), encoding="utf-8")
    return DEFAULT_GUIDE


GUIDE_DATA = _load_guide()


def _score(user_text: str, trigger: str) -> float:
    return SequenceMatcher(None, user_text.lower(), trigger.lower()).ratio()


def reply(user_text: str) -> str:
    user_text = user_text.strip()
    if not user_text:
        return "I need a bit more detail to respond."

    best_score = 0.0
    best_response = None
    for rule in GUIDE_DATA:
        triggers = rule.get("trigger") or []
        for trigger in triggers:
            score = _score(user_text, trigger)
            if score > best_score:
                best_score = score
                best_response = rule.get("response")

    if best_score < 0.45 or best_response is None:
        fallback_mode = CONFIG.get("memory", {}).get("fallback_mode", "apologise")
        if fallback_mode == "gentle":
            return "I'm not sure about that yet, but we can explore it together via /teach."
        if fallback_mode == "encourage":
            return "Teach me that phrase with /teach and I'll echo it back next time!"
        return "Sorry, I didn’t understand that yet. You can teach me using `/teach`."

    tone = CONFIG.get("tone", "friendly")
    if tone == "quiet":
        return best_response
    if tone == "verbose":
        return f"{best_response}\nLet me know if you want more detail or examples."
    return best_response


__all__ = ["reply"]
