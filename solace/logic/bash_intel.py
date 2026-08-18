from __future__ import annotations

import json
import re
import shlex
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from solace.configuration import ensure_storage_dirs, get_storage_path, load_config

KB_DIR = Path(__file__).resolve().parents[1] / "knowledge" / "programming" / "bash"
CONFIG = load_config()
ensure_storage_dirs(CONFIG)
BASH_MEMORY_FILE = get_storage_path(CONFIG, "training") / "bash_history.json"

BASH_LANGUAGE_HINTS = {
    "bash",
    "shell",
    "terminal",
    "cli",
    "sh",
    "shell script",
    "chmod",
    "grep",
    "sed",
    "awk",
    "find",
    "ls",
    "cd",
    "mkdir",
    "rm",
    "cp",
    "mv",
    "tar",
    "ps",
    "kill",
    "export",
    "source",
    "alias",
    "pipe",
    "redirect",
    "termux",
    "pkg",
    "storage",
    "scripts directory",
}


@dataclass
class BashLookupResult:
    command: str
    explanation: str
    placeholders: Dict[str, str]
    notes: List[str]
    safety: List[str]
    confidence: float
    source: str


def _load_json(name: str, default):
    path = KB_DIR / name
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError:
        return default


def _tokens(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9_+-]+", text.lower())


def is_bash_query(text: str) -> bool:
    lowered = text.lower()
    score = 0
    for hint in BASH_LANGUAGE_HINTS:
        if hint in lowered:
            score += 1
    token_set = set(_tokens(text))
    if {"python", "javascript", "html", "css"} & token_set and "bash" not in token_set and "shell" not in token_set:
        score -= 2
    return score >= 1


def classify_safety(command: str) -> List[str]:
    warnings: List[str] = []
    lowered = command.lower()
    for rule in _load_json("safety.json", []):
        pattern = str(rule.get("pattern", "")).lower()
        if not pattern:
            continue
        if pattern == ">":
            if ">" in lowered and ">>" not in lowered:
                warnings.append(
                    f"[{rule.get('severity', 'medium')}] {rule.get('message')} "
                    f"Safer: {rule.get('safer_alternative')}"
                )
        elif pattern in lowered:
            warnings.append(
                f"[{rule.get('severity', 'medium')}] {rule.get('message')} "
                f"Safer: {rule.get('safer_alternative')}"
            )
    normalized = f" {lowered.strip()} "
    if any(
        path in normalized
        for path in [" rm -rf /", " rm -rf ~", " /system", " /data/", " $home/storage", ' "$home/storage']
    ):
        warnings.append("[high] Command appears to target a critical path. Validate the target path before running.")
    return warnings


def _match_patterns(query: str) -> Optional[BashLookupResult]:
    entries = _load_json("patterns.json", [])
    if not entries:
        return None
    query_tokens = set(_tokens(query))
    best = None
    best_score = 0.0
    for item in entries:
        keywords = {str(k).lower() for k in item.get("keywords", [])}
        overlap = len(query_tokens & keywords)
        if not overlap:
            continue
        coverage = overlap / max(len(keywords), 1)
        score = overlap + coverage
        if score > best_score:
            best_score = score
            best = item
    if not best:
        return None
    confidence = min(1.0, best_score / 4.0)
    return BashLookupResult(
        command=best.get("command", ""),
        explanation=best.get("explanation", ""),
        placeholders=best.get("placeholders", {}),
        notes=[],
        safety=classify_safety(best.get("command", "")),
        confidence=confidence,
        source="patterns",
    )


def _match_scripts(query: str) -> Optional[BashLookupResult]:
    scripts = _load_json("scripts.json", [])
    query_tokens = set(_tokens(query))
    best = None
    best_score = 0
    for item in scripts:
        keys = set(_tokens(item.get("name", ""))) | {str(k).lower() for k in item.get("keywords", [])}
        score = len(query_tokens & keys)
        if score > best_score:
            best_score = score
            best = item
    if not best or best_score < 2:
        return None
    script = best.get("script", "")
    safety = classify_safety(script)
    if best.get("safety"):
        safety.append(best["safety"])
    return BashLookupResult(
        command=script,
        explanation=best.get("explanation", ""),
        placeholders=best.get("placeholders", {}),
        notes=["This is a reusable script template."],
        safety=safety,
        confidence=min(1.0, 0.4 + (best_score / 6.0)),
        source="scripts",
    )


def _load_memory() -> List[Dict]:
    if not BASH_MEMORY_FILE.exists():
        return []
    try:
        return json.loads(BASH_MEMORY_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def remember_mapping(
    phrase: str,
    command: str,
    explanation: str,
    *,
    tags: Optional[List[str]] = None,
    safety: str = "",
) -> None:
    data = _load_memory()
    normalized = phrase.strip().lower()
    entry = {
        "phrase": phrase.strip(),
        "phrase_normalized": normalized,
        "command": command.strip(),
        "explanation": explanation.strip(),
        "tags": tags or [],
        "safety": safety,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    deduped = [
        item
        for item in data
        if item.get("phrase_normalized") != normalized and item.get("command") != entry["command"]
    ]
    deduped.append(entry)
    BASH_MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    BASH_MEMORY_FILE.write_text(json.dumps(deduped, indent=2), encoding="utf-8")


def teach_text(text: str, *, tags: Optional[List[str]] = None) -> Dict[str, str]:
    cleaned = text.strip()
    command = cleaned
    explanation = "Taught by user"
    lower = cleaned.lower()
    if lower.startswith("use ") and " to " in lower:
        prefix, suffix = cleaned.split(" to ", 1)
        command = prefix[4:].strip()
        explanation = suffix.strip()
    remember_mapping(cleaned, command, explanation, tags=tags)
    return {"phrase": cleaned, "command": command, "explanation": explanation}


def _match_memory(query: str) -> Optional[BashLookupResult]:
    query_tokens = set(_tokens(query))
    best = None
    best_score = 0
    for item in _load_memory():
        source_tokens = set(_tokens(item.get("phrase", ""))) | set(_tokens(" ".join(item.get("tags", []))))
        score = len(query_tokens & source_tokens)
        if score > best_score:
            best_score = score
            best = item
    if not best or best_score < 2:
        return None
    safety = classify_safety(best.get("command", ""))
    if best.get("safety"):
        safety.append(best["safety"])
    return BashLookupResult(
        command=best.get("command", ""),
        explanation=best.get("explanation", ""),
        placeholders={},
        notes=["Retrieved from your saved Bash memory."],
        safety=safety,
        confidence=min(1.0, 0.5 + best_score / 8.0),
        source="memory",
    )


def lookup_bash(query: str) -> Optional[BashLookupResult]:
    memory_match = _match_memory(query)
    if memory_match:
        return memory_match
    script_match = _match_scripts(query)
    pattern_match = _match_patterns(query)
    if script_match and script_match.confidence > (pattern_match.confidence if pattern_match else 0):
        return script_match
    return pattern_match


def explain_command(command: str) -> List[str]:
    flags = _load_json("flags.json", {})
    commands = {item.get("command"): item for item in _load_json("commands.json", [])}
    parts: List[str] = []

    raw_segments = re.split(r"(\|\||&&|\||;)", command)
    segments = [seg.strip() for seg in raw_segments if seg.strip() and seg not in {"|", "||", "&&", ";"}]
    operators = [seg for seg in raw_segments if seg in {"|", "||", "&&", ";"}]
    for seg_idx, segment in enumerate(segments, 1):
        if len(segments) > 1:
            parts.append(f"Segment {seg_idx}: {segment}")
        try:
            tokens = shlex.split(segment)
        except ValueError:
            tokens = segment.split()
        if not tokens:
            continue
        cmd = tokens[0]
        if cmd in commands:
            parts.append(f"- {cmd}: {commands[cmd].get('description')}")
        else:
            parts.append(f"- {cmd}: unknown command token")
        for token in tokens[1:]:
            if token in flags:
                parts.append(f"  - {token}: {flags[token]}")
            elif token in {">", ">>", "<"}:
                parts.append(f"  - {token}: redirection operator")
            elif token.startswith("<") and token.endswith(">"):
                parts.append(f"  - {token}: placeholder value to replace")
            elif token.startswith("$"):
                parts.append(f"  - {token}: variable expansion")
            elif token.startswith("-"):
                parts.append(f"  - {token}: unknown flag")
    if "|" in command:
        parts.append("- |: pipe operator sends output from left command into right command input")
    if "&&" in operators:
        parts.append("- &&: run the command on the right only if the command on the left succeeds")
    if "||" in operators:
        parts.append("- ||: run the command on the right only if the command on the left fails")
    if ";" in operators:
        parts.append("- ;: command separator runs the next command regardless of the previous exit status")
    if ">>" in command:
        parts.append("- >>: append redirect")
    elif ">" in command:
        parts.append("- >: overwrite redirect")
    return parts


def explain_topic(query: str) -> Optional[str]:
    text = query.lower()
    best = None
    best_score = 0
    for topic in _load_json("topics.json", []):
        keys = {topic.get("topic", "").lower()} | {str(a).lower() for a in topic.get("aliases", [])}
        score = sum(1 for key in keys if key and key in text)
        if score > best_score:
            best_score = score
            best = topic
    if not best:
        return None
    lines = [best.get("summary", "")]
    examples = best.get("examples", [])
    if examples:
        lines.append("Examples: " + " | ".join(examples[:2]))
    return "\n".join(lines)


def debug_bash_error(message: str) -> Optional[str]:
    tokens = set(_tokens(message))
    best = None
    best_score = 0
    for err in _load_json("errors.json", []):
        required = [str(token).lower() for token in err.get("requires_any", [])]
        if required and not any(token in message.lower() for token in required):
            continue
        phrases = [err.get("error_message", "")] + list(err.get("patterns", []))
        score = 0
        for phrase in phrases:
            p_tokens = set(_tokens(phrase))
            score = max(score, len(tokens & p_tokens))
            if phrase and phrase.lower() in message.lower():
                score += 3
        if score:
            score += int(err.get("priority", 0))
        if score > best_score:
            best_score = score
            best = err
    if not best or best_score < 2:
        return None
    return f"Cause: {best.get('cause')}\nFix: {best.get('fix')}"
