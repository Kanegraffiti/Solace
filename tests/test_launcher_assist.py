import importlib
import sys


def _launcher():
    sys.modules.pop("solace.launcher", None)
    return importlib.import_module("solace.launcher")


def test_assist_uses_deterministic_handler_without_model(temp_home, monkeypatch):
    launcher = _launcher()
    calls = []
    monkeypatch.setattr(launcher.core.console, "print", lambda *args, **kwargs: None)
    launcher._register_extensions()
    launcher.core.COMMANDS["grammar"] = lambda args: calls.append(args)

    launcher._handle_assist("fix grammar: i has notes")

    assert calls == ["i has notes"]


def test_assist_ai_off_never_invokes_model(temp_home, monkeypatch):
    launcher = _launcher()
    printed = []
    monkeypatch.setattr(launcher.core.console, "print", lambda value: printed.append(value))
    monkeypatch.setattr(launcher, "run_local_model", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError()))
    launcher.core.CONFIG.setdefault("assistant", {})["ai_policy"] = "off"

    launcher._handle_assist("compare two fantasy stories")

    assert "did not guess" in printed[-1].renderable


def test_assist_ask_does_not_assume_consent_in_scripts(temp_home, monkeypatch):
    launcher = _launcher()
    printed = []
    monkeypatch.setattr(launcher.core.console, "print", lambda value: printed.append(str(value)))
    monkeypatch.setattr(launcher, "runtime_status", lambda: (True, "ready"))
    monkeypatch.setattr(launcher, "run_local_model", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError()))
    launcher.core.CONFIG.setdefault("assistant", {})["ai_policy"] = "ask"
    monkeypatch.setattr(launcher.core, "PROMPT_DEFAULTS_ONLY", True)

    launcher._handle_assist("compare two fantasy stories")

    assert "approval is required" in printed[-1]
