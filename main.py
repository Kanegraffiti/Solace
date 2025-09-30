"""Entry point for the lightweight Solace command line interface.

This script welcomes the user, loads their profile from ``memory/user.json``
and routes slash commands to the appropriate helper modules.  It keeps the
implementation intentionally friendly for people who are just getting started
with Python projects.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable, Dict

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich.table import Table

import journal
import mimic
import trainer
from solace.logic import codegen

# Paths ---------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
MEMORY_DIR = BASE_DIR / "memory"
USER_FILE = MEMORY_DIR / "user.json"
SESSION_LOG = MEMORY_DIR / "session.log"

console = Console()


def _ensure_memory_dir() -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    if not SESSION_LOG.exists():
        SESSION_LOG.touch()


def _load_user_profile() -> Dict[str, str]:
    """Return the user's saved profile, prompting for basics if missing."""
    _ensure_memory_dir()
    if USER_FILE.exists():
        try:
            return json.loads(USER_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            console.print("[yellow]Could not read memory/user.json. Starting fresh.")
    profile: Dict[str, str] = {}
    console.print(Panel("Welcome to Solace! Let's set up a quick profile.", title="First run"))
    profile["name"] = Prompt.ask("What should I call you?", default="Friend")
    profile["goal"] = Prompt.ask("What brings you here today?", default="journal")
    USER_FILE.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    return profile


def _log_event(kind: str, content: str) -> None:
    """Append an interaction to ``memory/session.log``."""
    _ensure_memory_dir()
    with SESSION_LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"{kind}: {content}\n")


# Command handlers ----------------------------------------------------------

def _handle_help(_: str) -> None:
    """Display all supported commands in a compact table."""
    table = Table(title="Solace commands", show_lines=True)
    table.add_column("Command", justify="left", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")
    table.add_row("/journal", "Write a new journal entry or paste quick thoughts.")
    table.add_row("/code <topic>", "Look up example code snippets using the local knowledge base.")
    table.add_row("/teach", "Store a rule or reminder inside the knowledge trainer.")
    table.add_row("/mimic", "Let your journaling twin craft a response using your tone.")
    table.add_row("/status", "Show quick stats about recent activity.")
    table.add_row("/help", "Show this table again.")
    table.add_row("/exit", "Save and close Solace.")
    console.print(table)


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


def _save_journal(text: str, *, ask_for_tags: bool) -> None:
    text = text.strip()
    if not text:
        console.print("[yellow]Nothing captured. Entry cancelled.")
        return
    tags = []
    if ask_for_tags:
        tags_input = Prompt.ask("Any tags? (comma separated)", default="")
        tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
    entry = journal.add_entry(text, tags=tags)
    console.print(Panel(f"Saved at [green]{entry['timestamp']}[/] with tags {tags or 'none'}.", title="Journal"))
    _log_event("journal", text)


def _handle_journal(args: str) -> None:
    """Prompt for a journal entry and save it through :mod:`journal`."""
    text = args.strip() or _prompt_multiline()
    _save_journal(text, ask_for_tags=True)


def _handle_code(args: str) -> None:
    """Look up example code using :mod:`solace.logic.codegen`."""
    query = args.strip() or Prompt.ask("What coding task should I recall?")
    if not query:
        console.print("[yellow]No query provided.")
        return
    result = codegen.lookup(query)
    if not result:
        console.print("[red]I could not find a matching example yet. Try teaching me with /teach!")
        return
    code, explanation = result
    language = codegen.detect_language(query)
    syntax = Syntax(code, language or "python", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title="Code snippet"))
    console.print(Panel(explanation or "", title="Why it works", expand=False))
    _log_event("code", query)


def _handle_teach(args: str) -> None:
    """Collect training data and persist it through :mod:`trainer`."""
    rule = args.strip()
    if not rule:
        rule = Prompt.ask("What's the rule or fact you want me to remember?")
    example = Prompt.ask("Any example or context to go with it?", default="")
    tags_raw = Prompt.ask("Tags (comma separated, optional)", default="")
    tags = [item.strip() for item in tags_raw.split(",") if item.strip()]
    saved = trainer.record(rule, example or None, tags=tags)
    console.print(Panel(f"Learned: {saved['rule']}", title="Trainer", subtitle="Thanks for teaching me!"))
    _log_event("teach", saved["rule"])


def _handle_mimic(args: str) -> None:
    """Generate a persona-style reply using :mod:`mimic`."""
    prompt = args.strip()
    if not prompt:
        prompt = Prompt.ask("What should your Solace twin respond to?", default="")
    response = mimic.reply(prompt)
    console.print(Panel(response, title="Mimic mode", border_style="magenta"))
    _log_event("mimic", prompt)


def _handle_status(_: str) -> None:
    """Summarise stored entries and knowledge for the user."""
    entries = journal.load_entries()
    knowledge = trainer.load_knowledge()
    table = Table(title="Your Solace snapshot")
    table.add_column("Category", style="cyan", no_wrap=True)
    table.add_column("Count", justify="right")
    table.add_row("Journal entries", str(len(entries)))
    table.add_row("Knowledge rules", str(len(knowledge)))
    console.print(table)


COMMANDS: Dict[str, Callable[[str], None]] = {
    "help": _handle_help,
    "journal": _handle_journal,
    "code": _handle_code,
    "teach": _handle_teach,
    "mimic": _handle_mimic,
    "status": _handle_status,
    "exit": lambda _: (_raise_exit()),
    "quit": lambda _: (_raise_exit()),
}


class _ExitSignal(Exception):
    """Internal exception used to break out of the input loop."""


def _raise_exit() -> None:
    raise _ExitSignal


def main() -> None:
    """Run the interactive Solace command line session."""
    profile = _load_user_profile()
    console.print(Panel(f"Welcome back, [bold green]{profile.get('name', 'Friend')}[/]!", title="Solace"))
    console.print("Type /help to see available commands. Regular text is saved as a journal entry.")

    while True:
        try:
            raw = Prompt.ask("[bold cyan]solace[/]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[bold]Exiting... Goodbye![/]")
            break
        if raw is None:
            continue
        text = raw.strip()
        if not text:
            continue
        if text.lower() in {"exit", "quit"}:
            console.print("[bold green]Take care![/]")
            break
        if text.startswith("/"):
            name, _, remainder = text[1:].partition(" ")
            handler = COMMANDS.get(name.lower())
            if handler is None:
                console.print(f"[red]Unknown command:[/] {name}. Try /help.")
                continue
            try:
                handler(remainder)
            except _ExitSignal:
                console.print("[bold green]Take care![/]")
                break
            except Exception as exc:  # noqa: BLE001
                console.print(f"[red]Something went wrong:[/] {exc}")
            continue

        # Plain text defaults to journaling for a quick capture experience.
        _save_journal(text, ask_for_tags=False)

    console.print("[bold cyan]Session saved in memory/session.log[/]")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold]Session aborted. See you soon![/]")
        sys.exit(0)
