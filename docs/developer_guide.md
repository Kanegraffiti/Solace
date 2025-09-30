# Developer Guide

This document describes the project layout and how to extend Solace.

## Directory Layout

```
solace/
  main.py             # application entry point
  commands.py         # command dispatch and CLI helpers
  modes/              # diary, teaching and chat modes
  logic/              # modules for diary storage, notes, code examples and more
  utils/              # helper functions (encryption, voice, file handling)
  models/             # optional speech models
storage/
  diary/              # saved diary entries
  notes/              # markdown notes
  todo/               # todo items
  settings/           # user preferences
```

Data files under `storage/` are created automatically at runtime. JSON files in `data/` hold seed facts and conversation examples used by the program.
User preferences are stored in `settings/settings.json` and can be changed at runtime with the `/mode settings` command.

## Installation for Development

1. Install Python 3.10 or newer.
2. Install dependencies using the unified installer:
   ```bash
   bash setup/install.sh
   bash solace/nltk-install.sh
   ```
   Extra packages for voice features are listed in `requirements-extra.txt`.
3. Run the program from the project root using the installed launcher or directly with Python during development:
   ```bash
   solace  # or `python main.py`
   ```

## Contributing

New commands can be added in `commands.py` by registering a function in `COMMAND_MAP`. Features such as diary storage or note parsing live in the `logic/` package.

The digital clone is implemented in `logic/mimic.py`. The module analyses diary entries to extract recurring themes, a dominant mood and a handful of representative sentences. Chat mode stays locked until at least ten entries are available; once unlocked the persona snapshot is rebuilt each time new entries are saved.

Pull requests are welcome. Please keep the codebase simple and limit heavy dependencies to maintain compatibility with low resource devices.

## Plugins

Place Python files in `solace/plugins/` to extend functionality. Each plugin should expose a `register(cmd_map)` function that adds commands to the global map. Plugins are loaded automatically when `allow_plugins` is enabled in the settings.

## Developer Mode

Launch Solace with the `--dev` flag or create a `devmode.txt` file to populate dummy entries for testing the interface. This seeds a handful of diary entries, notes and todo items.


