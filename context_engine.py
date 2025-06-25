from collections import deque
from datetime import datetime
from typing import Deque, Dict, List


class ContextEngine:
    """Maintain a sliding window of recent interactions."""

    def __init__(self, window_size: int = 20) -> None:
        self.window_size = window_size
        self.history: Deque[Dict[str, str]] = deque(maxlen=window_size)

    def add_entry(self, text: str) -> None:
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "text": text,
        }
        self.history.append(entry)

    def get_recent(self, n: int | None = None) -> List[Dict[str, str]]:
        if n is None or n > len(self.history):
            n = len(self.history)
        return list(self.history)[-n:]

    def summarize(self, n: int | None = None) -> str:
        entries = self.get_recent(n)
        return " ".join(item["text"] for item in entries)

