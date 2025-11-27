def build_entry(journal_module, content: str, date: str, tags=None):
    return journal_module.JournalEntry(
        identifier="id",
        entry_type="diary",
        timestamp=f"{date}T12:00:00",
        date=date,
        time="12:00",
        content=content,
        tags=tags or [],
        encrypted=False,
        metadata={},
    )


def test_search_matches_text_and_tags(reload_modules):
    journal = reload_modules["journal"]
    memory = reload_modules["solace.memory"]

    entries = [
        build_entry(journal, "A walk through the park", "2024-01-10"),
        build_entry(journal, "Grocery list", "2024-01-11", tags=["shopping", "errands"]),
    ]

    hits = memory.search_entries("park", entries)
    assert hits
    assert hits[0].entry.content.startswith("A walk")

    tag_hits = memory.search_entries("shopping", entries)
    assert tag_hits
    assert tag_hits[0].entry.tags == ["shopping", "errands"]


def test_search_prioritises_date_hint(reload_modules):
    journal = reload_modules["journal"]
    memory = reload_modules["solace.memory"]

    entries = [
        build_entry(journal, "First run", "2024-03-04"),
        build_entry(journal, "Second run", "2024-03-05"),
    ]

    hits = memory.search_entries("run 2024-03-05", entries)
    assert hits
    assert hits[0].entry.content == "Second run"
    assert hits[0].matched_date
