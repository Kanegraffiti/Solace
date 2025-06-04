from ..utils.storage import load_entries
from ..logic.mimic import mimic_reply


class ChatLockedError(Exception):
    pass


MIN_ENTRIES = 10


def chat(prompt: str) -> str:
    entries = load_entries()
    if len(entries) < MIN_ENTRIES:
        raise ChatLockedError('Not enough diary entries to unlock chat.')
    return mimic_reply(prompt)
