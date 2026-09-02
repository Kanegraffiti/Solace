from pathlib import Path
from types import SimpleNamespace

import pytest

from solace import updater


def _completed(stdout="", stderr="", returncode=0):
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


def _git_responses(*, status="", ahead=0, behind=1):
    return {
        ("remote", "get-url", "origin"): _completed("https://github.com/Kanegraffiti/Solace.git\n"),
        ("branch", "--show-current"): _completed("main\n"),
        ("status", "--porcelain", "--untracked-files=all"): _completed(status),
        ("rev-parse", "HEAD"): [_completed("old-commit\n"), _completed("new-commit\n")],
        ("fetch", "--prune", "origin", "main"): _completed(),
        ("rev-list", "--left-right", "--count", "HEAD...origin/main"): _completed(f"{ahead}\t{behind}\n"),
        ("merge", "--ff-only", "origin/main"): _completed(),
    }


def _mock_git(monkeypatch, responses):
    calls = []

    def _run_git(root, *arguments, check=True):
        calls.append(arguments)
        response = responses[arguments]
        if isinstance(response, list):
            return response.pop(0)
        return response

    monkeypatch.setattr(updater, "_run_git", _run_git)
    return calls


def test_update_fast_forwards_and_preserves_user_data(tmp_path, monkeypatch):
    project = tmp_path / "Solace"
    (project / ".git").mkdir(parents=True)
    (project / "install.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    data = tmp_path / ".solace" / "journal" / "entries.json"
    data.parent.mkdir(parents=True)
    data.write_text("private journal", encoding="utf-8")
    config = tmp_path / ".solaceconfig.json"
    config.write_text("private config", encoding="utf-8")

    calls = _mock_git(monkeypatch, _git_responses())
    install_calls = []
    monkeypatch.setattr(updater.shutil, "which", lambda command: f"/usr/bin/{command}")
    monkeypatch.setattr(
        updater.subprocess,
        "run",
        lambda args, **kwargs: install_calls.append((args, kwargs)) or _completed(),
    )

    result = updater.update_solace(project)

    assert result.changed is True
    assert ("merge", "--ff-only", "origin/main") in calls
    assert install_calls[0][0] == [
        "/usr/bin/bash",
        str(project / "install.sh"),
        "--preserve-config",
    ]
    assert data.read_text(encoding="utf-8") == "private journal"
    assert config.read_text(encoding="utf-8") == "private config"


def test_update_does_nothing_when_current(tmp_path, monkeypatch):
    project = tmp_path / "Solace"
    (project / ".git").mkdir(parents=True)
    calls = _mock_git(monkeypatch, _git_responses(behind=0))

    result = updater.update_solace(project)

    assert result.changed is False
    assert ("merge", "--ff-only", "origin/main") not in calls


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({("branch", "--show-current"): _completed("feature\n")}, "not main"),
        ({("status", "--porcelain", "--untracked-files=all"): _completed(" M main.py\n")}, "local or untracked"),
        ({("rev-list", "--left-right", "--count", "HEAD...origin/main"): _completed("1\t2\n")}, "local main"),
        ({("remote", "get-url", "origin"): _completed("https://example.com/wrong.git\n")}, "not the canonical"),
    ],
)
def test_update_refuses_unsafe_checkout(tmp_path, monkeypatch, override, message):
    project = tmp_path / "Solace"
    (project / ".git").mkdir(parents=True)
    responses = _git_responses()
    responses.update(override)
    calls = _mock_git(monkeypatch, responses)

    with pytest.raises(updater.UpdateError, match=message):
        updater.update_solace(project)

    assert ("merge", "--ff-only", "origin/main") not in calls


def test_update_requires_a_git_checkout(tmp_path):
    with pytest.raises(updater.UpdateError, match="not a Git checkout"):
        updater.update_solace(Path(tmp_path))


def test_canonical_remote_accepts_https_and_ssh():
    assert updater._is_canonical_remote("https://github.com/Kanegraffiti/Solace.git")
    assert updater._is_canonical_remote("git@github.com:Kanegraffiti/Solace.git")
    assert not updater._is_canonical_remote("https://github.com/someone-else/Solace.git")
