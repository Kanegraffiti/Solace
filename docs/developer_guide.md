# Developer Guide

This document outlines the current project structure and suggests starting points for contributors.

## Repository layout

```
README.md
main.py                              # interactive CLI entry point
journal.py                           # journal storage helpers
mimic.py                             # rule-based conversational replies
trainer.py                           # training snippet manager
solace/
  configuration.py                   # config handling + storage path helpers
  memory.py                          # fuzzy search across entries
  logic/
    bash_intel.py                    # deterministic Bash lookup/explain/safety/error engine
    ...
  knowledge/
    programming/
      bash/
        README.md                    # Bash knowledge schema
        commands.json
        flags.json
        patterns.json
        scripts.json
        topics.json
        safety.json
        errors.json
```

Solace persists user data outside the repository in `~/.solace/` and keeps configuration in `~/.solaceconfig.json`. These paths are created on first run or by the installer.

## Running the app during development

1. Create a virtual environment and install dependencies from `requirements.txt` (and `requirements-extra.txt` if you need voice features).
2. Run `python install.py --skip-deps` to create a launcher and initial config without reinstalling packages, or execute `python main.py` directly while developing.
3. Use `/help` inside the program to see available commands.

## Bash intelligence architecture

`solace.logic.bash_intel` is the central module for Bash-specific deterministic behavior:

- language detection (`is_bash_query`) with CLI-native keyword signals
- intent lookup (`lookup_bash`) from `patterns.json`
- reusable script retrieval from `scripts.json`
- command safety classification (`classify_safety`) via `safety.json`
- command parser for `/explain` (`explain_command`) using `commands.json` + `flags.json`
- concept help for `/ask bash ...` (`explain_topic`) from `topics.json`
- error assistance for `/debug` (`debug_bash_error`) from `errors.json`
- user-approved local memory in `~/.solace/training/bash_history.json`

This design intentionally avoids network calls and heavyweight dependencies, and is friendly to low-resource environments (including Termux/Android).

## Extending Solace

New commands are registered inside `main.py` by adding to the `COMMANDS` mapping. Each command handler receives the raw argument string and can call into helper modules (journal, trainer, mimic, bash_intel, etc.). Keep handlers focused on user interaction and move reusable logic into dedicated modules so they can be tested independently.

When adding new storage requirements, update `solace.configuration.DEFAULT_CONFIG` so directories are created automatically and the config file documents their purpose.

Voice functionality relies on optional dependencies (`pyttsx3`, `speechrecognition`, `sounddevice`). Ensure new features degrade gracefully when these packages are missing.

## Testing considerations

Run tests with:

```bash
pytest
```

Bash behavior is validated in `tests/test_bash_intel.py` and command integration checks in `tests/test_cli_bash_commands.py`.
