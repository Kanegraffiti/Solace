"""Deterministic offline Python help that never executes user-provided code."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PythonAnswer:
    code: str
    explanation: str
    confidence: float


_RECIPES = (
    ({"hello", "print", "output"}, 'print("Hello, world!")', "print writes a value to standard output."),
    (
        {"read", "file", "text"},
        'from pathlib import Path\n\ntext = Path("input.txt").read_text(encoding="utf-8")\nprint(text)',
        "pathlib provides a concise, cross-platform way to read a UTF-8 text file.",
    ),
    (
        {"write", "file", "text"},
        'from pathlib import Path\n\nPath("output.txt").write_text("Hello\\n", encoding="utf-8")',
        "write_text creates or replaces a text file.",
    ),
    (
        {"json", "read", "load"},
        'import json\nfrom pathlib import Path\n\ndata = json.loads(Path("data.json").read_text(encoding="utf-8"))\nprint(data)',
        "The standard-library json module converts JSON text into Python values.",
    ),
    (
        {"json", "write", "save"},
        'import json\nfrom pathlib import Path\n\ndata = {"answer": 42}\nPath("data.json").write_text(json.dumps(data, indent=2), encoding="utf-8")',
        "json.dumps serializes Python values; indent makes the file readable.",
    ),
    (
        {"list", "comprehension", "squares"},
        "squares = [number ** 2 for number in range(10)]",
        "A list comprehension transforms every value produced by an iterable.",
    ),
    (
        {"function", "define", "def"},
        'def greet(name: str) -> str:\n    """Return a friendly greeting."""\n    return f"Hello, {name}!"',
        "Use def to declare a function; type hints and a docstring document its contract.",
    ),
    (
        {"class", "dataclass", "object"},
        'from dataclasses import dataclass\n\n@dataclass\nclass Person:\n    name: str\n    age: int\n\nperson = Person("Ada", 36)',
        "A dataclass generates common methods while keeping attributes explicit.",
    ),
    (
        {"arguments", "cli", "argparse"},
        'import argparse\n\nparser = argparse.ArgumentParser()\nparser.add_argument("name")\nargs = parser.parse_args()\nprint(f"Hello, {args.name}!")',
        "argparse is the standard-library command-line argument parser.",
    ),
    (
        {"exception", "error", "handle"},
        'try:\n    value = int(user_input)\nexcept ValueError:\n    print("Please enter a whole number.")',
        "Catch the narrow exception you expect instead of hiding unrelated failures.",
    ),
)


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_]+", text.lower()))


def lookup_python(query: str) -> Optional[PythonAnswer]:
    """Return the best built-in recipe for *query*, or ``None`` when uncertain."""
    query_tokens = _tokens(query)
    matches = []
    for keywords, code, explanation in _RECIPES:
        score = len(query_tokens & keywords)
        if score:
            matches.append((score, len(keywords), code, explanation))
    if not matches:
        return None
    score, keyword_count, code, explanation = max(matches, key=lambda item: item[0])
    return PythonAnswer(code, explanation, min(1.0, 0.35 + score / keyword_count))
