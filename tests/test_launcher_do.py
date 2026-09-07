import importlib
import sys
from pathlib import Path

from solace.file_skill import FileManager
from solace.project_task import ProjectCommandResult


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


def test_failed_do_run_requires_fresh_approval_before_retry(temp_home: Path, monkeypatch, capsys) -> None:
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
    approvals = iter([True, False])
    monkeypatch.setattr(launcher, "_confirm_mutation", lambda prompt: next(approvals))
    calls = []

    def fake_execute(command, root):
        calls.append((command, root))
        return ProjectCommandResult(
            command, 127, "", "npm: command not found", False
        )

    monkeypatch.setattr(launcher, "execute_project_command", fake_execute)
    launcher._handle_do("run storefront")

    output = capsys.readouterr().out
    assert len(calls) == 1
    assert "executable is not on PATH" in output
    assert "Checked retry" in output
    assert "Retry declined" in output
