"""Local, memory-grounded responses for Solace's conversational CLI.

This module deliberately keeps orchestration separate from presentation.  It
never executes suggested code or sends journal text to a network service.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

from journal import JournalEntry
from solace.logic import bash_intel, python_intel
from solace.logic.converse import offline_reply
from solace.memory import search_entries


@dataclass(frozen=True)
class CompanionResponse:
    """A response plus the journal entries used to ground it."""

    text: str
    memories: tuple[JournalEntry, ...] = ()
    kind: str = "conversation"


def _is_python_query(prompt: str) -> bool:
    tokens = set(re.findall(r"[a-z0-9_]+", prompt.lower()))
    python_markers = {"python", "py", "pip", "pytest", "venv", "pathlib", "dataclass"}
    return bool(tokens & python_markers)


def _relevant_memories(prompt: str, entries: Sequence[JournalEntry], *, limit: int = 3) -> tuple[JournalEntry, ...]:
    """Return useful plaintext memories, excluding weak fuzzy matches."""

    searchable = [entry for entry in entries if not entry.encrypted and entry.content.strip()]
    hits = search_entries(prompt, searchable, limit=limit)
    return tuple(hit.entry for hit in hits if hit.score >= 0.28 or hit.matched_date)


def _memory_context(memories: Sequence[JournalEntry]) -> str:
    if not memories:
        return ""
    lines = ["Relevant memories:"]
    for memory in memories:
        preview = re.sub(r"\s+", " ", memory.content).strip()
        if len(preview) > 120:
            preview = preview[:117].rstrip() + "…"
        lines.append(f"- {memory.date}: {preview}")
    return "\n".join(lines)


def respond(prompt: str, entries: Sequence[JournalEntry], *, name: str = "Friend") -> CompanionResponse:
    """Answer *prompt* using local code knowledge and relevant diary memory.

    Programming questions are routed to deterministic, inspectable knowledge
    bases.  Other conversation uses the offline responder and adds dated recall
    only when a sufficiently relevant journal entry exists.
    """

    prompt = prompt.strip()
    memories = _relevant_memories(prompt, entries)
    context = _memory_context(memories)

    if bash_intel.is_bash_query(prompt):
        bash_result = bash_intel.lookup_bash(prompt)
        if bash_result:
            sections = [bash_result.command, bash_result.explanation]
            if bash_result.safety:
                sections.append("Safety:\n" + "\n".join(f"- {warning}" for warning in bash_result.safety))
            if context:
                sections.append(context)
            return CompanionResponse("\n\n".join(sections), memories, "bash")

    if _is_python_query(prompt):
        python_result = python_intel.lookup_python(prompt)
        if python_result:
            sections = [python_result.code, python_result.explanation]
            if context:
                sections.append(context)
            return CompanionResponse("\n\n".join(sections), memories, "python")

    reply = offline_reply(prompt, name=name)
    if context:
        reply = f"{reply}\n\n{context}\nDoes that still reflect where you are now?"
    return CompanionResponse(reply, memories)


__all__ = ["CompanionResponse", "respond"]
