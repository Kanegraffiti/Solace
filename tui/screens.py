"""Textual screens for the Solace TUI."""

from __future__ import annotations

from datetime import datetime
from typing import List
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, ListItem, ListView, Static, Switch, TextArea

from tui.controllers import JournalController, SettingsController


class JournalListScreen(Screen):
    """Display journal entries with optional tag filtering."""

    BINDINGS = [
        ("enter", "open_entry", "Open selected entry"),
    ]

    def __init__(self, controller: JournalController) -> None:
        super().__init__()
        self.controller = controller
        self.entries: List = []
        self.tag_filter: List[str] = []

    class RequestTagFilter(Message):
        """Request focusing the tag filter input."""

    class RequestRefresh(Message):
        """Signal that entries should refresh."""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Vertical(
            Label("Journal entries", id="journal-title"),
            Input(placeholder="Filter by tag and press Enter", id="tag-filter"),
            ListView(id="entries"),
            Static("Shortcuts: ctrl+n new entry • t filter tags • e export", id="hints"),
        )
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_entries()

    def refresh_entries(self) -> None:
        entries_widget = self.query_one("#entries", ListView)
        entries_widget.clear()
        tags = self.tag_filter or None
        self.entries = self.controller.list_entries(tags=tags)
        for entry in self.entries:
            preview = entry.content.splitlines()[0][:80] if entry.content else ""
            label = f"{entry.date} {entry.time} • {entry.entry_type.title()}"
            content = f"{label}\n{preview}"
            entries_widget.append(ListItem(Static(content), id=entry.identifier))

    def action_open_entry(self) -> None:
        entries_widget = self.query_one("#entries", ListView)
        if entries_widget.index is None:
            return
        idx = entries_widget.index
        if idx is None or idx >= len(self.entries):
            return
        self.app.push_screen(EntryDetailScreen(self.controller, entry=self.entries[idx]))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "tag-filter":
            self.tag_filter = [tag.strip() for tag in event.value.split(",") if tag.strip()]
            self.refresh_entries()

    def handle_request_tag_filter(self, _: RequestTagFilter) -> None:  # noqa: D401 - Textual handler
        """Focus the tag filter from an app-level shortcut."""
        self.query_one("#tag-filter", Input).focus()

    def handle_request_refresh(self, _: RequestRefresh) -> None:  # noqa: D401 - Textual handler
        """Refresh list when notified by other screens."""
        self.refresh_entries()


class EntryDetailScreen(Screen):
    """View or create a journal entry."""

    def __init__(self, controller: JournalController, entry=None) -> None:
        super().__init__()
        self.controller = controller
        self.entry = entry

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield VerticalScroll(
            Label("New diary entry" if self.entry is None else "Entry details", id="detail-title"),
            Input(value=self.entry.entry_type if self.entry else "diary", placeholder="Type", id="entry-type"),
            Input(value=",".join(self.entry.tags) if self.entry else "", placeholder="Tags (comma separated)", id="entry-tags"),
            TextArea(value=self.entry.content if self.entry else "", placeholder="Write your thoughts...", id="entry-content", height=10),
            Horizontal(
                Button("Save", id="save"),
                Button("Cancel", id="cancel"),
            ),
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.app.pop_screen()
            return
        if event.button.id == "save":
            self.save_entry()

    def save_entry(self) -> None:
        entry_type = self.query_one("#entry-type", Input).value or "diary"
        tags = [tag.strip() for tag in self.query_one("#entry-tags", Input).value.split(",") if tag.strip()]
        content = self.query_one("#entry-content", TextArea).value
        if self.entry is None:
            self.controller.add_entry(entry_type, content, when=datetime.now(), tags=tags)
        else:
            self.controller.add_entry(entry_type, content, when=datetime.fromisoformat(self.entry.timestamp), tags=tags)
        self.app.post_message(JournalListScreen.RequestRefresh())
        self.app.notify("Entry saved", timeout=3)
        self.app.pop_screen()


class SearchScreen(Screen):
    """Search through journal entries."""

    def __init__(self, controller: JournalController) -> None:
        super().__init__()
        self.controller = controller
        self.results: List = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Vertical(
            Label("Search memories"),
            Input(placeholder="Type search query and press Enter", id="search-query"),
            ListView(id="search-results"),
        )
        yield Footer()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "search-query":
            return
        query = event.value.strip()
        if not query:
            return
        self.results = self.controller.search(query)
        results_widget = self.query_one("#search-results", ListView)
        results_widget.clear()
        for hit in self.results:
            preview = hit.entry.content.splitlines()[0][:80]
            label = f"{hit.entry.date} {hit.entry.time} • {hit.entry.entry_type.title()}"
            results_widget.append(ListItem(Static(f"{label}\n{preview}")))


class SettingsScreen(Screen):
    """Settings toggles surfaced in the TUI."""

    def __init__(self, controller: SettingsController) -> None:
        super().__init__()
        self.controller = controller

    def compose(self) -> ComposeResult:
        voice = self.controller.config.get("voice", {})
        encryption_enabled = self.controller.config.get("security", {}).get("encryption_enabled", True)
        yield Header(show_clock=True)
        yield Vertical(
            Label("Settings"),
            Switch(value=encryption_enabled, name="encryption", id="encryption-toggle", label="Encryption"),
            Switch(value=voice.get("tts", False), name="tts", id="tts-toggle", label="Text to speech"),
            Switch(value=voice.get("stt", False), name="stt", id="stt-toggle", label="Speech to text"),
            Static(f"Config: {self.controller.info().get('config')}"),
        )
        yield Footer()

    def on_switch_changed(self, event: Switch.Changed) -> None:
        if event.switch.id == "encryption-toggle":
            enabled = bool(event.value)
            self.controller.toggle_encryption(enabled)
            self.app.notify(f"Encryption {'enabled' if enabled else 'disabled'}", timeout=3)
        if event.switch.id in {"tts-toggle", "stt-toggle"}:
            voice = self.controller.toggle_voice(
                tts=event.value if event.switch.id == "tts-toggle" else None,
                stt=event.value if event.switch.id == "stt-toggle" else None,
            )
            status = ", ".join(key for key, val in voice.items() if val) or "Voice off"
            self.app.notify(f"Voice updated: {status}", timeout=3)
