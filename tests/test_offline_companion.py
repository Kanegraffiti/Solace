from solace.logic.converse import offline_reply
from solace.logic.python_intel import lookup_python


def test_offline_chat_responds_and_identifies_uncertainty():
    assert "Hello, Ada" in offline_reply("hello", name="Ada")
    assert "offline" in offline_reply("What is next week's weather?")


def test_python_recipe_lookup_returns_runnable_shape():
    answer = lookup_python("read a text file")
    assert answer is not None
    assert "Path" in answer.code
    compile(answer.code, "<solace-recipe>", "exec")


def test_python_recipe_does_not_guess_unknown_topics():
    assert lookup_python("quantum frobnication") is None


def test_process_chat_command(main_module, monkeypatch):
    printed = []
    monkeypatch.setattr(main_module.console, "print", lambda value, **kwargs: printed.append(str(value)))
    assert main_module._process_command("/chat hello") is True
    assert printed
