from __future__ import annotations

from pathlib import Path
import json
import re
from collections import Counter

from ..utils.filehandler import read_text

DATA_FILE = Path(__file__).resolve().parents[2] / 'data' / 'facts_seed.json'

# very small set of stopwords just to avoid trivial tags
STOPWORDS = {
    'the', 'and', 'with', 'that', 'this', 'from', 'shall', 'for', 'have', 'are',
    'was', 'were', 'your', 'you', 'about', 'there', 'which', 'into', 'their',
    'these', 'those', 'them', 'they', 'what', 'when', 'where', 'while', 'will',
    'would', 'could', 'should', 'a', 'an', 'of', 'in', 'to', 'on', 'is', 'it', 'as'
}


def _read_text(path: Path) -> str:
    """Return the raw text from the supported file."""
    return read_text(path)


def _split_chunks(text: str) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    return paragraphs


def _guess_tags(text: str, n: int = 5) -> list[str]:
    words = re.findall(r'[A-Za-z]{4,}', text.lower())
    filtered = [w for w in words if w not in STOPWORDS]
    counts = Counter(filtered)
    tags = [w for w, _ in counts.most_common(n)]
    return tags


def _chunk_to_fact(chunk: str) -> dict:
    sentences = re.split(r'(?<=[.!?])\s+', chunk.strip())
    title = sentences[0].replace('\n', ' ') if sentences else chunk[:60]
    tags = _guess_tags(chunk)
    return {
        'title': title,
        'description': chunk.strip(),
        'tags': tags
    }


def process_file(path: str) -> int:
    """Read the given file, convert chunks to facts and store them.

    Returns the number of facts added.
    """
    p = Path(path)
    text = _read_text(p)
    chunks = _split_chunks(text)
    facts = [_chunk_to_fact(c) for c in chunks]

    if DATA_FILE.exists():
        try:
            data = json.loads(DATA_FILE.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            data = {}
    else:
        data = {}

    existing = data.get('facts', [])
    existing.extend(facts)
    data['facts'] = existing

    DATA_FILE.write_text(json.dumps(data, indent=2), encoding='utf-8')
    return len(facts)

