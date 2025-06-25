from pathlib import Path
from datetime import datetime
import json

from knowledge_graph import KnowledgeGraph
from entity_recognizer import extract_entities
from context_engine import ContextEngine
from response_engine import ResponseEngine


MOOD_KEYWORDS = {
    "happy": ["happy", "joy", "glad", "excited"],
    "sad": ["sad", "unhappy", "down"],
    "stressed": ["stress", "stressed", "anxious"],
}


def detect_mood(text: str) -> str:
    lowered = text.lower()
    for mood, words in MOOD_KEYWORDS.items():
        if any(w in lowered for w in words):
            return mood
    return "neutral"


class Solace:
    """Core engine tying all modules together."""

    def __init__(self, storage_dir: str | Path = "storage") -> None:
        self.storage = Path(storage_dir)
        self.graph = KnowledgeGraph(self.storage / "knowledge_graph.graphml")
        self.context = ContextEngine()
        self.responder = ResponseEngine()
        self.log_path = self.storage / "conversation_log.jsonl"

    def _log(self, user: str, response: str, mood: str) -> None:
        entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "user": user,
            "response": response,
            "mood": mood,
        }
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def chat(self, text: str) -> str:
        entities = extract_entities(text)
        for name in entities.get("names", []):
            self.graph.add_relation("user", name, "mentioned")
        for loc in entities.get("locations", []):
            self.graph.add_relation("user", loc, "location")
        for date in entities.get("dates", []):
            self.graph.add_relation("user", date, "date")
        self.graph.save_graph()

        self.context.add_entry(text)
        ctx = self.context.get_recent()
        mood = detect_mood(text)
        response = self.responder.generate(entities, ctx, style="neutral")
        self._log(text, response, mood)
        return response

