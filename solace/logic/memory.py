from __future__ import annotations

from pathlib import Path
import json
from typing import List, Dict

MEMORY_FILE = Path(__file__).resolve().parents[2] / 'storage' / 'user_memory.json'

DEFAULT_MEM = {"always": [], "never": []}


def load_memory() -> Dict[str, List[str]]:
    if not MEMORY_FILE.exists():
        return DEFAULT_MEM.copy()
    try:
        return json.loads(MEMORY_FILE.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        return DEFAULT_MEM.copy()


def save_memory(data: Dict[str, List[str]]) -> None:
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_FILE.write_text(json.dumps(data, indent=2), encoding='utf-8')


def remember(fact: str) -> None:
    data = load_memory()
    data.setdefault('always', []).append(fact)
    save_memory(data)


def forget(item: str) -> None:
    data = load_memory()
    data.setdefault('never', []).append(item)
    save_memory(data)
