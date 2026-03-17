import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def test_process_explain_command(main_module, monkeypatch):
    printed = []

    def _capture(*args, **kwargs):
        printed.append(str(args[0]))

    monkeypatch.setattr(main_module.console, "print", _capture)
    keep_running = main_module._process_command('/explain "ls -la"')
    assert keep_running is True
    assert printed


def test_process_debug_command(main_module, monkeypatch):
    printed = []

    def _capture(*args, **kwargs):
        printed.append(str(args[0]))

    monkeypatch.setattr(main_module.console, "print", _capture)
    keep_running = main_module._process_command('/debug "bash: command not found"')
    assert keep_running is True
    assert printed
