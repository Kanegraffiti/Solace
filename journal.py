"""Rich journaling helpers with encryption and export support."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from cryptography.fernet import Fernet, InvalidToken

from solace.configuration import ensure_storage_dirs, get_cipher, get_storage_path, load_config

CONFIG = load_config()
ensure_storage_dirs(CONFIG)
ENTRIES_FILE = get_storage_path(CONFIG, "journal") / "entries.json"


@dataclass
class JournalEntry:
    identifier: str
    entry_type: str
    timestamp: str
    date: str
    time: str
    content: str
    tags: List[str] = None
    encrypted: bool = False
    metadata: Dict[str, str] = None

    def serialise(self) -> Dict[str, object]:
        data = asdict(self)
        data["tags"] = self.tags or []
        data["metadata"] = self.metadata or {}
        return data


def _load_raw_entries() -> List[Dict[str, object]]:
    if not ENTRIES_FILE.exists():
        ENTRIES_FILE.parent.mkdir(parents=True, exist_ok=True)
        ENTRIES_FILE.write_text("[]", encoding="utf-8")
        return []
    try:
        data = json.loads(ENTRIES_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    return []


def _save_raw_entries(entries: Iterable[Dict[str, object]]) -> None:
    ENTRIES_FILE.parent.mkdir(parents=True, exist_ok=True)
    ENTRIES_FILE.write_text(json.dumps(list(entries), indent=2), encoding="utf-8")


def _ensure_cipher(cipher: Optional[Fernet], password: Optional[str]) -> Optional[Fernet]:
    if cipher:
        return cipher
    if CONFIG.get("security", {}).get("encryption_enabled", True):
        try:
            return get_cipher(CONFIG, password=password)
        except PermissionError:
            return None
    return None


def add_entry(
    content: str,
    *,
    entry_type: str,
    tags: Optional[List[str]] = None,
    when: Optional[datetime] = None,
    cipher: Optional[Fernet] = None,
    password: Optional[str] = None,
) -> JournalEntry:
    when = when or datetime.now()
    cipher = _ensure_cipher(cipher, password)
    encrypted = bool(cipher) and CONFIG.get("security", {}).get("encryption_enabled", True)
    payload = content
    if encrypted:
        payload = cipher.encrypt(content.encode("utf-8")).decode("utf-8")

    entry = JournalEntry(
        identifier=str(uuid.uuid4()),
        entry_type=entry_type,
        timestamp=when.strftime("%Y-%m-%dT%H:%M:%S"),
        date=when.strftime("%Y-%m-%d"),
        time=when.strftime("%H:%M"),
        content=payload,
        tags=tags or [],
        encrypted=encrypted,
        metadata={},
    )

    entries = _load_raw_entries()
    entries.append(entry.serialise())
    _save_raw_entries(entries)
    return entry


def load_entries(
    *,
    cipher: Optional[Fernet] = None,
    password: Optional[str] = None,
    include_encrypted: bool = True,
) -> List[JournalEntry]:
    cipher = _ensure_cipher(cipher, password)
    results: List[JournalEntry] = []
    for item in _load_raw_entries():
        entry = JournalEntry(
            identifier=item.get("identifier", str(uuid.uuid4())),
            entry_type=item.get("entry_type", "diary"),
            timestamp=item.get("timestamp", datetime.now().isoformat(timespec="seconds")),
            date=item.get("date", ""),
            time=item.get("time", ""),
            content=item.get("content", ""),
            tags=item.get("tags") or [],
            encrypted=bool(item.get("encrypted")),
            metadata=item.get("metadata") or {},
        )
        if entry.encrypted and cipher:
            try:
                entry.content = cipher.decrypt(entry.content.encode("utf-8")).decode("utf-8")
                entry.encrypted = False
            except InvalidToken:
                if not include_encrypted:
                    continue
        elif entry.encrypted and not cipher:
            if not include_encrypted:
                continue
        results.append(entry)
    return results


def export_entries(
    destination: Path,
    *,
    format: str = "markdown",
    cipher: Optional[Fernet] = None,
    password: Optional[str] = None,
) -> Path:
    entries = load_entries(cipher=cipher, password=password)
    if format.lower() in {"markdown", "md"}:
        lines = ["# Solace journal export", ""]
        for entry in entries:
            lines.append(f"## {entry.date} {entry.time} – {entry.entry_type.title()}")
            if entry.tags:
                lines.append(f"*Tags:* {', '.join(entry.tags)}")
            lines.append("")
            lines.append(entry.content)
            lines.append("")
        destination.write_text("\n".join(lines), encoding="utf-8")
        return destination

    if format.lower() == "pdf":
        try:
            from fpdf import FPDF
        except Exception as exc:  # noqa: BLE001 - surface missing optional dep
            raise RuntimeError("PDF export requires the 'fpdf' package") from exc

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.multi_cell(0, 10, "Solace journal export")
        pdf.ln(4)
        pdf.set_font("Arial", size=12)
        for entry in entries:
            pdf.set_font("Arial", "B", 12)
            pdf.multi_cell(0, 8, f"{entry.date} {entry.time} – {entry.entry_type.title()}")
            if entry.tags:
                pdf.set_font("Arial", size=10)
                pdf.multi_cell(0, 6, f"Tags: {', '.join(entry.tags)}")
            pdf.set_font("Arial", size=11)
            pdf.multi_cell(0, 6, entry.content)
            pdf.ln(4)
        pdf.output(str(destination))
        return destination

    raise ValueError(f"Unsupported export format: {format}")


def has_entries() -> bool:
    return bool(_load_raw_entries())


def suggest_datetime() -> datetime:
    return datetime.now()


ENTRY_TYPES = ["diary", "notes", "todo", "quote"]


__all__ = [
    "ENTRY_TYPES",
    "JournalEntry",
    "add_entry",
    "load_entries",
    "export_entries",
    "has_entries",
    "suggest_datetime",
]
