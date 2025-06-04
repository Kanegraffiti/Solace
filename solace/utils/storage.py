import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / 'data'

ENTRY_FILE = DATA_DIR / 'entries.json'
FACT_FILE = DATA_DIR / 'facts.json'
MEMORY_FILE = DATA_DIR / 'memory_index.json'


def load_json(path, default):
    if not path.exists():
        return default
    with path.open('r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


# high level helpers

def load_entries():
    return load_json(ENTRY_FILE, [])


def save_entries(entries):
    save_json(ENTRY_FILE, entries)


def load_facts():
    return load_json(FACT_FILE, {})


def save_facts(facts):
    save_json(FACT_FILE, facts)
