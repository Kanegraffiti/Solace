import json
from pathlib import Path
from typing import List, Dict

from getpass import getpass
import json

from .notes import load_notes
from ..settings_manager import SETTINGS
from ..utils.crypto_manager import decrypt_data
from ..utils.keys import get_key
from ..utils.encryption import decrypt_bytes
from ..utils.storage import DIARY_DIR, KNOWLEDGE_DIR



def _load_diary_entries(password: str | None = None) -> List[Dict]:
    DIARY_DIR.mkdir(parents=True, exist_ok=True)
    entries: List[Dict] = []
    for fpath in sorted(DIARY_DIR.glob('*')):
        if fpath.suffix not in {'.txt', '.enc', '.solace'}:
            continue
        if fpath.suffix == '.solace':
            try:
                obj = json.loads(fpath.read_text(encoding='utf-8'))
                if password is None:
                    password = getpass('Encryption password: ')
                data = decrypt_data(obj.get('data', ''), password)
            except Exception:
                print(f'Could not decrypt {fpath.name}')
                continue
        elif fpath.suffix == '.enc':
            data = decrypt_bytes(fpath.read_bytes(), get_key()).decode('utf-8')
        else:
            data = fpath.read_text(encoding='utf-8')
        lines = data.splitlines()
        meta = {'timestamp': fpath.stem}
        text_lines = []
        for line in lines:
            if line.startswith('Title:'):
                meta['title'] = line[6:].strip()
            elif line.startswith('Date:'):
                meta['timestamp'] = line[5:].strip()
            elif line.startswith('Mood:'):
                meta['mood'] = line[5:].strip()
            elif line.startswith('Tags:'):
                meta['tags'] = line[5:].split()
            elif line.startswith('-------------------------'):
                text_lines = lines[lines.index(line)+1:]
                break
        if not text_lines:
            text_lines = lines
        meta['text'] = '\n'.join(text_lines).strip()
        entries.append(meta)
    return entries


def _load_knowledge_entries(password: str | None = None) -> List[Dict]:
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    entries: List[Dict] = []
    for fpath in sorted(KNOWLEDGE_DIR.glob('*')):
        if fpath.suffix not in {'.json', '.enc', '.solace'}:
            continue
        if fpath.suffix == '.solace':
            try:
                obj = json.loads(fpath.read_text(encoding='utf-8'))
                if password is None:
                    password = getpass('Encryption password: ')
                data = decrypt_data(obj.get('data', ''), password)
            except Exception:
                print(f'Could not decrypt {fpath.name}')
                continue
        elif fpath.suffix == '.enc':
            data = decrypt_bytes(fpath.read_bytes(), get_key()).decode('utf-8')
        else:
            data = fpath.read_text(encoding='utf-8')
        try:
            obj = json.loads(data)
        except json.JSONDecodeError:
            continue
        obj['text'] = obj.get('content', '')
        entries.append(obj)
    return entries


def search(query: str, password: str | None = None) -> List[Dict]:
    q = query.lower()
    results: List[Dict] = []
    sources = _load_diary_entries(password) + _load_knowledge_entries(password) + load_notes()
    for item in sources:
        text = item.get('text', '').lower()
        tags = [t.lower() for t in item.get('tags', [])]
        if q.startswith('#'):
            if q[1:] in tags:
                results.append(item)
        elif q in text or any(q in t for t in tags):
            results.append(item)
    results.sort(key=lambda x: x.get('timestamp', ''))
    return results
