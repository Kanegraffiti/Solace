# Solace

Solace is a local-first personal journal, memory search tool, offline coding
companion, Excel helper, safe file manager, and optional on-device AI shell.
The primary interface is a Rich terminal CLI designed to work especially well
in Termux. A Textual TUI and local React/FastAPI interface remain optional.

The journal, memory recall, Bash/Python knowledge, Excel reference layer, file
manager, encryption, and local Qwen integration do not require a hosted AI
service. Qwen is used as an explanation/reasoning layer where useful; it does
not receive unrestricted shell execution.

## What Solace does

- **Journal and personal knowledge:** diary entries, notes, todos, quotes, tags,
  search, and weekly/monthly recaps.
- **Local memory companion:** `/chat` uses local journal recall and bundled
  deterministic knowledge rather than a cloud chatbot.
- **Offline coding reference:** Bash/Python recipes, Bash syntax explanations,
  common-error matching, and user-taught snippets.
- **Excel skill:** formula lookup, PivotTable/chart/table/data-validation
  guidance, workbook inspection, safe formula writes, chart creation, and
  pivot-style summary worksheets.
- **Safe file manager:** natural commands to find, copy, move, rename, organize,
  trash, restore, inspect history, and undo supported file operations.
- **Optional local Qwen:** Qwen2.5-Coder-1.5B-Instruct Q4_K_M through llama.cpp
  with `/qwen` or the standalone `qwen` command.
- **Privacy controls:** journal content is encrypted at rest by default, with an
  optional startup password.
- **Export, backup, and sync:** Markdown/PDF export, local backups, and optional
  S3 or WebDAV sync.
- **Scriptable terminal workflow:** `solace` works from any directory and still
  supports `-c`, `--command-file`, and the Textual TUI.

## Requirements

Core Solace requires:

- Python 3.9+
- Git

`openpyxl` is installed with the core dependencies for Excel workbook support.

Optional components add their own requirements:

- Node.js/npm for the web frontend
- platform audio libraries for voice features
- Termux + about 1.12 GB for the recommended Qwen GGUF, plus llama.cpp build
  files, if you enable local Qwen

## Install in Termux

```bash
pkg install -y git python
git clone https://github.com/Kanegraffiti/Solace.git
cd Solace
bash install.sh
```

The Termux installer deliberately does **not** ask pip to compile `cryptography`
from source. Termux ships an Android-patched `python-cryptography` package, so
`install.sh` uses that package and creates the project `.venv` with
`--system-site-packages`.

The installer also handles two current Termux edge cases:

1. Termux packages pip separately, so `python-pip` is established before
   `python-cryptography` is configured.
2. If a previous cryptography package setup failed while pip was missing, Solace
   detects the missing CFFI runtime and performs one bounded reinstall of
   Termux's package so its own dependency setup can run correctly.

Some Android/Termux/Python combinations can additionally have native loader
visibility problems. `solace/termux_compat.py` first loads the active
interpreter's `libpython` with platform-correct global visibility and uses
bounded file-based re-exec fallbacks only when necessary. No Python version is
hard-coded.

A full `pkg upgrade` is not the normal recovery step for these Solace install
checks. If a compatibility check fails, the installer surfaces the underlying
traceback so the actual missing library/symbol can be diagnosed.

The Termux core dependency file intentionally excludes optional web-server and
voice stacks that can trigger large native source builds on Android.

If Termux later upgrades Python, rerunning `bash install.sh` detects an obsolete
Solace `.venv` and recreates only that disposable environment. Your journal,
configuration, Qwen model, llama.cpp checkout, and files outside `.venv` remain
untouched.

On Termux, the launchers are written directly to `$PREFIX/bin`.

Start Solace from anywhere:

```bash
solace
```

### Refresh an existing checkout

```bash
cd ~/Solace
git pull
bash install.sh
```

You can also refresh only launchers/configuration:

```bash
python3 install.py --skip-deps
```

Direct checkout fallback:

```bash
python3 solace/launcher.py
```

## Startup mini-manual

Interactive starts show a small quick-start panel.

```text
/manual off      hide it on future starts
/manual          show it now
/manual on       restore it on startup
/manual status   show the current setting
```

Scripted `solace -c ...` runs do not print the startup manual.

## Excel skill

Solace treats Excel as a first-class local skill rather than simply asking the
model to guess formulas.

### Formula knowledge

`/excel functions` uses openpyxl's local Excel formula-name registry plus a
modern-function supplement (dynamic arrays, LAMBDA helpers, regex functions,
GROUPBY/PIVOTBY, XLOOKUP/XMATCH, and related functions).

Detailed deterministic recipes are bundled for the most-used formula families,
including:

- SUM/SUMIF/SUMIFS, COUNT/COUNTIF/COUNTIFS, AVERAGEIF/AVERAGEIFS
- IF/IFS/AND/OR/NOT, IFERROR/IFNA
- XLOOKUP/VLOOKUP/HLOOKUP, INDEX/MATCH/XMATCH
- FILTER/UNIQUE/SORT/SORTBY/SEQUENCE
- LET/LAMBDA
- TEXTJOIN/CONCAT/TEXTSPLIT/TEXTBEFORE/TEXTAFTER
- date/time, finance, statistics, rounding, regex and array helpers

Examples:

```text
/excel XLOOKUP
/excel SUMIFS
/excel how do I fix #SPILL!
/excel functions regex
/excel functions look
```

If a question is outside the deterministic recipes and local Qwen is ready,
Solace opens Qwen with an Excel-specific prompt that instructs it not to invent
functions and to call out version limitations.

### PivotTables and charts

```text
/excel pivot table
/excel chart
/excel conditional formatting
/excel data validation
```

Solace teaches native Excel PivotTable setup step-by-step. Workbook automation
uses `openpyxl`, which preserves existing native PivotTables but is not intended
to create new ones. Therefore `/excel summarize` creates a normal, clearly
labelled grouped summary worksheet rather than claiming it created a native
PivotTable.

### Inspect a workbook

```text
/excel inspect sales.xlsx
```

If the filename is not an exact path, Solace uses the same file search and
ambiguity handling as `/file`. Inspection reports each sheet's row/column count,
formula count, Excel Tables, charts, and existing pivots.

### Write a formula safely

```text
/excel set sales.xlsx | Sales | E2 | SUM(B2:D2)
```

Workbook-changing Excel commands create a **new copy** such as
`sales-formula.xlsx`; the source workbook is not silently overwritten.

### Create a chart

```text
/excel make-chart sales.xlsx | Sales | A1:B20 | column
/excel make-chart sales.xlsx | Sales | A1:B20 | line | H2
/excel make-chart sales.xlsx | Sales | A1:B20 | pie
```

Supported automated chart types in this first version are bar, column, line,
and pie. Solace's teaching layer also explains when scatter and other native
Excel chart types are more appropriate.

### Create a pivot-style summary sheet

```text
/excel summarize sales.xlsx | Sales | Region | Revenue | sum
/excel summarize sales.xlsx | Sales | Region | Revenue | average
/excel summarize sales.xlsx | Sales | Region | OrderID | count
```

The output is a new workbook copy containing `Solace Summary`.

## Safe file manager

The file manager uses deterministic Python operations. Qwen does **not** get
`rm`, `mv`, `cp`, or arbitrary shell access.

### Natural file commands

```text
/file find my invoice
/file rename project invoice.pdf to final invoice.pdf
/file copy DavidDoku.jpg to ~/Documents
/file move report.xlsx to ~/Documents/Finance
/file make folder Client Assets
/file show 20 largest files
/file files modified today
```

If exactly one source matches, Solace shows the action and asks for confirmation.
If several files match, it shows numbered choices. If nothing matches, it asks
for an exact path, so the original high-level action can continue without being
retyped.

Scripted/non-interactive mode never auto-confirms file-changing operations.

### Safe delete and restore

```text
/file delete old-budget.xlsx
/file trash old-report.pdf
/file show trash
/file restore old-budget.xlsx
/file undo
```

`delete`, `remove`, and `trash` all mean the same safe operation: move the item
to `~/.solace/trash/`. Solace never maps those commands directly to `rm`.

### History

```text
/file history
```

Solace records its own file transactions in:

```text
~/.solace/file-history.jsonl
```

History is local and records paths/actions needed for recovery and undo.

### File safety boundary

Mutations are restricted to user-owned roots: the user's home directory and
Termux shared-storage roots discovered under `~/storage/`. Existing destination
paths are not overwritten. Symlink-resolved destinations outside those roots are
refused.

## Local Qwen on Termux

Qwen remains optional. Solace does **not** download a gigabyte-scale model or
compile llama.cpp during a normal install.

Set it up explicitly:

```bash
cd ~/Solace
bash scripts/setup-qwen-termux.sh
```

Or:

```bash
python3 install.py --skip-deps --setup-qwen
```

The helper reuses an existing `~/llama.cpp` checkout when available, builds only
`llama-cli`, downloads the recommended Qwen Q4_K_M model only when missing,
verifies its published SHA-256, and installs the standalone `qwen` command.

Phone-friendly defaults:

- context: `2048`
- threads: `4`
- generated-token limit: `512`
- llama.cpp binary: `~/llama.cpp/build/bin/llama-cli`
- model: `~/models/qwen2.5-coder-1.5b/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf`

Override them without editing source:

```bash
export SOLACE_QWEN_CONTEXT=1024
export SOLACE_QWEN_THREADS=2
export SOLACE_QWEN_TOKENS=256
export SOLACE_LLAMA_CLI="$HOME/other-llama/build/bin/llama-cli"
export SOLACE_QWEN_MODEL="$HOME/models/another-model.gguf"
```

Use directly:

```bash
qwen
qwen "Explain this Bash pipeline and point out anything dangerous"
```

Inside Solace:

```text
/qwen status
/qwen Write a Bash function that checks whether a command exists
/qwen
```

Solace invokes llama.cpp with an argument list rather than through a shell, so a
prompt is not interpreted as a Bash command.

## Using the CLI

Plain text that is not a command remains a diary entry.

```text
I finished the first deployment today
/notes Release checklist and rollback steps
/todo Verify the production backup
/search deployment
/summarize week
/chat What did I decide about the deployment?
/excel XLOOKUP
/file find deployment notes
/qwen Explain rsync --delete and its risks
```

### Main commands

| Command | Purpose |
| --- | --- |
| `/diary [text]`, `/notes [text]`, `/todo [text]`, `/quote [text]` | Save a dated, tagged entry. |
| `/search <query>` | Search journal text, tags, and dates. |
| `/summarize [week\|month]` | Show recent extractive recaps. |
| `/chat <message>` | Talk with the deterministic local memory companion. |
| `/excel <question>` | Excel formulas, errors, PivotTables, charts and workbook tools. |
| `/excel functions [term]` | Search the local Excel function-name index. |
| `/file <request>` | Safely find/copy/move/rename/trash/restore user files. |
| `/file history` | Show file operations performed by Solace. |
| `/file undo` | Undo the latest supported Solace file mutation. |
| `/qwen <prompt>` | Start local Qwen with an initial prompt. |
| `/qwen` | Open interactive local Qwen. |
| `/qwen status` | Check whether the local Qwen runtime/model are ready. |
| `/teach <language> [text]` | Add an example, error, or tip to local training data. |
| `/remember <language> <query>` | Retrieve matching taught material. |
| `/code bash <topic>` | Look up a Bash command/template with safety notes. |
| `/code python <topic>` | Look up a bundled Python recipe. |
| `/ask bash <topic>` | Explain a supported Bash concept. |
| `/debug <error>` | Match a common Bash error to likely fixes. |
| `/explain [bash] <command>` | Break down Bash tokens, flags, pipes, and redirects. |
| `/manual [on\|off\|status]` | Show/configure the startup mini-manual. |
| `/mimic <text>` | Use the rule-based mimic responder. |
| `/export [markdown\|pdf] [path]` | Export journal entries. |
| `/backup [options]` | Create a local backup archive. |
| `/sync [backend] [options]` | Sync through a configured backend. |
| `/listen` | Capture speech when STT is enabled. |
| `/settings` | Manage password, voice, tone, alias, backup/restore and related settings. |
| `/help` | Show the full in-app command list. |
| `/exit`, `exit`, `quit` | Leave Solace. |

Colon shortcuts (`:diary`, `:notes`, `:todo`, and `:quote`) remain supported.

## Scripted use

```bash
solace --accept-defaults \
  -c "/diary Automated check completed" \
  -c "/search automated"

solace --accept-defaults --command-file commands.txt
```

The startup manual is suppressed during scripted use. File-changing actions
also refuse to auto-confirm in scripted mode.

## Textual TUI

```bash
solace --tui
```

## Data and privacy

Primary local paths include:

- `~/.solaceconfig.json` — configuration and encryption key material
- `~/.solace/journal/entries.json` — journal records
- `~/.solace/training/` — taught snippets
- `~/.solace/conversation/` — mimic data
- `~/.solace/cache/` — generated/cache files
- `~/.solace/trash/` — recoverable file deletions performed through `/file`
- `~/.solace/file-history.jsonl` — file-manager transaction history
- `~/.solace/session.log` — short command/session activity log

Journal content is encrypted by default. Keep a safe copy of
`~/.solaceconfig.json`; losing its key material can make encrypted data
unrecoverable.

Local Qwen runs on the device through llama.cpp and does not require an OpenAI,
Gemini, or other hosted-model API key. S3/WebDAV and other network-capable
features remain opt-in.

## Backup and sync

Backups contain an encrypted journal payload. By default they also include a
plain-text restore copy and configuration for recovery. Use `--no-restore` if
the archive must not contain that restore copy, and protect backup files
accordingly.

S3 sync requires `boto3`; WebDAV uses Python's standard library. Configure and
test remote backends with dry-run settings before a real upload.

## Local web app (optional)

```bash
make dev
```

By default the API uses port 8000 and Vite uses port 4173. Treat it as a local
development service rather than exposing it directly to an untrusted network.
See [`web/README.md`](web/README.md) for web-specific details.

## Repository map

| Path | Contents |
| --- | --- |
| `solace/launcher.py` | Supported launcher and `/qwen`, `/excel`, `/file`, `/manual` registration. |
| `solace/excel_skill.py` | Excel formula knowledge and safe workbook operations. |
| `solace/file_skill.py` | Deterministic safe file search/mutation/history/undo engine. |
| `solace/local_llm.py` | Safe llama.cpp/Qwen discovery and process invocation. |
| `solace/termux_compat.py` | Android/Termux native-loader compatibility for cryptography. |
| `solace/user_manual.py` | Tiny startup manual and visibility preference. |
| `scripts/qwen.sh` | Standalone Termux `qwen` wrapper. |
| `scripts/setup-qwen-termux.sh` | Explicit llama.cpp build + verified Qwen setup. |
| `requirements-termux.txt` | Termux-safe core pip dependencies. |
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

Frontend:

```bash
cd web/frontend
npm install
npm run build
```

Further documentation lives in [`docs/`](docs/).
