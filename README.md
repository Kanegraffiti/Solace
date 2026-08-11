# Solace

Solace is an offline, local-first journaling and knowledge companion.

Its conversational and coding features run locally: `/chat` provides a transparent
rule-based response, while `/code bash <topic>` and `/code python <topic>` retrieve
inspectable recipes without sending diary text to an online service. Solace does not
claim consciousness; “sentient” here means that it can respond to you offline.

It includes:
- a **CLI app** for journaling, notes, todos, quotes, memory search, and code/snippet recall;
- a **local web app** (`web/`) for browsing and managing entries/snippets on your machine;
- optional encryption, backup, and sync helpers.

All core data is stored under your home directory (for example `~/.solace/` and `~/.solaceconfig.json`).

## Quick start

```bash
git clone https://github.com/Kanegraffiti/Solace.git
cd Solace
python install.py
solace
```

If the launcher is not available yet, run:

```bash
python main.py
```

Inside Solace, run `/help` to see available commands.

## Repository layout

- `main.py` – CLI entrypoint.
- `journal.py` – journal storage/export helpers.
- `trainer.py` – snippet teaching and recall helpers.
- `solace/` – shared application modules (logic, config, utilities, plugins, knowledge files).
- `web/` – local FastAPI + React application.
- `docs/` – user and developer documentation.
- `tests/` – automated test suite.

## Development

Install dependencies:

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

Run checks:

```bash
ruff check .
flake8 .
mypy .
pytest
```

## Web app (optional)

From the repo root:

```bash
make dev
```

This starts the local backend and frontend dev servers.

## Documentation

See:
- `docs/overview.md`
- `docs/user_guide.md`
- `docs/cli_reference.md`
- `docs/settings.md`
- `docs/developer_guide.md`
