from __future__ import annotations

import subprocess

import pytest

from solace.toolkit import ToolkitClient, ToolkitUnavailable


def _completed(args, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args, returncode, stdout, stderr)


def test_unavailable_toolkit_reports_clear_error():
    client = ToolkitClient(executable="")

    with pytest.raises(ToolkitUnavailable, match="not installed"):
        client.list_tools()


def test_discovers_toolkit_metadata_and_commands():
    def runner(command, **kwargs):
        responses = {
            "root": "/data/data/com.termux/files/home/.termux-toolkit\n",
            "version": "v1.0-alpha\n",
            "list": "move-files\nmini-man\nping-check\n",
        }
        return _completed(command, stdout=responses[command[1]])

    client = ToolkitClient("/usr/bin/ttk", runner=runner)

    assert client.root().endswith(".termux-toolkit")
    assert client.version() == "v1.0-alpha"
    assert client.list_tools() == ["move-files", "mini-man", "ping-check"]


def test_capability_check_and_safe_execution():
    calls = []

    def runner(command, **kwargs):
        calls.append((command, kwargs))
        if command[1] == "has":
            return _completed(command, returncode=0)
        return _completed(command, returncode=0)

    client = ToolkitClient("/usr/bin/ttk", runner=runner)
    result = client.run("move-files", ["--help"])

    assert result.returncode == 0
    assert calls[-1][0] == ["/usr/bin/ttk", "run", "move-files", "--help"]
    assert calls[-1][1]["capture_output"] is False


def test_rejects_invalid_or_missing_tool_names():
    client = ToolkitClient("/usr/bin/ttk", runner=lambda command, **kwargs: _completed(command, 1))

    assert not client.has("../wipe-history")
    with pytest.raises(ValueError, match="Invalid"):
        client.run("../wipe-history")
    with pytest.raises(KeyError, match="not installed"):
        client.run("missing-tool")
