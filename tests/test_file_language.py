from pathlib import Path

from solace.file_skill import FileManager, parse_intent


def test_conversational_find_and_rename_requests() -> None:
    find_intent = parse_intent("Where is my invoice.pdf?")
    rename_intent = parse_intent("Let's rename draft.pdf to final.pdf")
    polite_intent = parse_intent("please move report.xlsx to ~/Documents")

    assert find_intent is not None
    assert find_intent.action == "find"
    assert find_intent.query == "invoice.pdf"

    assert rename_intent is not None
    assert rename_intent.action == "rename"
    assert rename_intent.source == "draft.pdf"
    assert rename_intent.destination == "final.pdf"

    assert polite_intent is not None
    assert polite_intent.action == "move"
    assert polite_intent.source == "report.xlsx"


def test_normal_search_does_not_surface_solace_trash(tmp_path: Path) -> None:
    manager = FileManager(home=tmp_path, search_roots=[tmp_path], state_dir=tmp_path / ".solace")
    source = tmp_path / "private-note.txt"
    source.write_text("keep", encoding="utf-8")

    trashed = manager.trash(source)

    assert trashed.exists()
    assert manager.find("private-note.txt") == []
    assert len(manager.trashed("private-note.txt")) == 1
