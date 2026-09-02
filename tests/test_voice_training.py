import json
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from solace.voice_training import (
    VoiceTrainingError,
    clean_message,
    make_summary,
    parse_transcript,
    participants,
    read_transcript,
    save_voice_dataset,
    selected_reviews,
)

WHATSAPP_EXPORT = """01/09/2026, 10:20 - Anna: Heyyy 😅
01/09/2026, 10:21 - Friend: Hello dear
01/09/2026, 10:22 - Anna: Email me at anna@example.com or call +234 801 234 5678
continued thought
01/09/2026, 10:23 - Anna: <Media omitted>
"""


def test_parse_whatsapp_selects_one_speaker_and_joins_multiline() -> None:
    messages = parse_transcript(WHATSAPP_EXPORT)

    assert participants(messages) == [("Anna", 2), ("Friend", 1)]
    reviews = selected_reviews(messages, "Anna")
    assert reviews[0].cleaned == "Heyyy 😅"
    assert "continued thought" in reviews[1].original


def test_parse_bracketed_and_plain_transcripts() -> None:
    bracketed = parse_transcript("[01/09/2026, 10:20:30] Anna: Hello\n[01/09/2026, 10:21:00] Jo: Hi")
    plain = parse_transcript("Anna: Hello\nJo: Hi")

    assert [message.speaker for message in bracketed] == ["Anna", "Jo"]
    assert [message.text for message in plain] == ["Hello", "Hi"]


def test_clean_message_redacts_identifiers_and_flags_sensitive_text() -> None:
    review = clean_message(
        "My bank email is anna@example.com, call +234 801 234 5678 and visit https://example.com/private"
    )

    assert "anna@example.com" not in review.cleaned
    assert "+234 801 234 5678" not in review.cleaned
    assert "https://example.com/private" not in review.cleaned
    assert {"email", "phone_or_account_number", "url", "financial"}.issubset(review.flags)


def test_save_dataset_encrypts_examples_and_report_contains_no_messages(tmp_path: Path) -> None:
    cipher = Fernet(Fernet.generate_key())
    reviews = [clean_message("Heyyy there 😅"), clean_message("anna@example.com")]
    approved = ["Heyyy there 😅", "[EMAIL]"]
    summary = make_summary("Anna", reviews, approved, removed=0, source_messages=4)

    destination = save_voice_dataset(tmp_path, "Anna", approved, summary, cipher)

    encrypted = (destination / "approved_examples.enc").read_bytes()
    assert b"Heyyy" not in encrypted
    assert json.loads(cipher.decrypt(encrypted).decode("utf-8")) == approved
    report = (destination / "import_report.json").read_text(encoding="utf-8")
    assert "Heyyy" not in report
    assert "anna@example.com" not in report


def test_invalid_or_oversized_transcript_is_refused(tmp_path: Path, monkeypatch) -> None:
    invalid = tmp_path / "chat.csv"
    invalid.write_text("Anna: hello", encoding="utf-8")
    with pytest.raises(VoiceTrainingError, match=".txt format"):
        read_transcript(invalid)

    transcript = tmp_path / "chat.txt"
    transcript.write_text("Anna: hello", encoding="utf-8")
    monkeypatch.setattr("solace.voice_training.MAX_TRANSCRIPT_BYTES", 2)
    with pytest.raises(VoiceTrainingError, match="25 MB"):
        read_transcript(transcript)


def test_empty_approved_dataset_is_not_created(tmp_path: Path) -> None:
    cipher = Fernet(Fernet.generate_key())
    summary = make_summary("Anna", [], [], removed=1, source_messages=1)

    with pytest.raises(VoiceTrainingError, match="No approved messages"):
        save_voice_dataset(tmp_path, "Anna", [], summary, cipher)

    assert not (tmp_path / "voice").exists()


def test_existing_approved_dataset_is_never_overwritten(tmp_path: Path) -> None:
    cipher = Fernet(Fernet.generate_key())
    reviews = [clean_message("Original style")]
    first = make_summary("Anna", reviews, ["Original style"], 0, 1)
    destination = save_voice_dataset(tmp_path, "Anna", ["Original style"], first, cipher)
    original = (destination / "approved_examples.enc").read_bytes()
    second = make_summary("Anna", reviews, ["Replacement"], 0, 1)

    with pytest.raises(VoiceTrainingError, match="Nothing was overwritten"):
        save_voice_dataset(tmp_path, "Anna", ["Replacement"], second, cipher)

    assert (destination / "approved_examples.enc").read_bytes() == original
