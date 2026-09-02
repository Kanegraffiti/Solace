import importlib
import sys
from pathlib import Path

from solace.file_skill import FileManager


def test_do_inspects_folder_without_executing_commands(temp_home: Path, monkeypatch, capsys) -> None:
    sys.modules.pop("solace.launcher", None)
    launcher = importlib.import_module("solace.launcher")
    project = temp_home / "storefront"
    project.mkdir()
    (project / "package.json").write_text(
        '{"scripts":{"dev":"vite"},"devDependencies":{"vite":"latest"}}', encoding="utf-8"
    )
    launcher.FILE_MANAGER = FileManager(
        home=temp_home,
        search_roots=[temp_home],
        state_dir=temp_home / ".solace",
    )
    events = []
    monkeypatch.setattr(launcher.core, "_log_event", lambda action, detail: events.append((action, detail)))
    launcher._register_extensions()

    assert launcher.core._process_command("/do inspect storefront") is True

    output = capsys.readouterr().out
    assert "Project task plan" in output
    assert "Vite" in output
    assert "npm run dev" in output
    assert events == [("do", "inspect storefront")]


def test_scripted_do_never_extracts_without_confirmation(temp_home: Path, monkeypatch, capsys) -> None:
    sys.modules.pop("solace.launcher", None)
    launcher = importlib.import_module("solace.launcher")
    archive = temp_home / "portfolio.zip"
    import zipfile

    with zipfile.ZipFile(str(archive), "w") as bundle:
        bundle.writestr("index.html", "hello")
    launcher.FILE_MANAGER = FileManager(
        home=temp_home,
        search_roots=[temp_home],
        state_dir=temp_home / ".solace",
    )
    monkeypatch.setattr(launcher.core, "PROMPT_DEFAULTS_ONLY", True)

    launcher._handle_do("inspect portfolio.zip")

    assert not (temp_home / "portfolio").exists()
    assert "Nothing was changed" in capsys.readouterr().out


def test_scripted_do_run_never_executes_project_code(temp_home: Path, monkeypatch, capsys) -> None:
    sys.modules.pop("solace.launcher", None)
    launcher = importlib.import_module("solace.launcher")
    project = temp_home / "storefront"
    project.mkdir()
    (project / "package.json").write_text(
        '{"scripts":{"dev":"vite"}}', encoding="utf-8"
    )
    launcher.FILE_MANAGER = FileManager(
        home=temp_home,
        search_roots=[temp_home],
        state_dir=temp_home / ".solace",
    )
    monkeypatch.setattr(launcher.core, "PROMPT_DEFAULTS_ONLY", True)
    monkeypatch.setattr(
        launcher,
        "execute_project_command",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not execute")),
    )

    launcher._handle_do("run storefront")

    assert "Scripted mode will not execute project code" in capsys.readouterr().out


def test_scripted_training_never_imports_private_transcript(temp_home: Path, monkeypatch, capsys) -> None:
    sys.modules.pop("solace.launcher", None)
    launcher = importlib.import_module("solace.launcher")
    monkeypatch.setattr(launcher.core, "PROMPT_DEFAULTS_ONLY", True)
    monkeypatch.setattr(
        launcher,
        "read_transcript",
        lambda *args: (_ for _ in ()).throw(AssertionError("must not read transcript")),
    )

    launcher._handle_train("chat private.txt")

    assert "require interactive local review" in capsys.readouterr().out
