"""Deterministic, offline conversation support for Solace.

The responder is intentionally small and inspectable. It does not pretend to
know live facts, invent a biography, or send conversation text to a service.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

EMOTION_GROUPS = {
    "distress": {"sad", "lonely", "hurt", "heartbroken", "miserable", "crying"},
    "pressure": {"anxious", "anxiety", "overwhelmed", "stressed", "worried", "afraid", "scared", "panic"},
    "frustration": {"angry", "annoyed", "frustrated", "irritated", "furious", "tired", "exhausted"},
    "positive": {"happy", "excited", "proud", "relieved", "grateful", "hopeful"},
}

CRISIS_PHRASES = ("kill myself", "end my life", "hurt myself", "self harm", "self-harm", "suicide")

LIVE_INFORMATION = {
    "weather",
    "news",
    "price",
    "prices",
    "score",
    "scores",
    "traffic",
    "exchange rate",
    "stock",
}


@dataclass
class ConversationState:
    """Small, in-memory context for one CLI chat session."""

    last_topic: str = ""
    last_emotion: str = ""
    last_question: str = ""
    turn_count: int = 0
    recent_replies: list[str] = field(default_factory=list)

    def remember(self, *, topic: str, emotion: str, reply: str) -> None:
        if topic:
            self.last_topic = topic
        if emotion:
            self.last_emotion = emotion
        self.last_question = _last_question(reply)
        self.turn_count += 1
        self.recent_replies.append(reply)
        del self.recent_replies[:-4]


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9']+", text.lower()))


def _has_phrase(text: str, phrases: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in phrases)


def _emotion(text: str) -> str:
    tokens = _tokens(text)
    for group, words in EMOTION_GROUPS.items():
        if tokens & words:
            return group
    return ""


def _topic(text: str) -> str:
    """Extract a short subject without claiming deeper language understanding."""

    cleaned = re.sub(r"\s+", " ", text.strip()).rstrip(".!?")
    for marker in (" about ", " because ", " with ", " over "):
        if marker in cleaned.lower():
            start = cleaned.lower().index(marker) + len(marker)
            candidate = cleaned[start:].strip()
            if candidate:
                return candidate[:100]

    cleaned = re.sub(
        r"^(?:honestly\s+|well\s+|so\s+)?"
        r"(?:should\s+i|what\s+should\s+i|i\s+am|i'm|i\s+feel|i\s+think|i\s+need|i\s+want|i)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    if not cleaned or cleaned.lower() in {"yes", "no", "okay", "ok", "maybe", "i don't know"}:
        return ""
    return cleaned[:100]


def _last_question(reply: str) -> str:
    questions = re.findall(r"[^?]+\?", reply)
    return questions[-1].strip() if questions else ""


def _apply_tone(reply: str, tone: str) -> str:
    if tone == "quiet":
        sentences = re.split(r"(?<=[.!?])\s+", reply)
        return " ".join(sentences[:2]).strip()
    if tone == "verbose" and "?" in reply:
        return reply + " We can take it one piece at a time; you do not need to explain everything perfectly."
    return reply


def _short_follow_up(text: str, state: ConversationState) -> str | None:
    lowered = text.lower().strip(" .!?")
    topic = state.last_topic or "it"
    if lowered in {"i don't know", "idk", "not sure", "i'm not sure"}:
        return f"That's okay. Let's make {topic} smaller: what is the first detail you feel sure about?"
    if lowered in {"maybe", "perhaps"}:
        return (
            f"The hesitation around {topic} may be useful. "
            "What is pulling you toward yes, and what is holding you back?"
        )
    if lowered in {"no", "nope", "not really"}:
        return f"Understood. We can leave that route. What would feel more useful around {topic}?"
    if lowered in {"yes", "yeah", "yep", "exactly"}:
        return f"All right. Tell me the part of {topic} you want us to focus on first."
    if lowered in {"okay", "ok", "alright"}:
        return f"All right. We can continue with {topic} whenever you're ready."
    return None


def _base_reply(text: str, name: str, state: ConversationState) -> tuple[str, str]:
    lowered = text.lower()
    tokens = _tokens(text)
    topic = _topic(text) or state.last_topic
    emotion = _emotion(text)

    if _has_phrase(lowered, CRISIS_PHRASES):
        return (
            "I'm glad you told me. Your immediate safety matters more than continuing this chat. "
            "Please contact local emergency services now, move toward a trusted person who can stay with you, "
            "and put distance between you and anything you could use to hurt yourself.",
            emotion,
        )

    follow_up = _short_follow_up(text, state)
    if follow_up:
        return follow_up, state.last_emotion

    if lowered in {"hi", "hello", "hey"} or lowered.startswith(("hi ", "hello ", "hey ")):
        if state.turn_count:
            previous = state.last_topic or "our last thought"
            return f"Hello again, {name}. Do you want to continue with {previous}, or start fresh?", ""
        return f"Hello, {name}. I'm here. What would you like to talk through?", ""

    if tokens & {"thanks", "thank", "appreciate"}:
        return "You're welcome. I'm glad that helped. Do you want to keep going or pause here?", "positive"

    if _has_phrase(lowered, ("i did it", "i finished", "it worked", "we won", "i succeeded")):
        subject = topic or "that"
        return f"You did it—{subject} sounds worth acknowledging. What helped it finally come together?", "positive"

    if emotion == "distress":
        subject = f" around {topic}" if topic else ""
        return (
            f"That sounds painful{subject}. Do you want comfort, help thinking it through, "
            "or simply room to say it fully?",
            emotion,
        )
    if emotion == "pressure":
        subject = f" with {topic}" if topic else ""
        return f"That sounds like a lot to hold{subject}. Which part feels most urgent right now?", emotion
    if emotion == "frustration":
        subject = f" about {topic}" if topic else ""
        return (
            f"I can hear the strain{subject}. Do you want to untangle what happened, "
            "or focus on the next practical move?",
            emotion,
        )
    if emotion == "positive":
        subject = f" about {topic}" if topic else ""
        return f"I'm glad{subject}. What part of this matters most to you?", emotion

    if _has_phrase(lowered, ("should i ", "what should i", "help me decide", "which should i")):
        return (
            f"Let's make the decision around {topic or 'this'} concrete. What are the options, "
            "and which constraint matters most—time, money, risk, or energy?",
            "",
        )

    if _has_phrase(lowered, ("i need to ", "i have to ", "my plan is", "help me plan")):
        return f"Let's turn {topic or 'that'} into a workable next step. What outcome must happen first?", ""

    if text.endswith("?"):
        if any(marker in lowered for marker in LIVE_INFORMATION):
            return (
                "I don't have live information in offline mode. If you give me the current facts, "
                "I can help you compare them or make a plan.",
                "",
            )
        return (
            "I don't know that reliably from local conversation data alone. "
            "Tell me what you already know, and I'll help you reason without pretending certainty.",
            "",
        )

    subject = topic or "that"
    return f"I hear you about {subject}. What changed, or what made it feel important today?", emotion


def offline_reply(
    message: str,
    *,
    name: str = "Friend",
    state: ConversationState | None = None,
    tone: str = "friendly",
) -> str:
    """Return a warm local reply and optionally update session-only context."""

    text = message.strip()
    state = state or ConversationState()
    if not text:
        reply = "I'm here. What would you like to write or talk through?"
        state.remember(topic="", emotion="", reply=reply)
        return _apply_tone(reply, tone)

    topic = _topic(text)
    reply, emotion = _base_reply(text, name, state)
    reply = _apply_tone(reply, tone)

    if reply in state.recent_replies and state.last_topic:
        reply = f"We're still with {state.last_topic}. What feels different about it now?"

    state.remember(topic=topic, emotion=emotion, reply=reply)
    return reply


def get_reply(message: str) -> str:
    """Backward-compatible entry point without invented seed biographies."""

    return offline_reply(message)


__all__ = ["ConversationState", "get_reply", "offline_reply"]
