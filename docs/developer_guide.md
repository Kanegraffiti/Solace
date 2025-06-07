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
```

Data files under `storage/` are created automatically at runtime. JSON files in `data/` hold seed facts and conversation examples used by the program.

## Installation for Development

1. Install Python 3.10 or newer.
2. Install dependencies using the provided helper script:
   ```bash
   bash install-safe.sh
   bash solace/nltk-install.sh
   ```
   Extra packages for voice features are listed in `requirements-extra.txt`.
3. Run the program from the project root:
   ```bash
   python main.py
   ```

## Contributing

New commands can be added in `commands.py` by registering a function in `COMMAND_MAP`. Features such as diary storage or note parsing live in the `logic/` package.

Pull requests are welcome. Please keep the codebase simple and limit heavy dependencies to maintain compatibility with low resource devices.


