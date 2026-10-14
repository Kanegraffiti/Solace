"""Small, offline English grammar editor for the terminal interface."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Match, Optional, Pattern, Tuple, Union

MAX_TEXT_BYTES = 1_000_000
Replacement = Union[str, Callable[[Match[str]], str]]


@dataclass(frozen=True)
class GrammarEdit:
    before: str
    after: str
    reason: str


@dataclass(frozen=True)
class GrammarResult:
    original: str
    corrected: str
    edits: List[GrammarEdit]


@dataclass(frozen=True)
class GrammarFileResult:
    source: Path
    output: Path
    result: GrammarResult


def _match_case(source: str, replacement: str) -> str:
    if source.isupper():
        return replacement.upper()
    if source[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def _agreement(match: Match[str]) -> str:
    subject = match.group(1)
    verb = match.group(2).casefold()
    if subject.casefold() == "i" and verb == "is":
        corrected = "am"
    elif subject.casefold() in {"i", "you", "we", "they"}:
        corrected = {"is": "are", "has": "have", "doesn't": "don't"}[verb]
    else:
        corrected = {"are": "is", "have": "has", "don't": "doesn't"}[verb]
    return f"{_match_case(subject, subject.casefold())} {corrected}"


IRREGULAR_AFTER_DID = {
    "ate": "eat",
    "bought": "buy",
    "brought": "bring",
    "came": "come",
    "found": "find",
    "gave": "give",
    "knew": "know",
    "made": "make",
    "saw": "see",
    "spoke": "speak",
    "thought": "think",
    "took": "take",
    "went": "go",
    "wrote": "write",
}

MISSING_APOSTROPHES = {
    "arent": "aren't",
    "cant": "can't",
    "couldnt": "couldn't",
    "didnt": "didn't",
    "doesnt": "doesn't",
    "dont": "don't",
    "hasnt": "hasn't",
    "havent": "haven't",
    "isnt": "isn't",
    "shouldnt": "shouldn't",
    "wasnt": "wasn't",
    "werent": "weren't",
    "wont": "won't",
    "wouldnt": "wouldn't",
}


def _did_base_form(match: Match[str]) -> str:
    helper = match.group(1)
    verb = match.group(2)
    return f"{helper} {_match_case(verb, IRREGULAR_AFTER_DID[verb.casefold()])}"


def _capitalise_sentence(match: Match[str]) -> str:
    return match.group(1) + match.group(2).upper()


def _restore_apostrophe(match: Match[str]) -> str:
    return _match_case(match.group(0), MISSING_APOSTROPHES[match.group(0).casefold()])


def _base_after_does(match: Match[str]) -> str:
    return f"{match.group(1)} have"


def _remove_modifier(match: Match[str]) -> str:
    return _match_case(match.group(0), match.group(1).casefold())


RULES: Tuple[Tuple[Pattern[str], Replacement, str], ...] = (
    (re.compile(r"[ \t]+([,.;:!?])"), r"\1", "removed spacing before punctuation"),
    (re.compile(r"([,;:!?])(?=[A-Za-z])"), r"\1 ", "added spacing after punctuation"),
    (re.compile(r" {2,}"), " ", "removed repeated spacing"),
    (re.compile(r"\bi\b"), "I", "capitalised the pronoun “I”"),
    (
        re.compile(r"\b(" + "|".join(MISSING_APOSTROPHES) + r")\b", re.IGNORECASE),
        _restore_apostrophe,
        "restored a missing apostrophe",
    ),
    (
        re.compile(r"\b(I|you|we|they)\s+(is|has|doesn't)\b", re.IGNORECASE),
        _agreement,
        "corrected subject–verb agreement",
    ),
    (re.compile(r"\b(he|she|it)\s+(are|have|don't)\b", re.IGNORECASE), _agreement, "corrected subject–verb agreement"),
    (
        re.compile(r"\b(doesn't|does not)\s+has\b", re.IGNORECASE),
        _base_after_does,
        "used the base verb after “does”",
    ),
    (
        re.compile(
            r"\b(didn't|did not)\s+"
            r"(ate|bought|brought|came|found|gave|knew|made|saw|spoke|thought|took|went|wrote)\b",
            re.IGNORECASE,
        ),
        _did_base_form,
        "used the base verb after “did”",
    ),
    (
        re.compile(r"\bmore\s+(better|easier)\b", re.IGNORECASE),
        _remove_modifier,
        "removed a double comparative",
    ),
    (
        re.compile(r"\bmost\s+(easiest|best)\b", re.IGNORECASE),
        _remove_modifier,
        "removed a double superlative",
    ),
    (
        re.compile(r"(^|(?<=[.!?])\s+|\n+)([a-z])"),
        _capitalise_sentence,
        "capitalised the start of a sentence",
    ),
)


def edit_english(text: str) -> GrammarResult:
    """Apply conservative, explainable grammar corrections to English prose."""

    if not text.strip():
        raise ValueError("Provide English text to edit.")
    if len(text.encode("utf-8")) > MAX_TEXT_BYTES:
        raise ValueError(f"Text is larger than the {MAX_TEXT_BYTES:,}-byte editing limit.")

    corrected = text
    edits: List[GrammarEdit] = []
    for pattern, replacement, reason in RULES:
        examples: List[Tuple[str, str]] = []

        def substitute(
            match: Match[str],
            current_replacement: Replacement = replacement,
            current_examples: List[Tuple[str, str]] = examples,
        ) -> str:
            after = (
                current_replacement(match)
                if callable(current_replacement)
                else match.expand(current_replacement)
            )
            if after != match.group(0):
                current_examples.append((match.group(0), after))
            return after

        corrected = pattern.sub(substitute, corrected)
        for before, after in examples:
            edits.append(GrammarEdit(before=before, after=after, reason=reason))

    return GrammarResult(original=text, corrected=corrected, edits=edits)


def _next_output_path(source: Path) -> Path:
    candidate = source.with_name(f"{source.stem}.grammar-edited{source.suffix}")
    number = 2
    while candidate.exists():
        candidate = source.with_name(f"{source.stem}.grammar-edited-{number}{source.suffix}")
        number += 1
    return candidate


def edit_english_file(path: Path, *, output: Optional[Path] = None) -> GrammarFileResult:
    """Edit a bounded UTF-8 text file into a new file, never overwriting the source."""

    source = path.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Text file not found: {source}")
    if source.suffix.casefold() not in {".txt", ".md"}:
        raise ValueError("Grammar file editing supports .txt and .md files.")
    if source.stat().st_size > MAX_TEXT_BYTES:
        raise ValueError(f"Text file is larger than the {MAX_TEXT_BYTES:,}-byte editing limit.")
    try:
        text = source.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Text file must use UTF-8 encoding.") from exc

    result = edit_english(text)
    destination = output.expanduser().resolve() if output else _next_output_path(source)
    if destination == source or destination.exists():
        raise FileExistsError(f"Refusing to overwrite an existing file: {destination}")
    destination.write_text(result.corrected, encoding="utf-8")
    return GrammarFileResult(source=source, output=destination, result=result)


__all__ = [
    "GrammarEdit",
    "GrammarFileResult",
    "GrammarResult",
    "MAX_TEXT_BYTES",
    "edit_english",
    "edit_english_file",
]
