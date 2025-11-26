# Solace Overview

Solace is a text-first command line assistant centred on journaling and lightweight personal knowledge management. Everything runs offline: configuration lives in `~/.solaceconfig.json` and content is written to `~/.solace/` inside your home directory.

The application focuses on three areas:

- **Journaling** – capture dated diary, note, todo and quote entries that are stored as JSON. Entries can be encrypted when Solace is configured with a password.
- **Memory search** – query past writing with `/search`, which performs fuzzy matching across text and tags to resurface relevant memories.
- **Teaching snippets** – curate language-tagged examples using `/teach`, then revisit them through `/remember` or `/code` when you need a refresher.

Data is intentionally simple so it can be inspected or backed up manually. Journal entries are appended to `entries.json`, training snippets sit under `~/.solace/training`, and the mimic guide is a small JSON file that you can edit to customise responses.

The `/settings` command provides quick switches for password protection, voice options, tone, alias name and backup helpers. See [settings.md](settings.md) for command details.

Solace ships as a single-terminal experience: run it, type `/help` to view commands, and keep writing. There is no web UI or analytics. Optional `/sync` backends stay disabled until you configure them, keeping the default experience fully offline.
