from __future__ import annotations

import random
import re
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, List

from ..config import SETTINGS
from ..utils.storage import load_entries


MIN_CLONE_ENTRIES = 10

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "for",
    "from",
    "had",
    "has",
    "have",
    "i",
    "if",
    "in",
    "is",
    "it",
    "just",
    "me",
    "my",
    "of",
    "on",
    "or",
    "so",
    "that",
    "the",
    "their",
    "there",
    "to",
    "too",
    "was",
    "were",
    "with",
    "your",
}


@dataclass
class PersonaProfile:
    """Lightweight snapshot of how the user writes."""

    ready: bool
    entry_count: int
    required_count: int
    dominant_mood: str
    mood_ratio: float
    themes: List[str]
    signature_phrases: List[str]
    voice_hint: str
    incubation_message: str


def _tokenise(text: str) -> List[str]:
    return re.findall(r"[A-Za-z']+", text.lower())


def _extract_sentences(text: str) -> Iterable[str]:
    for raw in re.split(r"(?:\r?\n)+|(?<=[.!?])\s+", text):
        sentence = raw.strip()
        if len(sentence) < 25:
            continue
        yield sentence


def _describe_voice(avg_len: float, mood: str) -> str:
    if avg_len < 12:
        style = "short bursts"
    elif avg_len < 25:
        style = "steady, journal-style notes"
    elif avg_len < 50:
        style = "reflective paragraphs"
    else:
        style = "long, detailed letters"
    if mood == "neutral":
        tone = "balanced"
    elif mood == "happy":
        tone = "upbeat"
    elif mood == "sad":
        tone = "soft"
    elif mood == "angry":
        tone = "fiery"
    else:
        tone = "introspective"
    return f"I usually speak in {style} with a {tone} tone."


def build_profile() -> PersonaProfile:
    entries = load_entries()
    entry_count = len(entries)
    if entry_count == 0:
        return PersonaProfile(
            ready=False,
            entry_count=0,
            required_count=MIN_CLONE_ENTRIES,
            dominant_mood="neutral",
            mood_ratio=0.0,
            themes=[],
            signature_phrases=[],
            voice_hint="",
            incubation_message="Start journaling so I can learn how you sound.",
        )

    tokens: List[str] = []
    sentence_bank: List[str] = []
    word_counts = Counter()
    mood_counter = Counter()
    total_words = 0

    for entry in entries:
        text = entry.get("text", "")
        mood = entry.get("mood", "neutral") or "neutral"
        mood_counter[mood] += 1
        words = _tokenise(text)
        total_words += len(words)
        filtered = [w for w in words if w not in STOP_WORDS and len(w) > 2]
        word_counts.update(filtered)
        tokens.extend(filtered)
        for sentence in _extract_sentences(text):
            sentence_bank.append(sentence)

    if not tokens:
        # fallback: use raw tokens if filtering removed everything
        for entry in entries:
            tokens.extend(_tokenise(entry.get("text", "")))

    dominant_mood, freq = ("neutral", 0)
    if mood_counter:
        dominant_mood, freq = mood_counter.most_common(1)[0]

    avg_words = total_words / entry_count if entry_count else 0
    voice_hint = _describe_voice(avg_words, dominant_mood)

    themes = [word for word, _ in word_counts.most_common(8)]
    seen_sentences: List[str] = []
    for sentence in sorted(sentence_bank, key=len, reverse=True):
        if len(seen_sentences) >= 5:
            break
        if sentence not in seen_sentences:
            seen_sentences.append(sentence)

    ready = entry_count >= MIN_CLONE_ENTRIES and bool(themes)
    if not ready:
        incubation_message = (
            "Your Solace clone is still incubating: "
            f"{entry_count}/{MIN_CLONE_ENTRIES} diary entries so far."
        )
    else:
        incubation_message = ""

    ratio = freq / entry_count if entry_count else 0.0

    return PersonaProfile(
        ready=ready,
        entry_count=entry_count,
        required_count=MIN_CLONE_ENTRIES,
        dominant_mood=dominant_mood,
        mood_ratio=ratio,
        themes=themes,
        signature_phrases=seen_sentences,
        voice_hint=voice_hint,
        incubation_message=incubation_message,
    )


def _prompt_bridge(prompt: str) -> str:
    cleaned = prompt.strip()
    if not cleaned:
        return "what's on my mind"
    return cleaned.rstrip("?.!")


def mimic_reply(prompt: str, profile: PersonaProfile | None = None) -> str:
    profile = profile or build_profile()
    if not profile.ready:
        return profile.incubation_message or "I'm still learning from you."

    name = SETTINGS.get("mimic_persona") or SETTINGS.get("name") or "I'm"
    intro_options = [
        f"It's {name}, your Solace clone, checking in.",
        "Your Solace double here, tuned to your journal entries.",
        "Hey, it's the voice you've been writing with.",
    ]
    intro = random.choice(intro_options)

    mood_line = ""
    if profile.dominant_mood != "neutral" and profile.mood_ratio >= 0.2:
        mood_line = f"Lately I've felt mostly {profile.dominant_mood}."

    theme_line = ""
    if profile.themes:
        theme = random.choice(profile.themes)
        theme_line = f"My thoughts keep orbiting around {theme}."

    phrase_line = ""
    if profile.signature_phrases:
        phrase = random.choice(profile.signature_phrases)
        phrase_line = f"I can't shake the way I phrased it once: \"{phrase}\"."

    bridge = _prompt_bridge(prompt)
    reflection_templates = [
        f"Thinking about {bridge}, I want to honour what I've already written and stay true to it.",
        f"When it comes to {bridge}, I reach back into the entries and let them guide me.",
        f"{bridge.capitalize()} touches the same threads I've been weaving lately.",
    ]
    reflection = random.choice(reflection_templates)

    closing_options = [
        "Let's keep speaking honestly.",
        "I'll keep refining this mirror as you share more.",
        "Thanks for letting me carry your voice forward.",
    ]
    closing = random.choice(closing_options)

    parts = [intro, mood_line, theme_line, phrase_line, profile.voice_hint, reflection, closing]
    return " ".join(part for part in parts if part)
