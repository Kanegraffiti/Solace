"""Entry point for the Solace offline personal assistant."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.table import Table

import journal
import mimic
import trainer
from solace.configuration import (
    CONFIG_PATH,
    ensure_storage_dirs,
    get_storage_path,
    list_known_paths,
    load_config,
    save_config,
    set_password,
    update_alias,
    update_tone,
)
from tui.app import SolaceApp
from tui.controllers import (
    JournalController,
    MimicController,
    SettingsController,
    SolaceContext,
    TrainerController,
)


console = Console()
CONFIG = load_config()
ensure_storage_dirs(CONFIG)
PROFILE = CONFIG.get("profile", {})
SESSION_LOG = get_storage_path(CONFIG, "root") / "session.log"

CONTEXT = SolaceContext(CONFIG)
journal_controller = JournalController(CONTEXT)
trainer_controller = TrainerController()
mimic_controller = MimicController()
settings_controller = SettingsController(CONTEXT)


class VoiceIO:
    def __init__(self, config: dict) -> None:
        self.config = config
        self.engine = None
        self.recogniser = None
        try:  # TTS
            if self.config.get("voice", {}).get("tts"):
                import pyttsx3

                self.engine = pyttsx3.init()
        except Exception:  # noqa: BLE001 - best effort only
            self.engine = None

        try:  # STT
            if self.config.get("voice", {}).get("stt"):
                import speech_recognition as sr

                self.recogniser = sr.Recognizer()
        except Exception:  # noqa: BLE001
            self.recogniser = None

    def speak(self, text: str) -> None:
        if not text or not self.engine:
            return
        self.engine.say(text)
        self.engine.runAndWait()

    def listen(self) -> Optional[str]:
        if not self.recogniser:
            console.print("[yellow]Speech recognition is not available.[/]")
            return None
        try:
            import speech_recognition as sr

            with sr.Microphone() as source:
                console.print("[cyan]Listening...[/]")
                audio = self.recogniser.listen(source, timeout=5)
            return self.recogniser.recognize_sphinx(audio)
        except Exception as exc:  # noqa: BLE001
            console.print(f"[red]Voice capture failed:[/] {exc}")
            return None


VOICE = VoiceIO(CONFIG)
SESSION_PASSWORD: Optional[str] = None
SESSION_CIPHER = None


def _log_event(kind: str, content: str) -> None:
    SESSION_LOG.parent.mkdir(parents=True, exist_ok=True)
    with SESSION_LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"{datetime.now().isoformat(timespec='seconds')}\t{kind}\t{content}\n")


def _prompt_datetime() -> datetime:
    suggestion = journal.suggest_datetime()
    while True:
        date_str = Prompt.ask("Date", default=suggestion.strftime("%Y-%m-%d"))
        time_str = Prompt.ask("Time", default=suggestion.strftime("%H:%M"))
        try:
            return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        except ValueError:
            console.print("[red]Invalid date or time. Please try again.[/]")


def _prompt_multiline() -> str:
    console.print("[bold cyan]Enter your thoughts. Finish with an empty line.[/]")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            line = ""
        if not line:
            break
        lines.append(line)
    return "\n".join(lines)


def _capture_entry(entry_type: str, args: str) -> None:
    text = args.strip() or _prompt_multiline()
    if not text.strip():
        console.print("[yellow]No content captured.[/]")
        return
    when = _prompt_datetime()
    tags_input = Prompt.ask("Tags (comma separated)", default="")
    tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
    entry = journal_controller.add_entry(text, entry_type=entry_type, tags=tags, when=when)
    console.print(Panel(f"Saved {entry.entry_type} entry for {entry.date} {entry.time}.", title="Journal"))
    VOICE.speak(f"Entry saved for {entry.date}")
    _log_event(entry_type, entry.content[:80])


def _handle_search(args: str) -> None:
    query = args.strip() or Prompt.ask("What would you like to find?")
    results = journal_controller.search(query)
    if not results:
        console.print("[yellow]No matching memories yet.[/]")
        return
    table = Table(title=f"Results for '{query}'", show_lines=True)
    table.add_column("Score", justify="right")
    table.add_column("Date")
    table.add_column("Type")
    table.add_column("Preview")
    for hit in results:
        preview = hit.entry.content.splitlines()[0][:60]
        table.add_row(f"{hit.score:.2f}", hit.entry.date, hit.entry.entry_type, preview)
    console.print(table)


def _handle_export(args: str) -> None:
    parts = args.split()
    if not parts:
        format_choice = Prompt.ask("Export format", choices=["markdown", "pdf"], default="markdown")
    else:
        format_choice = parts[0]
    if len(parts) > 1:
        destination = Path(parts[1]).expanduser()
    else:
        destination = get_storage_path(CONFIG, "journal") / f"journal-export.{format_choice[:3]}"
    exported = journal_controller.export(format_choice=format_choice, destination=destination)
    console.print(Panel(f"Exported entries to {exported}", title="Export"))


def _handle_teach(args: str) -> None:
    parts = args.split()
    language = parts[0] if parts else Prompt.ask("Language", choices=list(trainer.LANGUAGE_MAP.keys()))
    content = " ".join(parts[1:]) or _prompt_multiline()
    category = Prompt.ask("Category", choices=["example", "error", "tip"], default="example")
    snippet = trainer_controller.teach(language, content, category=category)
    console.print(Panel(f"Stored {category} for {language} from manual teaching.", title="Trainer"))
    VOICE.speak("Training updated")


def _handle_remember(args: str) -> None:
    parts = args.split()
    if not parts:
        language = Prompt.ask("Language", choices=list(trainer.LANGUAGE_MAP.keys()))
        prompt = Prompt.ask("What should I recall?")
    else:
        language = parts[0]
        prompt = " ".join(parts[1:]) or Prompt.ask("What should I recall?")
    results = trainer_controller.query(language, prompt)
    if not results:
        console.print("[yellow]Nothing in the training set yet. Try /teach first.[/]")
        return
    for snippet in results:
        panel = Panel(snippet.text, title=f"{snippet.language.title()} {snippet.category}", subtitle=snippet.source)
        console.print(panel)


def _handle_code(args: str) -> None:
    parts = args.split()
    if not parts:
        language = Prompt.ask("Language", choices=list(trainer.LANGUAGE_MAP.keys()))
        prompt = Prompt.ask("Keyword")
    else:
        language = parts[0]
        prompt = " ".join(parts[1:]) or Prompt.ask("Keyword")
    results = trainer_controller.query(language, prompt)
    if not results:
        console.print("[yellow]No examples found. Teach me with /teach <language> first.[/]")
        return
    for snippet in results:
        syntax = Syntax(snippet.text, language.lower(), line_numbers=False, word_wrap=True)
        console.print(Panel(syntax, title=f"{language.title()} example", subtitle=snippet.source))


def _handle_mimic(args: str) -> None:
    response = mimic_controller.reply(args)
    console.print(Panel(response, title="Mimic"))
    VOICE.speak(response)
    _log_event("mimic", args)


def _handle_settings(args: str) -> None:
    global CONFIG
    parts = args.split()
    if not parts:
        table = Table(title="Settings commands")
        table.add_column("Command")
        table.add_column("Description")
        table.add_row("password", "Change or remove the password lock")
        table.add_row("voice", "Toggle text-to-speech or speech recognition")
        table.add_row("tone <friendly|quiet|verbose>", "Adjust Solace response tone")
        table.add_row("alias <name>", "Update the launcher alias in the config")
        table.add_row("backup", "Create a backup archive of data")
        table.add_row("restore <archive>", "Restore data from an archive")
        table.add_row("info", "Show configuration paths and version")
        table.add_row("fallback <mode>", "Set mimic fallback style")
        console.print(table)
        return

    subcommand = parts[0].lower()
    if subcommand == "password":
        CONFIG = set_password(CONFIG)
        CONTEXT.config = CONFIG
        return
    if subcommand == "voice":
        tts = Confirm.ask("Enable text to speech?", default=CONFIG.get("voice", {}).get("tts", False))
        stt = Confirm.ask("Enable speech to text?", default=CONFIG.get("voice", {}).get("stt", False))
        settings_controller.toggle_voice(tts=tts, stt=stt)
        console.print("Voice preferences saved. Re-run Solace to reload engines.")
        return
    if subcommand == "tone":
        tone = parts[1] if len(parts) > 1 else Prompt.ask("Tone", choices=["friendly", "quiet", "verbose"], default=CONFIG.get("tone", "friendly"))
        CONFIG = update_tone(CONFIG, tone)
        CONTEXT.config = CONFIG
        console.print(f"Tone set to {tone}.")
        return
    if subcommand == "alias":
        alias = parts[1] if len(parts) > 1 else Prompt.ask("Alias", default=CONFIG.get("alias", "solace"))
        CONFIG = update_alias(CONFIG, alias)
        CONTEXT.config = CONFIG
        console.print(f"Alias stored as {alias}. Re-run install.py --alias {alias} to update launchers.")
        return
    if subcommand == "backup":
        target = get_storage_path(CONFIG, "root") / f"solace-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        archive = shutil.make_archive(str(target), "zip", root_dir=get_storage_path(CONFIG, "root"))
        extra = CONFIG_PATH
        console.print(Panel(f"Backup created at {archive}. Remember to copy {extra} as well.", title="Backup"))
        return
    if subcommand == "restore" and len(parts) > 1:
        archive = Path(parts[1]).expanduser()
        if not archive.exists():
            console.print("[red]Archive not found.[/]")
            return
        shutil.unpack_archive(str(archive), get_storage_path(CONFIG, "root"))
        console.print("[green]Backup restored. Restart Solace to reload data.[/]")
        return
    if subcommand == "info":
        info = settings_controller.info()
        table = Table(title="Solace info")
        table.add_column("Key")
        table.add_column("Value")
        table.add_row("Config", info.get("config", str(CONFIG_PATH)))
        table.add_row("Version", info.get("version", CONFIG.get("version", "2.0")))
        for path in info.get("paths", list_known_paths(CONFIG)):
            table.add_row("Storage", str(path))
        console.print(table)
        return
    if subcommand == "fallback" and len(parts) > 1:
        CONFIG.setdefault("memory", {})["fallback_mode"] = parts[1]
        save_config(CONFIG)
        console.print(f"Fallback mode set to {parts[1]}.")
        return
    console.print("[yellow]Unknown settings subcommand. Use /settings for options.[/]")


def _handle_listen(_: str) -> None:
    heard = VOICE.listen()
    if heard:
        console.print(Panel(heard, title="Heard"))


def _handle_help(_: str) -> None:
    table = Table(title="Solace commands", show_header=True)
    table.add_column("Command")
    table.add_column("Description")
    table.add_row("/diary", "Capture a dated diary entry")
    table.add_row("/notes", "Save study notes with tags")
    table.add_row("/todo", "Record a to-do item")
    table.add_row("/quote", "Save an inspiring quote")
    table.add_row("/search <query>", "Search indexed memories")
    table.add_row("/export [format] [path]", "Export entries to Markdown or PDF")
    table.add_row("/teach <language>", "Add a training snippet manually")
    table.add_row("/remember <language> <query>", "Recall training notes")
    table.add_row("/code <language> <topic>", "Show code examples from training data")
    table.add_row("/mimic", "Generate a rule-based conversation reply")
    table.add_row("/listen", "Capture voice input when STT is enabled")
    table.add_row("/settings", "Manage Solace configuration")
    table.add_row("/help", "Show this command list")
    table.add_row("/exit", "Save and leave")
    console.print(table)


def _verify_security() -> None:
    global SESSION_PASSWORD, SESSION_CIPHER
    try:
        settings_controller.verify_security()
        SESSION_PASSWORD = CONTEXT.password
        SESSION_CIPHER = CONTEXT.cipher
    except PermissionError:
        console.print("[red]Password verification failed. Exiting.[/]")
        sys.exit(1)


COMMANDS: Dict[str, Callable[[str], None]] = {
    "help": _handle_help,
    "diary": lambda args: _capture_entry("diary", args),
    "notes": lambda args: _capture_entry("notes", args),
    "todo": lambda args: _capture_entry("todo", args),
    "quote": lambda args: _capture_entry("quote", args),
    "search": _handle_search,
    "export": _handle_export,
    "teach": _handle_teach,
    "remember": _handle_remember,
    "code": _handle_code,
    "mimic": _handle_mimic,
    "settings": _handle_settings,
    "listen": _handle_listen,
}


COLON_TYPES = {
    ":diary": "diary",
    ":notes": "notes",
    ":todo": "todo",
    ":quote": "quote",
}


def run_cli() -> None:
    console.print(Panel(f"Welcome back, {PROFILE.get('name', 'Friend')}!", title="Solace"))
    _verify_security()
    console.print("Type /help for commands or /settings to configure Solace.")

    while True:
        try:
            raw = Prompt.ask("[bold cyan]solace[/]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[bold]Goodbye![/]")
            break
        if raw is None:
            continue
        text = raw.strip()
        if not text:
            continue
        if text.lower() in {"exit", "quit"}:
            console.print("[green]Take care.[/]")
            break
        if text.startswith("/"):
            name, _, remainder = text[1:].partition(" ")
            handler = COMMANDS.get(name.lower())
            if handler is None:
                console.print(f"[red]Unknown command:[/] {name}")
                continue
            handler(remainder)
            continue
        if text.split()[0].lower() in COLON_TYPES:
            prefix, _, remainder = text.partition(" ")
            _capture_entry(COLON_TYPES[prefix.lower()], remainder)
            continue
        _capture_entry("diary", text)

    console.print(f"[cyan]Session log stored at {SESSION_LOG}[/]")


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Solace personal assistant")
    parser.add_argument("--tui", action="store_true", help="Launch the Textual user interface")
    args = parser.parse_args(argv)

    if args.tui:
        _verify_security()
        app = SolaceApp(
            CONFIG,
            journal_controller,
            trainer_controller,
            mimic_controller,
            settings_controller,
            voice=VOICE,
        )
        app.run()
        return

    run_cli()


if __name__ == "__main__":
    main()
