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


def test_process_bash_check_command(main_module, monkeypatch):
    printed = []

    def _capture(*args, **kwargs):
        printed.append(str(args[0]))

    monkeypatch.setattr(main_module.console, "print", _capture)
    keep_running = main_module._process_command('/bash check printf "%s\\n" "$HOME"')

    assert keep_running is True
    assert printed


def test_process_bash_do_never_executes_in_scripted_mode(main_module, monkeypatch, tmp_path):
    printed = []
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr(main_module.console, "print", lambda *args, **kwargs: printed.append(str(args[0])))
    monkeypatch.setattr(main_module, "PROMPT_DEFAULTS_ONLY", True)
    monkeypatch.setattr(
        main_module,
        "execute_bash_task",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not execute")),
    )

    keep_running = main_module._process_command("/bash do git status {}".format(project))

    assert keep_running is True
    assert any("will not approve" in item for item in printed)
