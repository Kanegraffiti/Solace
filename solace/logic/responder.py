from pathlib import Path
import json
import re


DATA_FILE = Path(__file__).resolve().parents[2] / 'data' / 'facts_seed.json'


def _load_facts():
    try:
        with DATA_FILE.open('r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    return data.get('facts', [])


def _score_fact(fact, question_words, question_lower):
    score = 0
    tags = fact.get('tags', [])
    for tag in tags:
        if tag.lower() in question_lower:
            score += 2
    title = fact.get('title', '').lower()
    desc = fact.get('description', '').lower()
    for word in question_words:
        if word in title or word in desc:
            score += 1
    return score


def get_response(question: str) -> str:
    facts = _load_facts()
    if not facts:
        return "No facts available."

    question_lower = question.lower()
    question_words = re.findall(r"\w+", question_lower)

    scored = []
    for fact in facts:
        score = _score_fact(fact, question_words, question_lower)
        if score > 0:
            scored.append((score, fact))

    if not scored:
        return "I don't have information about that."

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:3]
    parts = []
    for _, fact in top:
        part = f"{fact['title']}\n{fact['description']}"
        tags = fact.get('tags')
        if tags:
            part += f"\nTags: {', '.join(tags)}"
        parts.append(part)
    return "\n\n".join(parts)
