"""Textual application entrypoint for Solace."""

from __future__ import annotations

from typing import Optional

from textual.app import App
from textual.binding import Binding

from tui.controllers import JournalController, MimicController, SettingsController, TrainerController
from tui.screens import EntryDetailScreen, JournalListScreen, SearchScreen, SettingsScreen


class SolaceApp(App):
    """A Textual-powered experience for navigating Solace."""

    CSS_PATH = None
    BINDINGS = [
        Binding("ctrl+n", "new_diary", "New diary entry"),
        Binding("t", "tag_filter", "Filter tags"),
        Binding("e", "export", "Export"),
        Binding("s", "search", "Search"),
        Binding("ctrl+,", "settings", "Settings"),
    ]

    def __init__(
        self,
        config: dict,
        journal_controller: JournalController,
        trainer_controller: TrainerController,
        mimic_controller: MimicController,
        settings_controller: SettingsController,
        voice: Optional[object] = None,
    ) -> None:
        super().__init__()
        self.config = config
        self.journal_controller = journal_controller
        self.trainer_controller = trainer_controller
        self.mimic_controller = mimic_controller
        self.settings_controller = settings_controller
        self.voice = voice

    def on_mount(self) -> None:
        if "journal" not in self.screen_stack:
            self.push_screen(JournalListScreen(self.journal_controller), name="journal")

    def action_new_diary(self) -> None:
        self.push_screen(EntryDetailScreen(self.journal_controller), name="entry-detail")

    def action_tag_filter(self) -> None:
        journal = self.get_screen("journal")
        if isinstance(journal, JournalListScreen):
            journal.post_message(JournalListScreen.RequestTagFilter())

    def action_search(self) -> None:
        self.push_screen(SearchScreen(self.journal_controller), name="search")

    def action_export(self) -> None:
        exported = self.journal_controller.export()
        self.notify(f"Exported entries to {exported}", timeout=4)

    def action_settings(self) -> None:
        self.push_screen(SettingsScreen(self.settings_controller), name="settings")
