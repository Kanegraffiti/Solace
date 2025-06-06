import json
import re
from pathlib import Path
from typing import Optional, Dict

BASE_DIR = Path(__file__).resolve().parents[1] / "knowledge" / "programming"
LANGUAGES = ["python", "bash", "html", "javascript", "css"]
DEFAULT_LANGUAGE = "python"


def _tokenize(text: str):
    return re.findall(r"\w+", text.lower())


def _load_errors(language: str):
    path = BASE_DIR / language / "errors.json"
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


def find_best_error(language: str, message: str) -> Optional[Dict]:
    errors = _load_errors(language)
    tokens = set(_tokenize(message))
    best = None
    best_score = 0
    for err in errors:
        msg_tokens = set(_tokenize(err.get("error_message", "")))
        score = len(tokens & msg_tokens)
        if score > best_score:
            best_score = score
            best = err
    return best


def lookup(message: str) -> Optional[str]:
    lang = detect_language(message)
    err = find_best_error(lang, message)
    if not err:
        return None
    return err.get("fix")

