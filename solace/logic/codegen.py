import json
import re
from pathlib import Path
from typing import Optional, Tuple, List, Dict

BASE_DIR = Path(__file__).resolve().parents[1] / "knowledge" / "programming"
LANGUAGES = ["python", "bash", "html", "javascript", "css"]
DEFAULT_LANGUAGE = "python"


def sanitize_input(text: str) -> str:
    return text.strip().lower()


def _tokenize(text: str) -> List[str]:
    return re.findall(r"\w+", text.lower())


def _load_examples(language: str) -> List[Dict]:
    path = BASE_DIR / language / "examples.json"
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []


def detect_language(text: str) -> str:
    t = text.lower()
    for lang in LANGUAGES:
        if lang in t:
            return lang
    return DEFAULT_LANGUAGE


def _special_cases(text: str) -> Optional[Tuple[str, str]]:
    """Return hard coded snippets for very common questions."""
    t = text.lower()
    if "reverse" in t and "string" in t and "python" in t:
        return ("text[::-1]", "Use slicing with step -1 to reverse a string.")
    return None


def find_best_match(language: str, query: str) -> Optional[Dict]:
    examples = _load_examples(language)
    if not examples:
        return None
    tokens = set(_tokenize(query))
    best = None
    best_score = 0
    for ex in examples:
        kws = set(map(str.lower, ex.get("keywords", [])))
        score = len(tokens & kws)
        if score > best_score:
            best_score = score
            best = ex
    return best


def lookup(text: str) -> Optional[Tuple[str, str]]:
    text = sanitize_input(text)
    lang = detect_language(text)
    special = _special_cases(text)
    if special:
        return special
    match = find_best_match(lang, text)
    if not match:
        return None
    return match.get("code", ""), match.get("explanation", "")


def explain(text: str) -> Optional[Tuple[str, str]]:
    return lookup(text)


def add_example(language: str, description: str, code: str, explanation: str, tags: Optional[List[str]] = None) -> None:
    language = language.lower()
    if language not in LANGUAGES:
        return
    path = BASE_DIR / language / "examples.json"
    data = []
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = []
    entry = {
        "description": description,
        "keywords": _tokenize(description) + [language],
        "code": code,
        "explanation": explanation,
        "tags": tags or [],
        "text_to_speak": explanation,
    }
    data.append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

