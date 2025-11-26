"""Controller classes that expose Solace behaviors to UI layers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import journal
import mimic
import trainer
from solace.configuration import (
    CONFIG_PATH,
    get_cipher,
    get_storage_path,
    list_known_paths,
    save_config,
    toggle_voice,
    update_alias,
    update_tone,
    verify_password,
)
from solace.memory import search_entries


@dataclass
class SolaceContext:
    """Runtime configuration shared between controllers."""

    config: dict
    cipher: Optional[object] = None
    password: Optional[str] = None

    def refresh_security(self, *, cipher: Optional[object], password: Optional[str]) -> None:
        self.cipher = cipher
        self.password = password


class JournalController:
    """Operations over journal entries with optional encryption."""

    def __init__(self, context: SolaceContext) -> None:
        self.context = context

    def add_entry(
        self,
        entry_type: str,
        content: str,
        *,
        when: Optional[datetime] = None,
        tags: Optional[List[str]] = None,
    ) -> journal.JournalEntry:
        return journal.add_entry(
            content,
            entry_type=entry_type,
            tags=tags,
            when=when,
            cipher=self.context.cipher,
            password=self.context.password,
        )

    def list_entries(self, tags: Optional[Iterable[str]] = None) -> List[journal.JournalEntry]:
        entries = journal.load_entries(cipher=self.context.cipher, password=self.context.password)
        if not tags:
            return entries
        filtered_tags = {tag.lower() for tag in tags}
        return [entry for entry in entries if filtered_tags.intersection({tag.lower() for tag in entry.tags})]

    def search(self, query: str) -> List:
        entries = journal.load_entries(cipher=self.context.cipher, password=self.context.password)
        return search_entries(query, entries)

    def export(self, *, format_choice: str = "markdown", destination: Optional[Path] = None) -> Path:
        target = destination
        if target is None:
            target = get_storage_path(self.context.config, "journal") / f"journal-export.{format_choice[:3]}"
        return journal.export_entries(
            target,
            format=format_choice,
            cipher=self.context.cipher,
            password=self.context.password,
        )


class TrainerController:
    """Wrapper around trainer helpers for the UI."""

    def teach(self, language: str, content: str, *, category: str = "example") -> trainer.Snippet:
        snippet = trainer.teach(language.lower(), content, category=category)
        trainer.record_session(language, content, tags=[category])
        return snippet

    def query(self, language: str, prompt: str):
        return trainer.query(language.lower(), prompt)


class MimicController:
    """Proxy for mimic reply generation."""

    def reply(self, prompt: str) -> str:
        return mimic.reply(prompt)


class SettingsController:
    """Manage Solace configuration for both CLI and TUI layers."""

    def __init__(self, context: SolaceContext) -> None:
        self.context = context

    @property
    def config(self) -> dict:
        return self.context.config

    def verify_security(self) -> None:
        password = verify_password(self.context.config)
        cipher = None
        if self.context.config.get("security", {}).get("encryption_enabled", True):
            cipher = get_cipher(self.context.config, password=password)
        self.context.refresh_security(cipher=cipher, password=password)

    def toggle_encryption(self, enabled: bool) -> bool:
        self.context.config.setdefault("security", {})["encryption_enabled"] = enabled
        save_config(self.context.config)
        return enabled

    def toggle_voice(self, *, tts: Optional[bool] = None, stt: Optional[bool] = None) -> Dict[str, bool]:
        updated = toggle_voice(self.context.config, tts=tts, stt=stt)
        self.context.config.update(updated)
        return updated.get("voice", {}) if isinstance(updated, dict) else self.context.config.get("voice", {})

    def set_tone(self, tone: str) -> str:
        self.context.config.update(update_tone(self.context.config, tone))
        return tone

    def set_alias(self, alias: str) -> str:
        self.context.config.update(update_alias(self.context.config, alias))
        return alias

    def info(self) -> Dict[str, str]:
        return {
            "config": str(CONFIG_PATH),
            "version": self.context.config.get("version", "2.0"),
            "paths": [str(path) for path in list_known_paths(self.context.config)],
        }
