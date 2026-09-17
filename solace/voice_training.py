"""Local, review-first conversation import for Solace voice profiles."""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Sequence

from cryptography.fernet import Fernet

MAX_TRANSCRIPT_BYTES = 25 * 1024 * 1024
MAX_MESSAGES = 100_000

WHATSAPP_LINE = re.compile(
    r"^(?:\[)?\d{1,4}[/.\-]\d{1,2}[/.\-]\d{1,4},?\s+"
    r"\d{1,2}:\d{2}(?::\d{2})?\s*(?:[ap]m)?(?:\])?\s*(?:-|–)\s*([^:]+):\s?(.*)$",
    re.IGNORECASE,
)
BRACKETED_LINE = re.compile(
    r"^\[\d{1,4}[/.\-]\d{1,2}[/.\-]\d{1,4},?\s+"
    r"\d{1,2}:\d{2}(?::\d{2})?\s*(?:[ap]m)?\]\s*([^:]+):\s?(.*)$",
    re.IGNORECASE,
)
PLAIN_LINE = re.compile(r"^([^:\n]{1,80}):\s+(.+)$")

REDACTIONS = (
    ("email", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE), "[EMAIL]"),
    ("url", re.compile(r"\b(?:https?://|www\.)\S+", re.IGNORECASE), "[URL]"),
    (
        "phone_or_account_number",
        re.compile(r"(?<!\w)(?:\+?\d[\d\s()\-]{7,}\d)(?!\w)"),
        "[PRIVATE NUMBER]",
    ),
)
SENSITIVE_TERMS = {
    "account": "financial",
    "bank": "financial",
    "password": "secret",
    "pin": "secret",
    "otp": "secret",
    "hospital": "medical",
    "diagnosis": "medical",
    "pregnant": "medical",
    "sex": "sexual",
    "nude": "sexual",
    "kill": "violence",
    "suicide": "self-harm",
}
OFFENSIVE_TERMS = {
    "bitch",
    "bastard",
    "fuck",
    "idiot",
    "stupid",
}
SYSTEM_MESSAGES = {
    "<media omitted>",
    "image omitted",
    "video omitted",
    "audio omitted",
    "sticker omitted",
    "this message was deleted",
    "you deleted this message",
}


class VoiceTrainingError(RuntimeError):
    """Raised when a transcript cannot be processed safely."""


@dataclass(frozen=True)
class TranscriptMessage:
    speaker: str
    text: str


@dataclass(frozen=True)
class ReviewedMessage:
    original: str
    cleaned: str
    flags: Sequence[str]


@dataclass(frozen=True)
class ImportSummary:
    profile: str
    source_messages: int
    selected_messages: int
    approved_messages: int
    removed_messages: int
    redaction_counts: dict[str, int]
    created_at: str


def read_transcript(path: Path) -> str:
    """Read one bounded plain-text transcript without modifying it."""

    source = path.expanduser().resolve()
    if source.suffix.casefold() != ".txt" or not source.is_file():
        raise VoiceTrainingError("Choose an existing conversation transcript in .txt format.")
    if source.stat().st_size > MAX_TRANSCRIPT_BYTES:
        raise VoiceTrainingError("Transcript is larger than Solace's 25 MB import limit.")
    try:
        return source.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise VoiceTrainingError("Transcript is not valid UTF-8 text.") from exc


def parse_transcript(text: str) -> List[TranscriptMessage]:
    """Parse WhatsApp exports and simple ``Speaker: message`` transcripts."""

    messages: List[TranscriptMessage] = []
    for raw in text.splitlines():
        line = raw.strip("\ufeff\r")
        match = WHATSAPP_LINE.match(line) or BRACKETED_LINE.match(line) or PLAIN_LINE.match(line)
        if match:
            speaker, body = (value.strip() for value in match.groups())
            if body.casefold() not in SYSTEM_MESSAGES:
                messages.append(TranscriptMessage(speaker, body))
                if len(messages) > MAX_MESSAGES:
                    raise VoiceTrainingError("Transcript contains more than 100,000 messages.")
        elif messages and line.strip():
            previous = messages[-1]
            messages[-1] = TranscriptMessage(previous.speaker, previous.text + "\n" + line.strip())
    if not messages:
        raise VoiceTrainingError(
            "No supported messages were found. Export WhatsApp chat without media or use 'Name: message' lines."
        )
    return messages


def participants(messages: Iterable[TranscriptMessage]) -> List[tuple[str, int]]:
    counts = Counter(message.speaker for message in messages)
    return sorted(counts.items(), key=lambda item: (-item[1], item[0].casefold()))


def clean_message(text: str) -> ReviewedMessage:
    """Redact strong identifier patterns and flag uncertain sensitive content."""

    cleaned = text
    flags: List[str] = []
    for category, pattern, replacement in REDACTIONS:
        cleaned, count = pattern.subn(replacement, cleaned)
        if count:
            flags.extend([category] * count)
    words = {word.casefold() for word in re.findall(r"[A-Za-z']+", text)}
    flags.extend(sorted({SENSITIVE_TERMS[word] for word in words if word in SENSITIVE_TERMS}))
    if words.intersection(OFFENSIVE_TERMS):
        flags.append("offensive-language")
    return ReviewedMessage(text, cleaned.strip(), tuple(dict.fromkeys(flags)))


def selected_reviews(messages: Iterable[TranscriptMessage], speaker: str) -> List[ReviewedMessage]:
    return [clean_message(message.text) for message in messages if message.speaker == speaker]


def safe_profile_name(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    if not slug:
        raise VoiceTrainingError("Profile name must contain at least one letter or number.")
    return slug[:60]


def save_voice_dataset(
    root: Path,
    profile: str,
    approved: Sequence[str],
    summary: ImportSummary,
    cipher: Fernet,
) -> Path:
    """Encrypt approved examples and store only aggregate metadata in plaintext."""

    if not approved:
        raise VoiceTrainingError("No approved messages remain; nothing was saved.")
    profile_dir = root.expanduser() / "voice" / safe_profile_name(profile)
    dataset = profile_dir / "approved_examples.enc"
    if dataset.exists():
        raise VoiceTrainingError(
            "That voice profile already has an approved dataset. Nothing was overwritten."
        )
    profile_dir.mkdir(parents=True, exist_ok=True)
    encrypted = cipher.encrypt(json.dumps(list(approved), ensure_ascii=False).encode("utf-8"))
    dataset.write_bytes(encrypted)
    (profile_dir / "import_report.json").write_text(
        json.dumps(asdict(summary), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return profile_dir


def make_summary(
    profile: str,
    reviews: Sequence[ReviewedMessage],
    approved: Sequence[str],
    removed: int,
    source_messages: int,
) -> ImportSummary:
    counts = Counter(flag for review in reviews for flag in review.flags)
    return ImportSummary(
        profile=profile,
        source_messages=source_messages,
        selected_messages=len(reviews),
        approved_messages=len(approved),
        removed_messages=removed,
        redaction_counts=dict(sorted(counts.items())),
        created_at=datetime.now(timezone.utc).isoformat(),
    )


__all__ = [
    "ImportSummary",
    "ReviewedMessage",
    "TranscriptMessage",
    "VoiceTrainingError",
    "clean_message",
    "make_summary",
    "parse_transcript",
    "participants",
    "read_transcript",
    "safe_profile_name",
    "save_voice_dataset",
    "selected_reviews",
]
