from pathlib import Path

import pytest

from solace.file_skill import FileManager, UnsafePathError, parse_intent


def _manager(tmp_path: Path) -> FileManager:
    return FileManager(home=tmp_path, search_roots=[tmp_path], state_dir=tmp_path / ".solace")


def test_parse_high_level_file_commands() -> None:
    rename = parse_intent("rename draft report.pdf to final report.pdf")
    copy = parse_intent("copy photo.jpg to ~/Documents")
    find = parse_intent("find my invoice")
    delete = parse_intent("delete old budget.xlsx")

    assert rename is not None and rename.action == "rename"
    assert rename.source == "draft report.pdf"
    assert rename.destination == "final report.pdf"
    assert copy is not None and copy.action == "copy"
    assert find is not None and find.query == "invoice"
    assert delete is not None and delete.action == "trash"


def test_find_rename_move_copy_and_history(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    source = tmp_path / "draft report.pdf"
    source.write_text("report", encoding="utf-8")
    destination_dir = tmp_path / "Documents"
    destination_dir.mkdir()

    matches = manager.find("draft report")
    assert matches == [source.resolve()]

    renamed = manager.rename(source, "final report.pdf")
    assert renamed.name == "final report.pdf"
    assert renamed.exists()

    copied = manager.copy(renamed, str(destination_dir))
    assert copied == (destination_dir / "final report.pdf").resolve()
    assert copied.read_text(encoding="utf-8") == "report"

    moved = manager.move(renamed, str(tmp_path / "Archive" / "report.pdf"))
    assert moved.exists()
    assert not renamed.exists()

    actions = [str(event.get("action")) for event in manager.history()]
    assert actions[-3:] == ["rename", "copy", "move"]


def test_trash_restore_and_undo(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    source = tmp_path / "old.txt"
    source.write_text("keep me", encoding="utf-8")

    trash_path = manager.trash(source)
    assert trash_path.exists()
    assert not source.exists()

    trash_events = manager.trashed("old.txt")
    assert len(trash_events) == 1
    restored = manager.restore_event(trash_events[0])
    assert restored == source.resolve()
    assert restored.read_text(encoding="utf-8") == "keep me"

    renamed = manager.rename(restored, "new.txt")
    assert renamed.exists()
    message = manager.undo_last()
    assert "Restored" in message
    assert source.exists()
    assert not renamed.exists()


def test_delete_is_safe_trash_not_unlink(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    source = tmp_path / "important.txt"
    source.write_text("data", encoding="utf-8")

    payload = manager.trash(source)

    assert not source.exists()
    assert payload.exists()
    assert payload.read_text(encoding="utf-8") == "data"
    assert str(payload).startswith(str(tmp_path / ".solace" / "trash"))


def test_mutation_outside_allowed_roots_is_refused(tmp_path: Path) -> None:
    manager = _manager(tmp_path / "home")
    manager.home.mkdir(exist_ok=True)
    outside = tmp_path / "outside.txt"
    outside.write_text("no", encoding="utf-8")

    with pytest.raises(UnsafePathError):
        manager.trash(outside)
