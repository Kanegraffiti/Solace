"""Deterministic, confirmation-friendly file management for Solace."""

from __future__ import annotations

import json
import os
import re
import shutil
import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

SKIP_DIR_NAMES = {
    ".cache",
    ".git",
    ".gradle",
    ".npm",
    ".solace",
    ".venv",
    "__pycache__",
    "node_modules",
}


@dataclass(frozen=True)
class FileIntent:
    action: str
    source: str = ""
    destination: str = ""
    query: str = ""
    limit: int = 20


class UnsafePathError(PermissionError):
    """Raised when a mutation would leave Solace's user-owned file roots."""


class FileManager:
    """Manage user files without executing shell commands.

    Mutations are restricted to the user's home directory and Termux shared
    storage roots. Deletes move content into Solace Trash instead of unlinking.
    """

    def __init__(
        self,
        home: Optional[Path] = None,
        search_roots: Optional[Sequence[Path]] = None,
        state_dir: Optional[Path] = None,
    ) -> None:
        self.home = (home or Path.home()).expanduser().resolve()
        self.state_dir = (state_dir or self.home / ".solace").expanduser()
        self.history_path = self.state_dir / "file-history.jsonl"
        self.trash_dir = self.state_dir / "trash"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.trash_dir.mkdir(parents=True, exist_ok=True)

        roots = list(search_roots or self._default_search_roots())
        self.search_roots = self._dedupe_roots(roots)
        self.allowed_roots = self._dedupe_roots([self.home] + self.search_roots)

    def _default_search_roots(self) -> List[Path]:
        roots = [self.home]
        storage = self.home / "storage"
        for name in ("shared", "downloads", "documents", "dcim", "pictures", "movies", "music"):
            candidate = storage / name
            if candidate.exists():
                try:
                    roots.append(candidate.resolve())
                except OSError:
                    continue
        return roots

    @staticmethod
    def _dedupe_roots(roots: Iterable[Path]) -> List[Path]:
        result: List[Path] = []
        seen = set()
        for root in roots:
            try:
                resolved = root.expanduser().resolve()
            except OSError:
                continue
            key = str(resolved)
            if key not in seen and resolved.exists():
                seen.add(key)
                result.append(resolved)
        return result

    @staticmethod
    def _under(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            return False

    def _assert_allowed(self, path: Path) -> Path:
        resolved = path.expanduser().resolve()
        if any(self._under(resolved, root) for root in self.allowed_roots):
            return resolved
        raise UnsafePathError("Solace will not modify paths outside your home/shared storage: {}".format(path))

    def expand_path(self, value: str, *, cwd: Optional[Path] = None) -> Path:
        raw = Path(value.strip()).expanduser()
        if raw.is_absolute():
            return raw
        current = (cwd or Path.cwd()).expanduser()
        current_candidate = current / raw
        if current_candidate.exists():
            return current_candidate
        return self.home / raw

    def find(self, query: str, limit: int = 20) -> List[Path]:
        """Find files/directories by case-insensitive filename fragment."""

        needle = query.strip().strip("\"'")
        if not needle:
            return []

        explicit = self.expand_path(needle)
        if explicit.exists():
            return [explicit.resolve()]

        folded = needle.casefold()
        matches: List[Path] = []
        seen = set()
        for root in self.search_roots:
            for current, dirs, files in os.walk(str(root), followlinks=False):
                dirs[:] = [name for name in dirs if name not in SKIP_DIR_NAMES]
                names = dirs + files
                for name in names:
                    if folded not in name.casefold():
                        continue
                    candidate = Path(current) / name
                    try:
                        resolved = candidate.resolve()
                    except OSError:
                        continue
                    key = str(resolved)
                    if key in seen:
                        continue
                    seen.add(key)
                    matches.append(resolved)
                    if len(matches) >= limit:
                        return matches
        return matches

    def largest(self, limit: int = 20) -> List[Path]:
        """Return the largest regular files visible in configured search roots."""

        sized: List[tuple[int, Path]] = []
        seen = set()
        for root in self.search_roots:
            for current, dirs, files in os.walk(str(root), followlinks=False):
                dirs[:] = [name for name in dirs if name not in SKIP_DIR_NAMES]
                for name in files:
                    path = Path(current) / name
                    try:
                        resolved = path.resolve()
                        key = str(resolved)
                        if key in seen or not resolved.is_file():
                            continue
                        seen.add(key)
                        sized.append((resolved.stat().st_size, resolved))
                    except OSError:
                        continue
        sized.sort(key=lambda item: item[0], reverse=True)
        return [path for _, path in sized[:limit]]

    def modified_today(self, limit: int = 50) -> List[Path]:
        today = datetime.now().date()
        rows: List[tuple[float, Path]] = []
        seen = set()
        for root in self.search_roots:
            for current, dirs, files in os.walk(str(root), followlinks=False):
                dirs[:] = [name for name in dirs if name not in SKIP_DIR_NAMES]
                for name in files:
                    path = Path(current) / name
                    try:
                        resolved = path.resolve()
                        key = str(resolved)
                        if key in seen:
                            continue
                        seen.add(key)
                        mtime = resolved.stat().st_mtime
                        if datetime.fromtimestamp(mtime).date() == today:
                            rows.append((mtime, resolved))
                    except OSError:
                        continue
        rows.sort(key=lambda item: item[0], reverse=True)
        return [path for _, path in rows[:limit]]

    def _event(self, action: str, **fields: object) -> Dict[str, object]:
        event: Dict[str, object] = {
            "id": uuid.uuid4().hex,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "action": action,
        }
        event.update(fields)
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        with self.history_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        return event

    def history(self, limit: int = 20) -> List[Dict[str, object]]:
        if not self.history_path.exists():
            return []
        events: List[Dict[str, object]] = []
        for line in self.history_path.read_text(encoding="utf-8").splitlines():
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                events.append(data)
        return events[-limit:]

    def _target_for_copy_or_move(self, source: Path, destination: Path) -> Path:
        if destination.exists() and destination.is_dir():
            return destination / source.name
        return destination

    def rename(self, source: Path, new_name_or_path: str) -> Path:
        src = self._assert_allowed(source)
        if not src.exists():
            raise FileNotFoundError(src)
        raw = Path(new_name_or_path.strip()).expanduser()
        if raw.is_absolute() or len(raw.parts) > 1:
            destination = raw if raw.is_absolute() else Path.cwd() / raw
        else:
            destination = src.parent / raw
        dst = self._assert_allowed(destination)
        if dst.exists():
            raise FileExistsError(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)
        self._event("rename", source=str(src), destination=str(dst))
        return dst

    def copy(self, source: Path, destination: str) -> Path:
        src = self._assert_allowed(source)
        if not src.exists():
            raise FileNotFoundError(src)
        raw_dst = self.expand_path(destination)
        dst = self._assert_allowed(self._target_for_copy_or_move(src, raw_dst))
        if dst.exists():
            raise FileExistsError(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
        self._event("copy", source=str(src), destination=str(dst))
        return dst

    def move(self, source: Path, destination: str) -> Path:
        src = self._assert_allowed(source)
        if not src.exists():
            raise FileNotFoundError(src)
        raw_dst = self.expand_path(destination)
        dst = self._assert_allowed(self._target_for_copy_or_move(src, raw_dst))
        if dst.exists():
            raise FileExistsError(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        result = Path(shutil.move(str(src), str(dst))).resolve()
        self._event("move", source=str(src), destination=str(result))
        return result

    def make_directory(self, destination: str) -> Path:
        dst = self._assert_allowed(self.expand_path(destination))
        if dst.exists():
            raise FileExistsError(dst)
        dst.mkdir(parents=True, exist_ok=False)
        self._event("mkdir", destination=str(dst))
        return dst

    def trash(self, source: Path) -> Path:
        src = self._assert_allowed(source)
        if not src.exists():
            raise FileNotFoundError(src)
        event_id = uuid.uuid4().hex
        bucket = self.trash_dir / event_id
        bucket.mkdir(parents=True, exist_ok=False)
        payload = bucket / src.name
        shutil.move(str(src), str(payload))
        self._event("trash", source=str(src), trash=str(payload), trash_id=event_id)
        return payload

    def trashed(self, query: str = "", limit: int = 20) -> List[Dict[str, object]]:
        """Return trash events that have not already been restored/undone."""

        events = self.history(limit=10000)
        restored_ids = {
            str(event.get("target_id"))
            for event in events
            if event.get("action") in {"restore", "undo"} and event.get("target_id")
        }
        folded = query.casefold().strip()
        result: List[Dict[str, object]] = []
        for event in reversed(events):
            if event.get("action") != "trash":
                continue
            event_id = str(event.get("id", ""))
            if event_id in restored_ids:
                continue
            source = str(event.get("source", ""))
            trash = Path(str(event.get("trash", "")))
            if not trash.exists():
                continue
            if folded and folded not in Path(source).name.casefold() and folded not in source.casefold():
                continue
            result.append(event)
            if len(result) >= limit:
                break
        return result

    def restore_event(self, event: Dict[str, object]) -> Path:
        source = self._assert_allowed(Path(str(event.get("source", ""))))
        trash = Path(str(event.get("trash", ""))).expanduser()
        if not trash.exists():
            raise FileNotFoundError(trash)
        if source.exists():
            raise FileExistsError(source)
        source.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(trash), str(source))
        self._event("restore", source=str(source), target_id=str(event.get("id", "")))
        return source

    def _undone_ids(self, events: Sequence[Dict[str, object]]) -> set[str]:
        return {
            str(event.get("target_id"))
            for event in events
            if event.get("action") == "undo" and event.get("target_id")
        }

    def undo_last(self) -> str:
        events = self.history(limit=10000)
        undone = self._undone_ids(events)
        candidate: Optional[Dict[str, object]] = None
        for event in reversed(events):
            event_id = str(event.get("id", ""))
            if event_id in undone:
                continue
            if event.get("action") in {"rename", "copy", "move", "mkdir", "trash"}:
                candidate = event
                break
        if candidate is None:
            raise LookupError("No undoable file operation found.")

        action = str(candidate.get("action"))
        event_id = str(candidate.get("id", ""))
        if action in {"rename", "move"}:
            source = self._assert_allowed(Path(str(candidate.get("source", ""))))
            destination = self._assert_allowed(Path(str(candidate.get("destination", ""))))
            if source.exists():
                raise FileExistsError("Cannot undo because original path already exists: {}".format(source))
            if not destination.exists():
                raise FileNotFoundError(destination)
            source.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(destination), str(source))
            message = "Restored {} to {}".format(destination, source)
        elif action == "copy":
            destination = self._assert_allowed(Path(str(candidate.get("destination", ""))))
            if not destination.exists():
                raise FileNotFoundError(destination)
            bucket = self.trash_dir / ("undo-" + uuid.uuid4().hex)
            bucket.mkdir(parents=True, exist_ok=False)
            payload = bucket / destination.name
            shutil.move(str(destination), str(payload))
            message = "Removed copied item safely to Solace Trash: {}".format(destination)
        elif action == "mkdir":
            destination = self._assert_allowed(Path(str(candidate.get("destination", ""))))
            if not destination.exists():
                raise FileNotFoundError(destination)
            destination.rmdir()
            message = "Removed empty directory {}".format(destination)
        else:  # trash
            source = self._assert_allowed(Path(str(candidate.get("source", ""))))
            trash = Path(str(candidate.get("trash", "")))
            if source.exists():
                raise FileExistsError("Cannot restore because original path already exists: {}".format(source))
            if not trash.exists():
                raise FileNotFoundError(trash)
            source.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(trash), str(source))
            message = "Restored {}".format(source)

        self._event("undo", target_id=event_id, original_action=action)
        return message


def _strip_conversational_prefix(text: str) -> str:
    """Remove harmless conversational lead-ins before parsing a file request."""

    value = text.strip()
    prefixes = [
        r"so\s+let(?:'|’)?s\s+",
        r"let(?:'|’)?s\s+",
        r"lets\s+",
        r"please\s+",
        r"can\s+you\s+",
        r"could\s+you\s+",
        r"would\s+you\s+",
    ]
    changed = True
    while changed:
        changed = False
        for prefix in prefixes:
            cleaned = re.sub(r"^" + prefix, "", value, count=1, flags=re.IGNORECASE)
            if cleaned != value:
                value = cleaned.strip()
                changed = True
                break
    return value


def parse_intent(text: str) -> Optional[FileIntent]:
    """Parse a small, auditable natural-language file command grammar."""

    value = _strip_conversational_prefix(text)
    lowered = value.lower()
    if not value:
        return None
    if lowered in {"history", "show history", "file history"}:
        return FileIntent("history")
    if lowered in {"undo", "undo last", "undo last action", "undo last file action"}:
        return FileIntent("undo")
    if lowered in {"trash", "show trash", "list trash"}:
        return FileIntent("list-trash")
    if "modified today" in lowered:
        return FileIntent("modified-today")

    largest = re.search(r"(?:show(?: me)?\s+)?(?:(\d+)\s+)?largest files", lowered)
    if largest:
        return FileIntent("largest", limit=int(largest.group(1) or 20))

    patterns = [
        ("rename", r"^(?:rename|change(?: the)? name of)\s+(.+?)\s+(?:to|as)\s+(.+)$"),
        ("copy", r"^(?:copy|duplicate)\s+(.+?)\s+to\s+(.+)$"),
        ("move", r"^move\s+(.+?)\s+to\s+(.+)$"),
    ]
    for action, pattern in patterns:
        match = re.match(pattern, value, flags=re.IGNORECASE)
        if match:
            return FileIntent(action, source=match.group(1).strip(), destination=match.group(2).strip())

    match = re.match(r"^(?:delete|remove|trash)\s+(.+)$", value, flags=re.IGNORECASE)
    if match:
        return FileIntent("trash", source=match.group(1).strip())

    match = re.match(r"^restore\s+(.+)$", value, flags=re.IGNORECASE)
    if match:
        return FileIntent("restore", query=match.group(1).strip())

    match = re.match(
        r"^(?:make|create)\s+(?:a\s+)?(?:folder|directory)(?:\s+called|\s+named)?\s+(.+)$",
        value,
        flags=re.IGNORECASE,
    )
    if match:
        return FileIntent("mkdir", destination=match.group(1).strip())

    match = re.match(r"^(?:(?:find|search|locate)(?:\s+for)?|where\s+is)\s+(.+?)[?]?$", value, flags=re.IGNORECASE)
    if match:
        query = re.sub(r"^my\s+", "", match.group(1).strip(), flags=re.IGNORECASE)
        return FileIntent("find", query=query)

    return None


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return "{:.1f} {}".format(value, unit)
        value /= 1024
    return "{} B".format(size)


__all__ = [
    "FileIntent",
    "FileManager",
    "UnsafePathError",
    "human_size",
    "parse_intent",
]
