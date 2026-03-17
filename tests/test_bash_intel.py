import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pathlib import Path

from solace.logic import bash_intel


def test_bash_lookup_pattern():
    result = bash_intel.lookup_bash("list all files including hidden ones")
    assert result is not None
    assert result.command == "ls -la"
    assert result.confidence > 0.4


def test_bash_explain_command_tokens():
    lines = bash_intel.explain_command("find . -type f -name '*.py'")
    joined = "\n".join(lines)
    assert "find" in joined
    assert "-type" in joined
    assert "-name" in joined


def test_bash_error_match():
    message = "bash: ./deploy.sh: Permission denied"
    result = bash_intel.debug_bash_error(message)
    assert result is not None
    assert "Cause:" in result
    assert "Fix:" in result


def test_bash_safety_warnings():
    warnings = bash_intel.classify_safety("rm -rf /tmp/build")
    assert warnings
    assert any("Recursive forced delete" in warning for warning in warnings)


def test_bash_teach_and_memory_lookup(tmp_path, monkeypatch):
    memory_file = tmp_path / "bash_history.json"
    monkeypatch.setattr(bash_intel, "BASH_MEMORY_FILE", memory_file)

    bash_intel.teach_text("Use chmod +x deploy.sh to make script executable", tags=["permissions"])
    result = bash_intel.lookup_bash("make script executable")

    assert result is not None
    assert "chmod +x deploy.sh" in result.command
    assert result.source == "memory"


def test_bash_language_detection_keywords():
    assert bash_intel.is_bash_query("show running python processes with ps and grep")
    assert not bash_intel.is_bash_query("write a python class with inheritance")
