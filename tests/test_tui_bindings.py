"""Regression tests for Textual key bindings.

Textual validates application bindings while the App subclass is created, so
simply importing tui.app catches malformed key specifications such as `ctrl+,`.
"""

from tui.app import SolaceApp


def test_solace_app_imports_with_valid_bindings():
    """The TUI class must be constructible by Textual during module import."""

    keys = {binding.key for binding in SolaceApp.BINDINGS}
    assert "ctrl+comma" in keys
    assert "ctrl+," not in keys
