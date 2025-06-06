import json
from pathlib import Path
from typing import List, Dict

BASE_DIR = Path(__file__).resolve().parents[2] / 'storage' / 'todo'
TODO_FILE = BASE_DIR / 'todo.json'


def _load() -> List[Dict]:
    if not TODO_FILE.exists():
        return []
    try:
        return json.loads(TODO_FILE.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        return []


def _save(tasks: List[Dict]):
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    TODO_FILE.write_text(json.dumps(tasks, indent=2), encoding='utf-8')


def add_task(task: str, timestamp: str) -> Dict:
    tasks = _load()
    item = {'task': task, 'status': 'incomplete', 'added': timestamp}
    tasks.append(item)
    _save(tasks)
    snap = BASE_DIR / f"{timestamp.replace(':', '-').replace(' ', '_')}.json"
    snap.write_text(json.dumps(item, indent=2), encoding='utf-8')
    return item


def list_tasks(status: str | None = None) -> List[Dict]:
    tasks = _load()
    if status:
        return [t for t in tasks if t.get('status') == status]
    return tasks


def mark_complete(index: int) -> bool:
    tasks = _load()
    if 0 <= index < len(tasks):
        tasks[index]['status'] = 'complete'
        _save(tasks)
        return True
    return False


def delete_task(index: int) -> bool:
    tasks = _load()
    if 0 <= index < len(tasks):
        tasks.pop(index)
        _save(tasks)
        return True
    return False
