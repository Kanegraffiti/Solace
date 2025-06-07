# User Guide

This guide introduces the basic commands available in Solace. Start the program with:

```bash
python main.py
```

All interactions happen through the command line. Commands begin with `/`.

## Common Commands

- `/diary` – Add a new diary entry. You will be prompted for tags and whether the entry should be encrypted.
- `/notes` – Write a short markdown note with optional tags.
- `/todo` – Manage a small todo list. Use `add`, `list`, `done` and `delete` subcommands.
- `/ask` – Ask how to perform a coding task. Solace searches its stored examples and responds if it knows the answer.
- `/code` – Generate a code snippet from stored examples.
- `/debug` – Search for solutions to known error messages.
- `/teachcode` – Add a new code example for later reference.
- `/memory` – Show items marked as “always remember” or “never bring up”.
- `/summary` – Display how many entries and examples you have stored.
- `/speak` – Speak text aloud if voice packages are installed.
- `/help` – Show all available commands.
- `/exit` – Quit the program.

### Adding Entries

When you run `/diary` without text after it, Solace opens a multiline prompt. Finish by entering a blank line. Each entry is saved with a timestamp and a simple mood detected from keywords.

Encrypted entries are stored with the `.enc` extension. Keep the key file in `storage/.key` safe if you use encryption.

### Searching

Solace provides basic search with the `/recall` command. Type a keyword or `#tag` to list matching diary entries, notes or knowledge items.


