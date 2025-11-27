from datetime import datetime


def test_add_and_load_encrypted_entry(reload_modules):
    configuration = reload_modules["solace.configuration"]
    journal = reload_modules["journal"]

    config = configuration.load_config()
    cipher = configuration.get_cipher(config, password="seed")

    when = datetime(2024, 1, 2, 9, 30)
    entry = journal.add_entry(
        "Private thoughts",
        entry_type="diary",
        tags=["morning", "reflection"],
        when=when,
        cipher=cipher,
    )

    entries = journal.load_entries(cipher=cipher)
    assert len(entries) == 1
    loaded = entries[0]
    assert loaded.identifier == entry.identifier
    assert loaded.content == "Private thoughts"
    assert not loaded.encrypted

    unreadable = journal.load_entries(include_encrypted=False)
    assert unreadable == []


def test_export_to_markdown(reload_modules, tmp_path):
    configuration = reload_modules["solace.configuration"]
    journal = reload_modules["journal"]

    config = configuration.load_config()
    configuration.ensure_storage_dirs(config)
    when = datetime(2024, 2, 3, 18, 45)
    journal.add_entry(
        "Exportable content",
        entry_type="notes",
        tags=["share"],
        when=when,
    )

    destination = tmp_path / "journal.md"
    exported = journal.export_entries(destination)
    assert exported == destination

    content = destination.read_text(encoding="utf-8")
    assert "Exportable content" in content
    assert "# Solace journal export" in content
    assert "*Tags:* share" in content
    assert "Notes" in content
