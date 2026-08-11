from datetime import datetime


def _entry(journal_module, text: str, *, encrypted: bool = False):
    return journal_module.JournalEntry(
        identifier=text,
        entry_type="diary",
        timestamp=datetime(2026, 8, 10, 12, 0).isoformat(),
        date="2026-08-10",
        time="12:00",
        content=text,
        tags=[],
        encrypted=encrypted,
        metadata={},
    )


def test_companion_grounds_conversation_in_dated_memory(reload_modules):
    journal = reload_modules["journal"]
    from solace.logic.companion import respond

    response = respond("deployment decision", [_entry(journal, "The deployment decision is to ship on Friday.")])

    assert response.memories
    assert "2026-08-10" in response.text
    assert "ship on Friday" in response.text


def test_companion_routes_python_questions_without_execution(reload_modules):
    journal = reload_modules["journal"]
    from solace.logic.companion import respond

    response = respond("python read a text file", [_entry(journal, "I am learning Python.")])

    assert response.kind == "python"
    assert "Path" in response.text


def test_companion_never_uses_still_encrypted_content(reload_modules):
    journal = reload_modules["journal"]
    from solace.logic.companion import respond

    response = respond("private launch code", [_entry(journal, "private launch code is swordfish", encrypted=True)])

    assert not response.memories
    assert "swordfish" not in response.text
