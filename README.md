<p align="center">
  <img src="assets/banner.png" alt="Solace banner" style="width:100%;max-width:100%;height:auto;" />
</p>

# Solace

Solace is an offline command line companion for journaling, quick notes and a small personal code/reference library. All data is stored locally inside your home directory so your writing never leaves your device.

## What Solace Can Do Today

* **Capture entries** – create dated `/diary`, `/notes`, `/todo` or `/quote` entries with optional tags. Entries are stored as JSON under `~/.solace/journal`.
* **Remember securely** – enable password protection and Fernet-based encryption so saved entries stay private.
* **Search memories** – `/search` looks through diary text and tags with fuzzy matching to surface relevant entries.
* **Export journals** – `/export` can produce Markdown or PDF summaries of everything you have written.
* **Back up or sync** – `/backup` creates encrypted restore points while `/sync` can push archives to optional local, S3 or WebDAV destinations with dry-run safeguards.
* **Teach snippets** – `/teach`, `/remember` and `/code` manage a lightweight library of language-specific examples stored in `~/.solace/training`.
* **Rule-based mimicry** – `/mimic` replies using a configurable phrase guide and tone, providing a friendly echo of your writing.
* **Optional voice helpers** – toggle text-to-speech or speech recognition in `/settings` once the extra packages are installed.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Kanegraffiti/Solace.git
   cd Solace
   ```
2. Install the Python requirements. The simplest route is the helper script:
   ```bash
   python install.py
   ```
   The installer detects your platform, installs dependencies from `requirements*.txt`, creates a `solace` launcher and initialises `~/.solaceconfig.json`. You can re-run it with `--alias <name>` to change the launcher name or `--skip-deps` when managing packages manually.
3. Start Solace using the launcher (or run `python main.py`):
   ```bash
   solace
   ```
4. Type `/help` in the prompt to list commands. Settings such as password protection, voice toggles or response tone live under `/settings`.

See [docs/linux_setup.md](docs/linux_setup.md) and [docs/termux_setup.md](docs/termux_setup.md) for manual dependency notes.

## Project Tour

* `main.py` – interactive CLI loop that handles commands and session logging.
* `journal.py` – storage helpers for diary, note, todo and quote entries with optional encryption.
* `trainer.py` – manages language-tagged knowledge snippets and saved training sessions.
* `mimic.py` – rule-based conversational replies with configurable fallback modes.
* `solace/` – shared modules for configuration, storage paths and memory search utilities.
* `web/` – local-only FastAPI + React stack for browsing diaries, filtering tags, exporting entries and managing snippets.

Configuration and data live under `~/.solaceconfig.json` and `~/.solace/`. The application creates folders as needed and never contacts remote services.

## Web interface (local only)

A companion web UI lives in `web/`. It reuses the Solace password/encryption settings for authentication and is designed to stay on localhost.

```bash
make dev
```

The command starts the FastAPI backend (port 8000 by default) and Vite dev server (port 4173) with hot reload. Keep both processes bound to localhost or behind a firewall—there is no remote identity provider.

## Documentation

Guides for using, configuring and extending Solace are available in the `docs/` folder:

* [overview.md](docs/overview.md) – feature overview and storage model.
* [user_guide.md](docs/user_guide.md) – step-by-step walkthrough of commands.
* [cli_reference.md](docs/cli_reference.md) – quick command summary.
* [settings.md](docs/settings.md) – configuration options explained.
* [developer_guide.md](docs/developer_guide.md) – project layout and extension tips.

---

Solace is intentionally minimal and focused on text-first workflows. Issues and pull requests are welcome to improve the experience.
