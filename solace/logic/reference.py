"""Lookup syntax rules and function references for supported languages."""

from pathlib import Path
import json
import re
from typing import Optional, Dict

BASE_DIR = Path(__file__).resolve().parents[1] / "knowledge" / "programming"
LANGUAGES = ["python"]  # extendable
DEFAULT_LANGUAGE = "python"


def _tokenize(text: str):
    return re.findall(r"\w+", text.lower())


def _load_functions(language: str):
    path = BASE_DIR / language / "functions.json"
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


def find_function(language: str, name: str) -> Optional[Dict]:
    funcs = _load_functions(language)
    name_tokens = set(_tokenize(name))
    best = None
    best_score = 0
    for fn in funcs:
        fn_tokens = set(_tokenize(fn.get("name", "")))
        score = len(name_tokens & fn_tokens)
        if score > best_score:
            best_score = score
            best = fn
    return best


def lookup(text: str) -> Optional[str]:
    lang = detect_language(text)
    name = text
    if lang in text.lower():
        name = text.lower().replace(lang, "").strip()
    fn = find_function(lang, name)
    if not fn:
        return None
    args = fn.get("arguments", "")
    desc = fn.get("description", "")
    return f"{fn['name']}({args})\n{desc}"
