# Developer Guide

This document outlines the current project structure and suggests starting points for contributors.

## Repository layout

```
README.md
main.py                # interactive CLI entry point
journal.py             # journal storage helpers
mimic.py               # rule-based conversational replies
trainer.py             # training snippet manager
solace/
  __init__.py
  configuration.py     # config handling, encryption helpers
  memory.py            # fuzzy search across entries
assets/                # images used in documentation
setup/                 # legacy shell installer scripts
storage/               # sample data used for testing
```

Solace persists user data outside the repository in `~/.solace/` and keeps configuration in `~/.solaceconfig.json`. These paths are created on first run or by the installer.

## Running the app during development

1. Create a virtual environment and install dependencies from `requirements.txt` (and `requirements-extra.txt` if you need voice features).
2. Run `python install.py --skip-deps` to create a launcher and initial config without reinstalling packages, or execute `python main.py` directly while developing.
3. Use `/help` inside the program to see available commands.

## Key modules

- `journal.py` exposes functions to add, load and export entries. It relies on `solace.configuration` for storage paths and encryption.
- `trainer.py` manages the language-indexed knowledge snippets. The JSON index is rebuilt as needed and session notes are saved for reference.
- `mimic.py` loads a simple JSON rule set from the conversation storage directory and scores user input using `difflib.SequenceMatcher`.
- `solace/memory.py` implements the fuzzy search used by `/search`.
- `solace/configuration.py` centralises config I/O, password prompts, key derivation and helper utilities shared across modules.

## Extending Solace

New commands are registered inside `main.py` by adding to the `COMMANDS` mapping. Each command handler receives the raw argument string and can call into helper modules (journal, trainer, mimic, etc.). Keep handlers focused on user interaction and move reusable logic into dedicated modules so they can be tested independently.

When adding new storage requirements, update `solace.configuration.DEFAULT_CONFIG` so directories are created automatically and the config file documents their purpose.

Voice functionality relies on optional dependencies (`pyttsx3`, `speechrecognition`, `sounddevice`). Ensure new features degrade gracefully when these packages are missing.

## Testing considerations

The current codebase has no automated tests. Manual testing generally involves running Solace, creating sample entries, performing searches and exercising the training commands. Contributions that add unit tests for the helper modules are welcome.
