"""Deterministic intent routing for Solace's assistant entry point.

Routing is deliberately inspectable and side-effect free.  It chooses an
existing Solace command or reports that a local model would be needed; the
caller remains responsible for confirmation and execution policy.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AssistantRoute:
    kind: str
    command: Optional[str]
    arguments: str
    reason: str


def _contains(text: str, words: set[str]) -> bool:
    return bool(set(re.findall(r"[a-z0-9]+", text.casefold())) & words)


def route_request(request: str) -> AssistantRoute:
    """Select a deterministic Solace skill before considering a local model."""

    clean = request.strip()
    if not clean:
        raise ValueError("Tell Solace what you want help with.")
    lower = clean.casefold()

    grammar = re.match(
        r"^(?:please\s+)?(?:fix|correct|edit|check|improve)\s+(?:the\s+)?(?:english|grammar)\s*(?::|in)?\s*(.*)$",
        clean,
        re.IGNORECASE,
    )
    if grammar and grammar.group(1).strip():
        return AssistantRoute("deterministic", "grammar", grammar.group(1).strip(), "English editing")

    if _contains(lower, {"file", "folder", "directory"}) and _contains(
        lower, {"find", "copy", "move", "rename", "delete", "trash", "restore", "list"}
    ):
        return AssistantRoute("deterministic", "file", clean, "safe file management")

    if _contains(lower, {"project", "website", "archive", "zip"}) and _contains(
        lower, {"inspect", "find", "extract", "run", "launch", "start"}
    ):
        return AssistantRoute("deterministic", "do", clean, "guarded project workflow")

    if _contains(lower, {"excel", "spreadsheet", "workbook", "formula", "pivot"}):
        return AssistantRoute("deterministic", "excel", clean, "offline spreadsheet tools")

    if lower.startswith(("check bash ", "validate bash ")):
        command = clean.split(" ", 2)[2]
        return AssistantRoute("deterministic", "bash", f"check {command}", "Bash syntax checking")
    if _contains(lower, {"bash", "shell", "termux"}):
        return AssistantRoute("deterministic", "ask", f"bash {clean}", "offline Bash knowledge")

    if _contains(lower, {"journal", "diary", "memory", "memories"}) and _contains(
        lower, {"find", "search", "remember", "recall"}
    ):
        return AssistantRoute("deterministic", "search", clean, "local memory search")

    return AssistantRoute("local_model", None, clean, "no confident deterministic skill matched")


__all__ = ["AssistantRoute", "route_request"]
