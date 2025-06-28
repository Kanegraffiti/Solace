from __future__ import annotations

from typing import List


def extract_code_blocks(text: str) -> List[str]:
    """Return code blocks detected in ``text``.

    Blocks wrapped in triple backticks are extracted. If no such fences are
    found, groups of lines with leading spaces are used as a fallback. If still
    nothing looks like code the full text is returned as a single block.
    """
    blocks: List[str] = []
    inside = False
    current: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            if inside:
                if current:
                    blocks.append("\n".join(current).rstrip())
                current = []
                inside = False
            else:
                inside = True
            continue
        if inside:
            current.append(line)
    if inside and current:
        blocks.append("\n".join(current).rstrip())

    if not blocks:
        group: List[str] = []
        for line in text.splitlines():
            if line.startswith("    "):
                group.append(line[4:])
            elif group:
                blocks.append("\n".join(group).rstrip())
                group = []
        if group:
            blocks.append("\n".join(group).rstrip())

    if not blocks and text.strip():
        blocks = [text.strip()]
    return blocks
