import importlib
import sys


def _launcher():
    sys.modules.pop("solace.launcher", None)
    return importlib.import_module("solace.launcher")


def test_grammar_command_prints_corrected_text(temp_home, monkeypatch):
    launcher = _launcher()
    printed = []
    events = []
    monkeypatch.setattr(launcher.core.console, "print", lambda value: printed.append(value))
    monkeypatch.setattr(launcher.core, "_log_event", lambda action, detail: events.append((action, detail)))
    launcher._register_extensions()

    assert launcher.core._process_command("/grammar i has the notes") is True
    assert "I have the notes" in printed[0].renderable
    assert events == [("grammar", "2 local correction(s)")]


def test_grammar_file_command_creates_copy(temp_home, monkeypatch):
    launcher = _launcher()
    source = temp_home / "draft notes.txt"
    source.write_text("she dont know", encoding="utf-8")
    printed = []
    monkeypatch.setattr(launcher.core.console, "print", lambda value: printed.append(value))
    monkeypatch.setattr(launcher.core, "_log_event", lambda *args: None)

    launcher._handle_grammar(f'file "{source}"')

    output = temp_home / "draft notes.grammar-edited.txt"
    assert source.read_text(encoding="utf-8") == "she dont know"
    assert output.read_text(encoding="utf-8") == "She doesn't know"
    assert "The original file was not changed" in printed[0].renderable


def test_grammar_command_does_not_log_user_text(temp_home, monkeypatch):
    launcher = _launcher()
    events = []
    monkeypatch.setattr(launcher.core.console, "print", lambda value: None)
    monkeypatch.setattr(launcher.core, "_log_event", lambda action, detail: events.append((action, detail)))

    launcher._handle_grammar("i have a private secret")

    assert events == [("grammar", "1 local correction(s)")]
    assert "private secret" not in repr(events)
