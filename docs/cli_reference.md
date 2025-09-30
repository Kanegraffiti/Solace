# CLI Reference

Solace commands all start with `/`. The launcher also accepts `--speak` and `--listen` flags to temporarily enable voice features for the current session.

| Command | Description |
| ------- | ----------- |
| `/diary [text]` | Add a diary entry. Prompts for timestamp and tags when needed. |
| `/notes [text]` | Capture a note entry. |
| `/todo [text]` | Log a todo reminder. |
| `/quote [text]` | Save an inspirational quote. |
| `/search <query>` | Search entries with fuzzy matching across content and tags. |
| `/export [markdown|pdf] [path]` | Export all entries to Markdown or PDF. |
| `/teach <language> [text]` | Store a code/example snippet manually. |
| `/remember <language> <query>` | Retrieve stored snippets matching the query. |
| `/code <language> <keyword>` | Display snippets with syntax highlighting. |
| `/mimic <text>` | Generate a rule-based conversational reply. |
| `/listen` | Capture speech input when STT is enabled. |
| `/settings [subcommand]` | Configure password, voice, tone, alias, backups and fallback mode. |
| `/help` | Show the help table inside Solace. |
| `/exit` | Quit the program. |

Colon shortcuts like `:diary Something happened today` also record entries without the slash prefix.
