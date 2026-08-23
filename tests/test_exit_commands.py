import pytest

import main as main_module
from solace import commands
from tui.app import SolaceApp


@pytest.mark.parametrize("command", ["/end", "/exit", "end", "exit", "quit"])
def test_main_cli_exit_aliases(command):
    assert main_module._process_command(command, show_exit_message=False) is False


def test_legacy_dispatch_supports_end(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "yes")
    assert commands.dispatch("/end") == "EXIT"


def test_tui_exposes_exit_shortcut():
    assert any(binding.key == "ctrl+q" and binding.action == "quit" for binding in SolaceApp.BINDINGS)
