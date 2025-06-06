import json
from pathlib import Path
from typing import List, Dict

from ..utils.datetime import ts_to_filename

BASE_DIR = Path(__file__).resolve().parents[2] / 'storage' / 'todo'
TASK_FILE = BASE_DIR / 'tasks.json'


def _load_tasks() -> List[Dict]:
    if not TASK_FILE.exists():
        return []
    with TASK_FILE.open('r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def _save_tasks(tasks: List[Dict]):
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    with TASK_FILE.open('w', encoding='utf-8') as f:
        json.dump(tasks, f, indent=2)


def add_task(text: str, timestamp: str, tags: List[str] | None = None, important: bool = False) -> Dict:
    tasks = _load_tasks()
    next_id = tasks[-1]['id'] + 1 if tasks else 1
    item = {
        'id': next_id,
        'task': text,
        'done': False,
        'created_at': timestamp,
        'tags': tags or [],
        'important': important,
    }
    tasks.append(item)
    _save_tasks(tasks)
    snap = BASE_DIR / f"{ts_to_filename(timestamp)}.json"
    with snap.open('w', encoding='utf-8') as f:
        json.dump(item, f, indent=2)
    return item


def list_tasks() -> List[Dict]:
    return _load_tasks()


def mark_done(task_id: int) -> bool:
    tasks = _load_tasks()
    changed = False
    for t in tasks:
        if t['id'] == task_id:
            if not t['done']:
                t['done'] = True
                changed = True
            break
    if changed:
        _save_tasks(tasks)
    return changed
