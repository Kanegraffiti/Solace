from pathlib import Path

import pytest

from solace.english_editor import MAX_TEXT_BYTES, edit_english, edit_english_file


def test_edits_common_english_errors_and_explains_changes():
    result = edit_english("i dont know why she dont like it;it is more better now")

    assert result.corrected == "I don't know why she doesn't like it; it is better now"
    assert result.original == "i dont know why she dont like it;it is more better now"
    assert {edit.reason for edit in result.edits} >= {
        "capitalised the pronoun “I”",
        "restored a missing apostrophe",
        "corrected subject–verb agreement",
        "removed a double comparative",
    }


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("I didn't went there", "I didn't go there"),
        ("They is ready", "They are ready"),
        ("She have the notes", "She has the notes"),
        ("this is fine. it works", "This is fine. It works"),
        ("Hello ,world!how are you?", "Hello, world! How are you?"),
    ],
)
def test_targeted_grammar_rules(source, expected):
    assert edit_english(source).corrected == expected


def test_clean_text_is_unchanged():
    result = edit_english("This sentence is already clear.")

    assert result.corrected == result.original
    assert result.edits == []


def test_file_edit_creates_new_copy_and_preserves_original(tmp_path):
    source = tmp_path / "notes.txt"
    source.write_text("i has the notes", encoding="utf-8")

    edited = edit_english_file(source)

    assert edited.output == tmp_path / "notes.grammar-edited.txt"
    assert edited.output.read_text(encoding="utf-8") == "I have the notes"
    assert source.read_text(encoding="utf-8") == "i has the notes"


def test_file_edit_never_overwrites_previous_output(tmp_path):
    source = tmp_path / "notes.md"
    source.write_text("she have it", encoding="utf-8")
    (tmp_path / "notes.grammar-edited.md").write_text("keep me", encoding="utf-8")

    edited = edit_english_file(source)

    assert edited.output.name == "notes.grammar-edited-2.md"
    assert (tmp_path / "notes.grammar-edited.md").read_text(encoding="utf-8") == "keep me"


def test_file_edit_rejects_unsupported_or_oversized_input(tmp_path):
    unsupported = tmp_path / "notes.docx"
    unsupported.write_text("i has notes", encoding="utf-8")
    with pytest.raises(ValueError, match=".txt and .md"):
        edit_english_file(unsupported)

    oversized = tmp_path / "large.txt"
    oversized.write_bytes(b"x" * (MAX_TEXT_BYTES + 1))
    with pytest.raises(ValueError, match="larger"):
        edit_english_file(oversized)


def test_file_edit_rejects_non_utf8(tmp_path):
    source = Path(tmp_path) / "notes.txt"
    source.write_bytes(b"\xff\xfe\x00")

    with pytest.raises(ValueError, match="UTF-8"):
        edit_english_file(source)
