import json
import re
from pathlib import Path

# Path to the bundled programming facts
DATA_FILE = Path(__file__).resolve().parents[2] / 'data' / 'facts_seed.json'


def _load_facts():
    """Return the list of facts from the seed file."""
    try:
        with DATA_FILE.open('r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    return data.get('facts', [])


def _tokenize(text: str):
    return re.findall(r"\w+", text.lower())


def _has_code_snippet(text: str) -> bool:
    markers = ['<', '>', '{', '}', '```', '$', '=', '()', ';']
    return any(m in text for m in markers)


def _score_fact(fact, keywords):
    title = fact.get('title', '').lower()
    desc = fact.get('description', '').lower()
    tags = [t.lower() for t in fact.get('tags', [])]

    score = 0
    tag_overlap = len(keywords.intersection(tags))
    score += tag_overlap * 3

    for word in keywords:
        if word in title or word in desc:
            score += 1

    if _has_code_snippet(desc):
        score += 2

    return score, tag_overlap


def generate_code(task: str) -> str:
    """Return a relevant code snippet description for the given task."""
    facts = _load_facts()
    if not facts:
        return "I don't know how to do that yet. Try teaching me in /mode teach."

    keywords = set(_tokenize(task))
    matches = []
    for fact in facts:
        score, overlap = _score_fact(fact, keywords)
        if score > 0:
            matches.append((score, overlap, fact['description']))

    if not matches:
        return "I don't know how to do that yet. Try teaching me in /mode teach."

    matches.sort(key=lambda x: (x[0], x[1]), reverse=True)
    best_score = matches[0][0]
    top = [m for m in matches if m[0] == best_score]

    if len(top) > 1:
        # combine short descriptions when they all match equally
        short = [t[2] for t in top if len(t[2]) < 80]
        if len(short) > 1:
            return "\n".join(short)
        top.sort(key=lambda x: x[1], reverse=True)

    return top[0][2]
