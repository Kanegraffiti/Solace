from ..logic.mimic import MIN_CLONE_ENTRIES, build_profile, mimic_reply


class ChatLockedError(Exception):
    def __init__(self, message: str, entry_count: int, required: int) -> None:
        super().__init__(message)
        self.entry_count = entry_count
        self.required = required


def chat(prompt: str) -> str:
    profile = build_profile()
    if not profile.ready:
        message = profile.incubation_message or "Not enough diary entries to unlock chat."
        raise ChatLockedError(message, profile.entry_count, MIN_CLONE_ENTRIES)
    return mimic_reply(prompt, profile)
