# User Guide

This guide introduces the basic commands available in Solace. Start the program with:

```bash
solace
```

All interactions happen through the command line. Commands begin with `/`.

## Common Commands

- `/diary` – Add a new diary entry or import a document. You will be prompted for tags and whether the entry should be encrypted.
- `/notes` – Write a short markdown note or import a document with optional tags.
- `/todo` – Manage a small todo list. Use `add`, `list`, `done` and `delete` subcommands.
- `/ask` – Ask how to perform a coding task. Solace searches its stored examples and responds if it knows the answer.
- `/code` – Generate a code snippet from stored examples.
- `/debug` – Search for solutions to known error messages.
- `/teachcode` – Add a new code example or import a document containing code. When importing, Solace automatically extracts fenced code blocks.
- `/memory` – Show items marked as “always remember” or “never bring up”.
- `/summary` – Display how many entries and examples you have stored.
- `/speak` – Speak text aloud if voice packages are installed.
- `/unlock` – Decrypt a file saved by Solace.
- `/demo` – Display a short demo sequence.
- `/install voice` – Install optional voice packages.
- `/mode settings` – Configure Solace preferences.
- `/help` – Show all available commands.
- `/exit` – Quit the program.

After answering a coding question with `/ask`, `/code` or `/debug` Solace now asks “Did it work?”. If you reply no you can choose to teach the correct solution via `/teachcode`.

### Adding Entries

When you run `/diary` without text after it, Solace opens a multiline prompt. Finish by entering a blank line. Each entry is saved with a timestamp and a simple mood detected from keywords.
You can also choose to import a supported document (`.txt`, `.md`, `.rst`, `.pdf`, `.epub`) instead of typing.

Encrypted entries are stored with the `.enc` extension. Keep the key file in `storage/.key` safe if you use encryption.

### Searching

Solace provides basic search with the `/recall` command. Type a keyword or `#tag` to list matching diary entries, notes or knowledge items.



## Settings

Use `/mode settings` to change your preferences.
You can toggle autosave, typing effects, encryption defaults and more. The menu also lets you set a password lock for Solace. The password is stored as a hash alongside an optional hint.

If you lose the password simply delete `settings/settings.json` to start over.

