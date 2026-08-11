# Solace

Solace is a local-first personal journal, memory search tool, and offline coding
companion. The primary application is a Rich terminal CLI, with optional Textual
and React/FastAPI interfaces. Solace stores your writing on your machine and its
chat and built-in Bash/Python answers do not call a hosted AI service.

Solace is deliberately a deterministic companion rather than a general-purpose
AI: it can recall relevant journal entries, use rule-based conversation, and
return inspectable recipes from its bundled knowledge bases. It does not execute
the commands or code it suggests.

## What works today

- **Journal and personal knowledge:** dated diary entries, notes, todos, and
  quotes, with tags and colon shortcuts such as `:diary` and `:notes`.
- **Recall and recaps:** hybrid text/tag/date search across entries and weekly or
  monthly extractive summaries.
- **Offline companion:** `/chat` combines rule-based responses with up to three
  relevant, dated memories. Bash and Python questions are routed to bundled,
  deterministic knowledge instead.
- **Coding reference:** teach and retrieve your own language-tagged snippets;
  look up bundled Bash commands and Python recipes; explain Bash syntax; and
  match common Bash errors. Suggestions are for review, not automatic execution.
- **Privacy controls:** journal content is Fernet-encrypted at rest by default,
  with an optional startup password. Configuration and data remain local unless
  you explicitly configure sync.
- **Export, backup, and sync:** Markdown/PDF export, local ZIP backups, and
  optional S3 or WebDAV uploads. Sync starts disabled and in dry-run mode.
- **Multiple interfaces:** interactive CLI, a Textual TUI, scriptable CLI
  commands, and an optional local web UI/API.
- **Optional voice:** local text-to-speech and speech recognition, subject to
  platform audio support and installed engines/models.

## Requirements

- Python 3.9 or newer
- Git
- Node.js and npm only if you want to run the web frontend
- Platform audio libraries only if you enable voice features

The default installer installs the core requirements and PocketSphinx voice
extras. ML packages in `requirements-ml.txt` are optional; the core CLI and its
offline recipe/recall features do not require them.

## Install and run

```bash
git clone https://github.com/Kanegraffiti/Solace.git
cd Solace
python3 install.py
solace
```

The installer creates `~/.solaceconfig.json`, initializes directories beneath
`~/.solace/`, and places a launcher in `~/.local/bin` on Unix-like systems (or
`~/AppData/Local/solace` on Windows). Restart your shell if the new launcher is
not immediately on `PATH`.

To install without changing your Python environment, or to run directly from a
checkout:

```bash
python3 install.py --skip-deps
python3 main.py
```

Optional local ML dependencies can be requested during installation:

```bash
python3 install.py --extras ml
```

> **Privacy note:** Solace does not transmit journal or chat content as part of
> its normal CLI operation. Remote S3/WebDAV sync and the weather plugin are
> network-capable features and must be explicitly enabled/configured. Review
> your configuration before using them.

## Using the CLI

Run `solace` (or `python3 main.py`) and enter `/help`. Plain, non-command text is
saved as a diary entry. Entry commands prompt for a date, time, and tags.

```text
I finished the first deployment today
/notes Release checklist and rollback steps
/todo Verify the production backup
/quote Make it work, then make it clear
/search deployment
/summarize week
/chat What did I decide about the deployment?
```

Only entries that can be decrypted in the current session are used as readable
chat context. `/chat` is not a generative cloud chatbot: conversational replies
are rule-based, memory recall is local, and supported programming prompts use
the bundled knowledge files.

### Main commands

| Command | Purpose |
| --- | --- |
| `/diary [text]`, `/notes [text]`, `/todo [text]`, `/quote [text]` | Save a dated, tagged entry. Omitting text opens multiline input. |
| `/search <query>` | Search journal text, tags, and dates. |
| `/summarize [week\|month]` | Show recent extractive recaps. |
| `/chat <message>` | Get a local response grounded in relevant memories or bundled code knowledge. |
| `/teach <language> [text]` | Add an example, error, or tip to your local training set. |
| `/remember <language> <query>` | Retrieve matching taught material. |
| `/code bash <topic>` | Look up a Bash command/template with explanations, placeholders, and safety notes. |
| `/code python <topic>` | Look up a bundled Python recipe. Other languages search taught snippets. |
| `/ask bash <topic>` | Explain a supported Bash concept. |
| `/debug <error>` | Match a common Bash error to likely causes and fixes. |
| `/explain [bash] <command>` | Break down Bash tokens, flags, pipes, and redirects. |
| `/mimic <text>` | Use the rule-based mimic responder. |
| `/export [markdown\|pdf] [path]` | Export journal entries. |
| `/backup [--dry-run] [--force] [--no-restore]` | Create a local backup archive. |
| `/sync [local\|s3\|webdav] [--dry-run] [--force] [--no-restore]` | Sync through a configured backend. |
| `/listen` | Capture speech when STT is enabled. |
| `/settings` | Show password, voice, tone, alias, backup/restore, info, and fallback settings. |
| `/help` | Show the in-app command list. |
| `/exit`, `exit`, `quit` | Leave Solace. |

Colon shortcuts (`:diary text`, `:notes text`, `:todo text`, and `:quote text`)
are also supported.

### Textual TUI

```bash
python3 main.py --tui
```

### Scripted use

Use `-c/--command` more than once, or provide a newline-delimited command file.
`--accept-defaults` suppresses interactive entry metadata prompts where possible.

```bash
python3 main.py --accept-defaults \
  -c "/diary Automated check completed" \
  -c "/search automated"

python3 main.py --accept-defaults --command-file commands.txt
```

`--tui` cannot be combined with scripted commands.

## Data, encryption, backups, and sync

The primary application uses:

- `~/.solaceconfig.json` for its human-readable configuration;
- `~/.solace/journal/entries.json` for journal records;
- `~/.solace/training/` for manually taught snippets;
- `~/.solace/conversation/` for mimic data;
- `~/.solace/cache/` for generated/cache files; and
- `~/.solace/session.log` for a short command/session activity log.

Paths can be changed in the config. Content fields in journal records are
encrypted by default; metadata such as entry type, date/time, and tags remains
visible. An optional password protects startup and participates in key
derivation. Keep a safe copy of `~/.solaceconfig.json`: losing its generated key
material can make encrypted data unrecoverable.

Backups contain an encrypted journal payload. By default they **also include a
plain-text restore copy** (`entries.json`) and the configuration for recovery.
Use `--no-restore` if the archive must not contain that restore copy, and protect
backup files accordingly.

S3 sync requires `boto3` (not included in the core requirements); WebDAV uses
Python's standard library. Configure and enable remote backends in
`~/.solaceconfig.json`, then turn off `sync.dry_run` or explicitly test with
`/sync ... --dry-run` before a real upload.

## Local web app (optional)

The web application provides authenticated journal browsing/creation, tag
filtering, Markdown/PDF exports, and snippet browsing, search, teaching, and
index rebuilding.

```bash
# From the repository root; installs frontend packages on first run
make dev
```

By default the API uses port 8000 and Vite uses port 4173. Override them with
`API_PORT` and `UI_PORT`. The development script binds both services using
`--host`, so treat it as a development server: do not expose it to an untrusted
network, and use firewall/container port controls as appropriate. API sessions
use an in-memory bearer token obtained through the login endpoint; if a Solace
password is configured, login requires it.

Individual services and a production frontend build can be run with:

```bash
make api
make frontend
make build-frontend
```

See [`web/README.md`](web/README.md) for the web-specific overview.

## Repository map

| Path | Contents |
| --- | --- |
| `main.py` | Primary Rich CLI, scripted runner, and TUI launcher. |
| `journal.py` | Journal persistence, encryption/decryption, and export. |
| `trainer.py` | User-taught snippet storage and lookup. |
| `mimic.py` | Rule-based mimic support. |
| `solace/logic/` | Recall, companion, Bash/Python intelligence, and supporting logic. |
| `solace/knowledge/` | Bundled offline programming recipes and error references. |
| `solace/configuration.py` | Primary config, storage, password, and cipher management. |
| `solace/sync.py` | Backup packaging plus local, S3, and WebDAV backends. |
| `tui/` | Textual terminal interface. |
| `web/api/` | FastAPI service. |
| `web/frontend/` | React/Vite client. |
| `docs/` | Additional user, setup, settings, CLI, and developer documentation. |
| `tests/` | Unit and integration tests. |

The repository also contains `solace/main.py`, an older alternate CLI with a
different settings layout. The supported installer and launchers target the
root `main.py`; use that entry point unless you are specifically maintaining the
legacy implementation.

## Development

```bash
python3 -m pip install -r requirements.txt -r requirements-dev.txt
pytest
ruff check .
flake8 .
mypy .
```

Frontend checks/build:

```bash
cd web/frontend
npm install
npm run build
```

Further documentation is available in [`docs/overview.md`](docs/overview.md),
[`docs/user_guide.md`](docs/user_guide.md),
[`docs/cli_reference.md`](docs/cli_reference.md),
[`docs/settings.md`](docs/settings.md), and
[`docs/developer_guide.md`](docs/developer_guide.md).
