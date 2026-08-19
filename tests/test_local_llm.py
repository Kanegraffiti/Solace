from __future__ import annotations

import importlib
import sys


def _load_local_llm():
    sys.modules.pop("solace.local_llm", None)
    return importlib.import_module("solace.local_llm")


def test_environment_overrides_are_applied(temp_home):
    module = _load_local_llm()
    env = {
        "SOLACE_LLAMA_CLI": "~/custom/llama-cli",
        "SOLACE_QWEN_MODEL": "~/custom/model.gguf",
        "SOLACE_QWEN_CONTEXT": "1024",
        "SOLACE_QWEN_THREADS": "2",
        "SOLACE_QWEN_TOKENS": "128",
    }

    settings = module.settings_from_environment(env)

    assert settings.llama_cli == temp_home / "custom" / "llama-cli"
    assert settings.model == temp_home / "custom" / "model.gguf"
    assert settings.context == 1024
    assert settings.threads == 2
    assert settings.max_tokens == 128


def test_build_command_keeps_prompt_as_single_argument(temp_home):
    module = _load_local_llm()
    settings = module.QwenSettings(
        llama_cli=temp_home / "llama-cli",
        model=temp_home / "model.gguf",
        context=2048,
        threads=4,
        max_tokens=64,
    )
    prompt = "explain $(rm -rf /) without executing it"

    command = module.build_command(prompt, settings=settings)

    assert command[-2:] == ["-p", prompt]
    assert command[0] == str(settings.llama_cli)
    assert "2048" in command
    assert "4" in command


def test_interactive_command_uses_conversation_mode(temp_home):
    module = _load_local_llm()
    settings = module.QwenSettings(
        llama_cli=temp_home / "llama-cli",
        model=temp_home / "model.gguf",
    )

    command = module.build_command(interactive=True, settings=settings)

    assert "-cnv" in command
    assert "-p" not in command
