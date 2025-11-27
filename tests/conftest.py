import importlib
import sys
import types
from pathlib import Path

import pytest


@pytest.fixture
def temp_home(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


@pytest.fixture
def reload_modules(temp_home):
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    module_names = [
        "solace.configuration",
        "journal",
        "solace.memory",
    ]
    for name in module_names:
        sys.modules.pop(name, None)

    def _loader(name: str):
        if name in sys.modules:
            sys.modules.pop(name, None)
        return importlib.import_module(name)

    modules = {name: _loader(name) for name in module_names}
    return modules


@pytest.fixture
def main_module(temp_home, reload_modules):
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    sys.modules.pop("main", None)
    sys.modules.pop("tui", None)
    sys.modules.pop("tui.app", None)

    dummy_package = types.ModuleType("tui")
    dummy_package.__path__ = [str(project_root / "tui")]
    sys.modules["tui"] = dummy_package

    dummy_app = types.ModuleType("tui.app")

    class _PlaceholderApp:  # noqa: D401 - helper for tests only
        """Minimal stand-in for the Textual UI."""

        def __init__(self, *args, **kwargs):
            pass

        def run(self) -> None:
            return None

    dummy_app.SolaceApp = _PlaceholderApp
    sys.modules["tui.app"] = dummy_app

    return importlib.import_module("main")
