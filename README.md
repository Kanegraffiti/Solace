# Solace

Solace is a local-first personal journal, memory search tool, offline coding
companion, and optional on-device AI shell. The primary interface is a Rich
terminal CLI designed to work especially well in Termux, while Textual and a
local React/FastAPI interface remain available as optional interfaces.

The core journal, memory recall, Bash/Python knowledge, encryption, and local
Qwen integration do not require a hosted AI service. Solace does not execute
commands suggested by its deterministic coding knowledge or by Qwen; review
anything generated before running it.

## What Solace does

- **Journal and personal knowledge:** dated diary entries, notes, todos, quotes,
  tags, search, and weekly/monthly recaps.
- **Local memory companion:** `/chat` uses local journal recall and bundled
  deterministic knowledge rather than a cloud chatbot.
- **Offline coding reference:** bundled Bash and Python recipes, Bash syntax
  explanations, common-error matching, and user-taught snippets.
- **Optional local Qwen:** Termux users can run Qwen2.5-Coder-1.5B-Instruct
  Q4_K_M locally through llama.cpp with `/qwen` or the standalone `qwen`
  command.
- **Privacy controls:** journal content is encrypted at rest by default, with an
  optional startup password.
- **Export, backup, and sync:** Markdown/PDF export, local backups, and optional
  S3 or WebDAV sync.
- **Scriptable terminal workflow:** the installed `solace` command works from
  any directory and still supports `-c`, `--command-file`, and the Textual TUI.

## Requirements

Core Solace requires:

- Python 3.9+
- Git

Optional components add their own requirements:

- Node.js/npm for the web frontend
- platform audio libraries for voice features
- Termux + about 1.12 GB for the recommended Qwen GGUF, plus llama.cpp build
  files, if you enable local Qwen

## Install in Termux

The recommended Termux path is:

```bash
pkg install -y git python
git clone https://github.com/Kanegraffiti/Solace.git
cd Solace
bash install.sh
```

The shell installer creates a project-local virtual environment and then creates
real launchers. On Termux, `solace` is written directly to `$PREFIX/bin`, which
is already on Termux's `PATH`.

Start Solace from anywhere:

```bash
solace
```

You can also use the Python installer directly:

```bash
python3 install.py
solace
```

If you only want to refresh launchers/configuration without reinstalling Python
dependencies:

```bash
python3 install.py --skip-deps
```

The supported direct-entry fallback from a checkout is:

```bash
python3 solace/launcher.py
```

## The startup mini-manual

Interactive starts show a deliberately small quick-start panel. It reminds you
of the highest-value commands without turning startup into a wall of text.

To hide it on future starts:

```text
/manual off
```

To view it whenever you need it:

```text
/manual
```

To restore it on every interactive start:

```text
/manual on
```

Scripted invocations such as `solace -c ...` do not print the startup manual, so
it does not pollute automation output.

## Local Qwen on Termux

Qwen is optional. Solace intentionally does **not** download a gigabyte-scale
model or compile llama.cpp during a normal install.

To set up the recommended local model explicitly:

```bash
cd ~/Solace
bash scripts/setup-qwen-termux.sh
```

Or combine it with the Python installer:

```bash
python3 install.py --skip-deps --setup-qwen
```

The setup helper:

1. installs/confirms the Termux build tools it needs;
2. reuses an existing `~/llama.cpp` checkout or clones llama.cpp if missing;
3. builds only `llama-cli` in Release mode, using two parallel jobs by default;
4. downloads the official
   `Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF` Q4_K_M file if it is missing;
5. verifies the published SHA-256 before accepting the downloaded model; and
6. installs the standalone `qwen` command in `$PREFIX/bin`.

Two build jobs are intentionally conservative for phones. On a tighter device,
use one:

```bash
QWEN_BUILD_JOBS=1 bash scripts/setup-qwen-termux.sh
```

### Use Qwen directly

Interactive chat:

```bash
qwen
```

Start Qwen with an initial prompt:

```bash
qwen "Explain this Bash pipeline and point out anything dangerous"
```

### Use Qwen inside Solace

```text
/qwen status
/qwen Write a Bash function that checks whether a command exists
/qwen
```

`/qwen status` checks the expected runtime/model paths without starting the
model. `/qwen <prompt>` launches local Qwen with that initial prompt. `/qwen`
opens an interactive Qwen session. Use `/exit` or Ctrl+C inside Qwen to return
to the Solace prompt.

The default phone-friendly runtime settings are:

- context: `2048`
- threads: `4`
- generated-token limit: `512`
- llama.cpp binary: `~/llama.cpp/build/bin/llama-cli`
- model: `~/models/qwen2.5-coder-1.5b/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf`

They can be overridden without editing source code:

```bash
export SOLACE_QWEN_CONTEXT=1024
export SOLACE_QWEN_THREADS=2
export SOLACE_QWEN_TOKENS=256
export SOLACE_LLAMA_CLI="$HOME/other-llama/build/bin/llama-cli"
export SOLACE_QWEN_MODEL="$HOME/models/another-model.gguf"
```

Solace invokes llama.cpp with an argument list rather than through a shell, so a
prompt is not interpreted as a Bash command.

## Using the CLI

Run `solace` and enter `/help` for the complete command table. Plain text that
is not a command is saved as a diary entry.

```text
I finished the first deployment today
/notes Release checklist and rollback steps
/todo Verify the production backup
/search deployment
/summarize week
/chat What did I decide about the deployment?
/qwen Explain rsync --delete and its risks
```

### Main commands

| Command | Purpose |
| --- | --- |
| `/diary [text]`, `/notes [text]`, `/todo [text]`, `/quote [text]` | Save a dated, tagged entry. |
| `/search <query>` | Search journal text, tags, and dates. |
| `/summarize [week\|month]` | Show recent extractive recaps. |
| `/chat <message>` | Talk with the deterministic local memory companion. |
| `/qwen <prompt>` | Start local Qwen with an initial prompt. |
| `/qwen` | Open interactive local Qwen. |
| `/qwen status` | Check whether the local Qwen runtime/model are ready. |
| `/teach <language> [text]` | Add an example, error, or tip to local training data. |
| `/remember <language> <query>` | Retrieve matching taught material. |
| `/code bash <topic>` | Look up a Bash command/template with explanations and safety notes. |
| `/code python <topic>` | Look up a bundled Python recipe. |
| `/ask bash <topic>` | Explain a supported Bash concept. |
| `/debug <error>` | Match a common Bash error to likely causes and fixes. |
| `/explain [bash] <command>` | Break down Bash tokens, flags, pipes, and redirects. |
| `/manual [on\|off\|status]` | Show or configure the startup mini-manual. |
| `/mimic <text>` | Use the rule-based mimic responder. |
| `/export [markdown\|pdf] [path]` | Export journal entries. |
| `/backup [--dry-run] [--force] [--no-restore]` | Create a local backup archive. |
| `/sync [local\|s3\|webdav] [--dry-run] [--force] [--no-restore]` | Sync through a configured backend. |
| `/listen` | Capture speech when STT is enabled. |
| `/settings` | Manage password, voice, tone, alias, backup/restore, and related settings. |
| `/help` | Show the full in-app command list. |
| `/exit`, `exit`, `quit` | Leave Solace. |

Colon shortcuts (`:diary text`, `:notes text`, `:todo text`, and `:quote text`)
are also supported.

## Scripted use

The installed launcher forwards the existing scripting options:

```bash
solace --accept-defaults \
  -c "/diary Automated check completed" \
  -c "/search automated"

solace --accept-defaults --command-file commands.txt
```

The startup manual is suppressed during scripted use.

## Textual TUI

```bash
solace --tui
```

## Data and privacy

The primary application uses:

- `~/.solaceconfig.json` for configuration;
- `~/.solace/journal/entries.json` for journal records;
- `~/.solace/training/` for taught snippets;
- `~/.solace/conversation/` for mimic data;
- `~/.solace/cache/` for generated/cache files; and
- `~/.solace/session.log` for short command/session activity logs.

Journal content is encrypted by default. Metadata such as entry type, date/time,
and tags remains visible. Keep a safe copy of `~/.solaceconfig.json`; losing its
key material can make encrypted data unrecoverable.

Local Qwen runs on the device through llama.cpp and does not require an OpenAI,
Gemini, or other hosted-model API key. Remote S3/WebDAV sync and other explicitly
network-capable features remain opt-in.

## Backup and sync

Backups contain an encrypted journal payload. By default they also include a
plain-text restore copy (`entries.json`) and configuration for recovery. Use
`--no-restore` if the archive must not contain that restore copy, and protect
backup files accordingly.

S3 sync requires `boto3`; WebDAV uses Python's standard library. Configure and
enable remote backends in `~/.solaceconfig.json`, and test with dry-run settings
before a real upload.

## Local web app (optional)

The local web application provides journal browsing/creation, exports, snippet
management, and related tools.

```bash
make dev
```

By default the API uses port 8000 and Vite uses port 4173. Treat it as a local
development service rather than exposing it directly to an untrusted network.
See [`web/README.md`](web/README.md) for web-specific details.

## Repository map

| Path | Contents |
| --- | --- |
| `solace/launcher.py` | Supported launcher; startup manual and local-Qwen command registration. |
| `solace/local_llm.py` | Safe llama.cpp/Qwen discovery and process invocation. |
| `solace/user_manual.py` | Tiny startup manual and persistent visibility preference. |
| `scripts/qwen.sh` | Standalone Termux `qwen` wrapper. |
| `scripts/setup-qwen-termux.sh` | Explicit llama.cpp build + verified Qwen setup. |
| `main.py` | Existing Rich CLI implementation used by the supported launcher. |
| `journal.py` | Journal persistence, encryption/decryption, and export. |
| `trainer.py` | User-taught snippet storage and lookup. |
| `solace/logic/` | Recall, companion, Bash/Python intelligence, and supporting logic. |
| `solace/knowledge/` | Bundled offline programming recipes and error references. |
| `solace/configuration.py` | Configuration, storage, password, and cipher management. |
| `solace/sync.py` | Backup packaging plus local, S3, and WebDAV backends. |
| `tui/` | Textual terminal interface. |
| `web/` | Optional FastAPI + React/Vite interface. |
| `tests/` | Unit and integration tests. |

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

Further documentation lives in [`docs/`](docs/), including the user guide, CLI
reference, settings guide, developer guide, and Bash fluency benchmark.
