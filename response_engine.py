from typing import Dict, List


TEMPLATES = {
    "neutral": [
        "Thank you for sharing.",
        "I appreciate you telling me that.",
    ],
    "emotional": [
        "That sounds intense. I'm here for you.",
        "It seems like that affected you deeply.",
    ],
    "reflective": [
        "How do you feel about that now?",
        "What do you think led up to it?",
    ],
}


class ResponseEngine:
    def __init__(self) -> None:
        self.index: Dict[str, int] = {k: 0 for k in TEMPLATES}

    def _next_template(self, style: str) -> str:
        templates = TEMPLATES.get(style, TEMPLATES["neutral"])
        idx = self.index.get(style, 0)
        template = templates[idx % len(templates)]
        self.index[style] = idx + 1
        return template

    def generate(self, entities: Dict[str, List[str]], context: List[Dict[str, str]], style: str = "neutral") -> str:
        base = self._next_template(style)
        notes: List[str] = []
        if entities.get("names"):
            notes.append("mention of " + ", ".join(entities["names"]))
        if entities.get("locations"):
            notes.append("reference to " + ", ".join(entities["locations"]))
        if entities.get("dates"):
            notes.append("dates " + ", ".join(entities["dates"]))
        if notes:
            base += " (" + "; ".join(notes) + ")"
        return base

