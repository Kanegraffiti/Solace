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


def test_bash_check_validates_command_without_execution(monkeypatch):
    calls = []

    def _run(args, **kwargs):
        calls.append((args, kwargs))
        return type("Completed", (), {"returncode": 0, "stderr": ""})()

    monkeypatch.setattr(bash_intel.shutil, "which", lambda _: "/bin/bash")
    monkeypatch.setattr(bash_intel.subprocess, "run", _run)

    result = bash_intel.check_bash('for file in *.txt; do echo "$file"; done')

    assert result.syntax_valid is True
    assert calls[0][0] == ["/bin/bash", "-n"]
    assert calls[0][1]["input"] == 'for file in *.txt; do echo "$file"; done'
    assert "shell" not in calls[0][1]


def test_bash_check_reports_syntax_errors(monkeypatch):
    completed = type("Completed", (), {"returncode": 2, "stderr": "line 1: syntax error: unexpected end of file"})()
    monkeypatch.setattr(bash_intel.shutil, "which", lambda _: "/bin/bash")
    monkeypatch.setattr(bash_intel.subprocess, "run", lambda *args, **kwargs: completed)

    result = bash_intel.check_bash("if true; then echo yes")

    assert result.syntax_valid is False
    assert "unexpected end of file" in result.diagnostics


def test_bash_check_reads_termux_script_path_with_spaces(tmp_path, monkeypatch):
    script = tmp_path / "shared storage backup.sh"
    script.write_text(
        '#!/data/data/com.termux/files/usr/bin/bash\nprintf "%s\\n" "$HOME/storage/shared"\n',
        encoding="utf-8",
    )
    captured = {}

    def _run(args, **kwargs):
        captured.update(kwargs)
        return type("Completed", (), {"returncode": 0, "stderr": ""})()

    monkeypatch.setattr(bash_intel.shutil, "which", lambda _: "/data/data/com.termux/files/usr/bin/bash")
    monkeypatch.setattr(bash_intel.subprocess, "run", _run)

    result = bash_intel.check_bash(str(script))

    assert result.source == str(script)
    assert '"$HOME/storage/shared"' in captured["input"]


def test_bash_check_rejects_missing_script_path():
    try:
        bash_intel.check_bash("~/scripts/missing backup.sh")
    except FileNotFoundError as exc:
        assert "Script not found" in str(exc)
    else:
        raise AssertionError("missing script path was treated as a command")


def test_bash_check_keeps_destructive_command_as_warning(monkeypatch):
    completed = type("Completed", (), {"returncode": 0, "stderr": ""})()
    monkeypatch.setattr(bash_intel.shutil, "which", lambda _: "/bin/bash")
    monkeypatch.setattr(bash_intel.subprocess, "run", lambda *args, **kwargs: completed)

    result = bash_intel.check_bash('rm -rf "$HOME/storage/downloads"')

    assert result.syntax_valid is True
    assert any("critical path" in warning for warning in result.safety)
