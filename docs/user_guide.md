# User Guide

Start Solace from your terminal:

```bash
solace
```

All commands begin with a `/` prefix. If you simply type text and press enter, Solace treats it as a diary entry.

## Journaling commands

- `/diary [text]` – capture a diary entry. If you omit the text Solace opens a multiline prompt. You will be asked for the date/time and optional comma-separated tags.
- `/notes [text]` – store study or project notes with the same prompts.
- `/todo [text]` – record a to-do reminder.
- `/quote [text]` – save quotes or inspiration.

Each command writes to a shared JSON file under `~/.solace/journal/entries.json`. When encryption is enabled the body is stored using Fernet and decrypted automatically after you enter your password.

You can also start an entry with `:diary`, `:notes`, `:todo` or `:quote` followed by text without the slash command.

## Searching your writing

Use `/search <keywords>` to look through existing entries. The search considers both content and tags and will return the best matches with a similarity score.

## Exporting

`/export [markdown|pdf] [path]` creates a Markdown (`.md`) or PDF snapshot of all entries. When no path is provided Solace stores the export inside the journal folder.

## Training snippets

The training system keeps language-tagged snippets that you curate manually:

- `/teach <language> [text]` – add a code example, tip or error note. When text is omitted a multiline prompt appears and you can classify the snippet as an example, error or tip.
- `/remember <language> <query>` – list stored snippets whose text matches the query.
- `/code <language> <keyword>` – similar to `/remember` but renders code using syntax highlighting.

Snippets live in `~/.solace/training/` along with a JSON index and timestamped session logs created by `trainer.record_session`.

## Mimic replies

`/mimic <text>` runs the rule-based responder. Solace compares your text against triggers stored in `~/.solace/conversation/guide.json` and replies with the closest match, falling back to a simple apology or encouragement depending on the configured fallback mode.

## Voice helpers

If the optional voice dependencies are installed you can toggle text-to-speech and speech recognition under `/settings voice`. Once enabled:

- Solace speaks key confirmations via the text-to-speech engine.
- `/listen` captures a short utterance using PocketSphinx and prints the recognised text.

## Settings

Run `/settings` to see available subcommands:

- `password` – configure or remove the startup password.
- `voice` – enable or disable text-to-speech (TTS) and speech-to-text (STT).
- `tone <friendly|quiet|verbose>` – change how verbose mimic responses are.
- `alias <name>` – update the stored launcher name.
- `backup` – create an encrypted restore point of your Solace storage directory (use `--dry-run` to preview).
- `restore <archive>` – unpack a previously created archive.
- `info` – display paths and the current version.
- `fallback <mode>` – set the mimic fallback response (e.g. `apologise`, `gentle`, `encourage`).

All settings are saved to `~/.solaceconfig.json`. The storage directory is created automatically if it does not already exist.

### Sync and backups

- `/backup` always encrypts journal data using your configuration keys and includes a plain-text restore point by default.
- `/sync` packages the same archive and sends it to the configured backend (local, `s3` or `webdav`). Use `--dry-run` to see what would happen before any files are written.
- Network uploads remain disabled until you enable the relevant backend in `~/.solaceconfig.json`; leaving `enabled` as `false` keeps Solace offline.
- The `sync.dry_run` flag in `~/.solaceconfig.json` is `true` by default so your first runs only preview actions. Set it to `false` when you're comfortable with the flow.

## Leaving Solace

Type `/exit`, `exit`, `quit` or use `Ctrl+C`/`Ctrl+D` to close the program. A simple session log is kept inside `~/.solace/session.log`.
