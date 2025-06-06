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
    for tag in fact.get('tags', []):
        if tag.lower() in question_lower:
            score += 2
    title = fact.get('title', '').lower()
    desc = fact.get('description', '').lower()
    for word in question_words:
        if word in title or word in desc:
            score += 1
    return score


def get_answer(question: str) -> str:
    facts = _load_facts()
    if not facts:
        return "No facts available."

    question_lower = question.lower()
    question_words = re.findall(r"\w+", question_lower)

    best_score = 0
    best_fact = None
    for fact in facts:
        score = _score_fact(fact, question_words, question_lower)
        if score > best_score:
            best_score = score
            best_fact = fact

    if not best_fact:
        return "I don't have information about that."

    response = f"{best_fact['title']}\n{best_fact['description']}"
    tags = best_fact.get('tags')
    if tags:
        response += f"\nTags: {', '.join(tags)}"
    return response
