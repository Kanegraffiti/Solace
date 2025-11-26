"""Semantic utilities for Solace.

This module provides hybrid search that blends fuzzy matching with
lightweight embeddings. Embeddings are cached under the configured cache
path (``~/.solace/cache/semantic`` by default) and fall back to a simple
hash-based representation when ML dependencies are unavailable.

It also offers recap helpers that cluster recent entries into weekly or
monthly summaries using local models when available.
"""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from solace.configuration import get_storage_path, load_config
from solace.memory import MemoryHit

try:  # Optional heavy dependency
    from sentence_transformers import SentenceTransformer  # type: ignore
except Exception:  # noqa: BLE001
    SentenceTransformer = None


CONFIG = load_config()
CACHE_ROOT = get_storage_path(CONFIG, "cache") / "semantic"
DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@dataclass
class SearchHit(MemoryHit):
    """Extended search hit combining fuzzy and semantic sources."""

    snippet: str = ""
    source: str = "fuzzy"


class SemanticEngine:
    """Build and search a cached semantic index over journal entries."""

    def __init__(self, cache_dir: Path = CACHE_ROOT, model_name: str = DEFAULT_MODEL_NAME) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.cache_dir / "embeddings.json"
        self.model_name = model_name
        self._model = None
        self._index: Dict[str, Dict[str, object]] = {}

    @property
    def model_loaded(self) -> bool:
        return self._model is not None

    def _load_model(self) -> None:
        if self._model or SentenceTransformer is None:
            return
        try:
            self._model = SentenceTransformer(self.model_name)
        except Exception:  # noqa: BLE001
            self._model = None

    def _hash_embedding(self, text: str, dim: int = 48) -> List[float]:
        buckets = [0.0 for _ in range(dim)]
        for token in re.findall(r"\w+", text.lower()):
            idx = hash(token) % dim
            buckets[idx] += 1.0
        length = math.sqrt(sum(value * value for value in buckets)) or 1.0
        return [value / length for value in buckets]

    def _embed(self, texts: Sequence[str]) -> List[List[float]]:
        self._load_model()
        if self._model is not None:
            try:
                return self._model.encode(list(texts), normalize_embeddings=True).tolist()
            except Exception:  # noqa: BLE001
                pass
        return [self._hash_embedding(text) for text in texts]

    def _load_index(self) -> Dict[str, Dict[str, object]]:
        if self._index:
            return self._index
        if self.index_file.exists():
            try:
                data = json.loads(self.index_file.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self._index = data
            except json.JSONDecodeError:
                self._index = {}
        return self._index

    def _save_index(self) -> None:
        self.index_file.write_text(json.dumps(self._index, indent=2), encoding="utf-8")

    def _ensure_embeddings(self, entries: Sequence[object]) -> Dict[str, List[float]]:
        stored_index = self._load_index().get("entries", {}) if isinstance(self._index, dict) else {}
        updated_index = dict(stored_index) if isinstance(stored_index, dict) else {}

        missing_payloads: List[Tuple[str, str, str]] = []
        for entry in entries:
            identifier = getattr(entry, "identifier", None)
            timestamp = getattr(entry, "timestamp", None)
            if not identifier:
                continue
            cached = updated_index.get(identifier) if isinstance(updated_index, dict) else None
            if (
                cached
                and isinstance(cached, dict)
                and cached.get("timestamp") == timestamp
                and isinstance(cached.get("embedding"), list)
            ):
                continue
            missing_payloads.append((identifier, timestamp or datetime.now().isoformat(), getattr(entry, "content", "")))

        if missing_payloads:
            embeddings = self._embed([payload[2] for payload in missing_payloads])
            for (identifier, timestamp, _), vector in zip(missing_payloads, embeddings):
                updated_index[identifier] = {"timestamp": timestamp, "embedding": vector}

        keep_ids = {getattr(entry, "identifier", "") for entry in entries}
        updated_index = {key: value for key, value in updated_index.items() if key in keep_ids}

        self._index["entries"] = updated_index
        self._index["model"] = self.model_name if self._model else "hash"
        self._save_index()
        return {key: value.get("embedding", []) for key, value in updated_index.items() if isinstance(value, dict)}

    def search(self, query: str, entries: List[object], *, limit: int = 5) -> List[SearchHit]:
        if not query.strip() or not entries:
            return []
        embeddings = self._ensure_embeddings(entries)
        query_vec = self._embed([query])[0]
        hits: List[SearchHit] = []
        for entry in entries:
            vector = embeddings.get(getattr(entry, "identifier", ""))
            if not vector:
                continue
            similarity = _cosine_similarity(query_vec, vector)
            if similarity <= 0:
                continue
            hits.append(
                SearchHit(
                    entry=entry,
                    score=similarity,
                    matched_date=False,
                    snippet=build_snippet(entry.content, query),
                    source="semantic" if self._model else "semantic-fallback",
                )
            )
        hits.sort(key=lambda hit: hit.score, reverse=True)
        return hits[:limit]


def _cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a)) or 1.0
    norm_b = math.sqrt(sum(b * b for b in vec_b)) or 1.0
    return dot / (norm_a * norm_b)


def build_snippet(text: str, query: str, *, max_length: int = 120) -> str:
    clean = text.replace("\n", " ").strip()
    lowered = clean.lower()
    q = query.lower().strip()
    if q and q in lowered:
        idx = lowered.index(q)
        start = max(0, idx - 40)
        end = min(len(clean), idx + len(q) + 60)
        snippet = clean[start:end]
    else:
        snippet = clean[:max_length]
    return snippet + ("…" if len(snippet) == max_length and len(clean) > max_length else "")


def hybrid_search(query: str, entries: List[object], *, limit: int = 5) -> List[SearchHit]:
    """Combine fuzzy and semantic search for richer recall."""

    from solace.memory import search_entries  # local import to avoid cycles

    fuzzy_hits = [
        SearchHit(entry=hit.entry, score=hit.score, matched_date=hit.matched_date, snippet=build_snippet(hit.entry.content, query), source="fuzzy")
        for hit in search_entries(query, entries, limit=limit * 2)
    ]

    engine = SemanticEngine()
    semantic_hits = engine.search(query, entries, limit=limit * 2)

    combined: Dict[str, SearchHit] = {}
    for hit in fuzzy_hits + semantic_hits:
        key = getattr(hit.entry, "identifier", None) or f"{hit.entry.date}:{hit.entry.time}:{hit.entry.entry_type}"
        existing = combined.get(key)
        weight = 0.6 if hit.source == "fuzzy" else 0.65
        if existing:
            combined[key] = SearchHit(
                entry=hit.entry,
                score=max(existing.score, hit.score) + weight * hit.score,
                matched_date=existing.matched_date or hit.matched_date,
                snippet=hit.snippet or existing.snippet,
                source="hybrid",
            )
        else:
            combined[key] = SearchHit(
                entry=hit.entry,
                score=weight * hit.score,
                matched_date=hit.matched_date,
                snippet=hit.snippet,
                source=hit.source,
            )

    results = sorted(combined.values(), key=lambda hit: hit.score, reverse=True)
    return results[:limit]


def _sent_tokenise(text: str) -> List[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [sentence for sentence in sentences if sentence]


def _fallback_summarise(texts: Sequence[str], *, max_sentences: int = 4) -> str:
    sentences: List[str] = []
    for text in texts:
        sentences.extend(_sent_tokenise(text))
    if not sentences:
        return "No entries available to summarise."
    scored = sorted({sentence: len(sentence) for sentence in sentences}.items(), key=lambda item: item[1], reverse=True)
    chosen = [sentence for sentence, _ in scored[:max_sentences]]
    return " ".join(chosen)


def _transformer_summarise(text: str) -> Optional[str]:
    if os.getenv("SOLACE_DISABLE_TRANSFORMERS"):
        return None
    try:
        from transformers import pipeline  # type: ignore
    except Exception:  # noqa: BLE001
        return None
    try:
        summariser = pipeline("summarization")
        output = summariser(text, max_length=180, min_length=60, do_sample=False)
        if isinstance(output, list) and output:
            return output[0].get("summary_text")
    except Exception:  # noqa: BLE001
        return None
    return None


def summarise_cluster(texts: Sequence[str]) -> str:
    joined = "\n".join(texts)
    if not joined.strip():
        return "No entries available to summarise."
    summary = _transformer_summarise(joined)
    if summary:
        return summary
    return _fallback_summarise(texts)


def _group_entries(entries: Iterable[object], *, period: str) -> Dict[str, List[object]]:
    grouped: Dict[str, List[object]] = {}
    for entry in entries:
        try:
            stamp = datetime.fromisoformat(getattr(entry, "timestamp"))
        except Exception:  # noqa: BLE001
            continue
        if period == "week":
            iso_year, iso_week, _ = stamp.isocalendar()
            key = f"{iso_year}-W{iso_week:02d}"
        else:
            key = f"{stamp.year}-{stamp.month:02d}"
        grouped.setdefault(key, []).append(entry)
    return grouped


def recent_recaps(entries: Iterable[object], *, period: str = "week", lookback_days: int = 90) -> List[Tuple[str, str, int]]:
    cutoff = datetime.now() - timedelta(days=lookback_days)
    recent = [entry for entry in entries if _parse_timestamp(entry) >= cutoff]
    grouped = _group_entries(recent, period=period)
    summaries: List[Tuple[str, str, int]] = []
    for key, group_entries in sorted(grouped.items(), reverse=True):
        texts = [getattr(item, "content", "") for item in group_entries]
        summary = summarise_cluster(texts)
        summaries.append((key, summary, len(group_entries)))
    return summaries


def _parse_timestamp(entry: object) -> datetime:
    try:
        return datetime.fromisoformat(getattr(entry, "timestamp"))
    except Exception:  # noqa: BLE001
        return datetime.min


__all__ = [
    "SearchHit",
    "SemanticEngine",
    "hybrid_search",
    "build_snippet",
    "recent_recaps",
    "summarise_cluster",
]
