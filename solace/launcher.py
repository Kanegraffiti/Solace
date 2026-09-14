"""Supported launcher for Solace.

This module layers local Qwen, Excel/file skills, and the startup mini-manual
over the existing root CLI without changing its journal/memory semantics.
Installers point the ``solace`` command here.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Optional, Sequence

# When this file is launched directly from an installed wrapper, add the repo
# root so the historical root ``main.py`` remains importable.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from solace.termux_compat import ensure_termux_cryptography_compatible  # noqa: E402

# Some Android 16 / current Termux combinations do not expose CPython symbols
# globally enough for cryptography's Rust extension. Promote the active
# libpython inside this process first; bounded preload fallbacks are attempted
# only if Android still refuses the import. This is a no-op outside Termux.
ensure_termux_cryptography_compatible()

from rich.panel import Panel  # noqa: E402
from rich.prompt import Confirm, Prompt  # noqa: E402
from rich.table import Table  # noqa: E402

import main as core  # noqa: E402
from solace.configuration import get_cipher, get_storage_path  # noqa: E402
from solace.excel_skill import (  # noqa: E402
    answer_excel_query,
    create_chart,
    create_summary,
    formula_guide,
    inspect_workbook,
    known_formula_names,
    qwen_excel_prompt,
    search_functions,
    set_formula,
)
from solace.file_skill import FileManager, human_size, parse_intent  # noqa: E402
from solace.local_llm import run_qwen, runtime_status  # noqa: E402
from solace.project_task import (  # noqa: E402
    ProjectInspection,
    ProjectTaskError,
    choose_project_matches,
    execute_project_command,
    extract_zip,
    inspect_project,
    prepare_project_command,
    project_query,
    validate_zip,
    wants_project_execution,
)
from solace.updater import UpdateError, update_solace  # noqa: E402
from solace.user_manual import (  # noqa: E402
    MANUAL_TEXT,
    set_startup_manual,
    startup_manual_enabled,
)
from solace.voice_training import (  # noqa: E402
    VoiceTrainingError,
    make_summary,
    parse_transcript,
    participants,
    read_transcript,
    save_voice_dataset,
    selected_reviews,
)

FILE_MANAGER = FileManager()


def _show_manual() -> None:
    core.console.print(Panel(MANUAL_TEXT, title="Solace · quick start", border_style="cyan"))


def _handle_manual(args: str) -> None:
    action = args.strip().lower()
    if action in {"off", "hide", "disable"}:
        set_startup_manual(False)
        core.console.print(
            "[green]Startup manual hidden.[/] Use [bold]/manual[/bold] anytime, "
            "or [bold]/manual on[/bold] to restore it on startup."
        )
        return
    if action in {"on", "show", "enable"}:
        set_startup_manual(True)
        core.console.print("[green]Startup manual restored.[/]")
        _show_manual()
        return
    if action == "status":
        state = "on" if startup_manual_enabled() else "off"
        core.console.print(f"Startup manual: [bold]{state}[/bold]")
        return
    if action:
        core.console.print("[yellow]Usage: /manual [on|off|status][/]")
        return
    _show_manual()


def _handle_qwen(args: str) -> None:
    prompt = args.strip()
    if prompt.lower() == "status":
        ready, message = runtime_status()
        style = "green" if ready else "yellow"
        core.console.print(Panel(message, title="Qwen status", border_style=style))
        return

    if not prompt and core.PROMPT_DEFAULTS_ONLY:
        core.console.print("[yellow]Provide a prompt when scripting /qwen.[/]")
        return

    ready, message = runtime_status()
    if not ready:
        core.console.print(Panel(message, title="Qwen unavailable", border_style="yellow"))
        return

    core.console.print("[dim]Opening local Qwen. Use /exit or Ctrl+C inside Qwen to return to Solace.[/]")
    try:
        run_qwen(prompt or None, interactive=not bool(prompt))
    except KeyboardInterrupt:
        core.console.print("\n[yellow]Qwen stopped.[/]")
    except (OSError, RuntimeError, ValueError) as exc:
        core.console.print(Panel(str(exc), title="Qwen error", border_style="red"))
        return

    if prompt:
        core._log_event("qwen", prompt[:80])


def _show_file_paths(paths: Sequence[Path], title: str, show_size: bool = False) -> None:
    if not paths:
        core.console.print("[yellow]No matching files found.[/]")
        return
    table = Table(title=title, show_lines=True)
    table.add_column("#", justify="right")
    table.add_column("Path")
    if show_size:
        table.add_column("Size", justify="right")
    for index, path in enumerate(paths, start=1):
        row = [str(index), str(path)]
        if show_size:
            try:
                row.append(human_size(path.stat().st_size))
            except OSError:
                row.append("?")
        table.add_row(*row)
    core.console.print(table)


def _resolve_file_source(query: str) -> Optional[Path]:
    matches = FILE_MANAGER.find(query, limit=25)
    if len(matches) == 1:
        return matches[0]
    if not matches:
        if core.PROMPT_DEFAULTS_ONLY:
            core.console.print(f"[yellow]I couldn't find '{query}'. Provide an exact path interactively.[/]")
            return None
        supplied = Prompt.ask(f"I couldn't find '{query}'. Give me the path, or type cancel")
        if supplied.strip().lower() in {"cancel", "c", "quit", "exit"}:
            return None
        candidate = FILE_MANAGER.expand_path(supplied)
        if not candidate.exists():
            core.console.print(f"[red]That path does not exist:[/] {candidate}")
            return None
        return candidate.resolve()

    _show_file_paths(matches, "Possible matches")
    if core.PROMPT_DEFAULTS_ONLY:
        core.console.print("[yellow]Multiple matches found; scripted mode will not guess.[/]")
        return None
    choice = Prompt.ask("Choose a number, paste a path, or type cancel")
    if choice.strip().lower() in {"cancel", "c", "quit", "exit"}:
        return None
    if choice.strip().isdigit():
        index = int(choice.strip())
        if 1 <= index <= len(matches):
            return matches[index - 1]
    candidate = FILE_MANAGER.expand_path(choice)
    if candidate.exists():
        return candidate.resolve()
    core.console.print("[red]That selection was not valid.[/]")
    return None


def _confirm_mutation(message: str) -> bool:
    if core.PROMPT_DEFAULTS_ONLY:
        core.console.print("[yellow]File-changing actions require interactive confirmation.[/]")
        return False
    return Confirm.ask(message, default=False)


def _show_file_history() -> None:
    events = FILE_MANAGER.history(limit=25)
    if not events:
        core.console.print("[yellow]No Solace file operations recorded yet.[/]")
        return
    table = Table(title="Solace file history", show_lines=True)
    table.add_column("Time")
    table.add_column("Action")
    table.add_column("Details")
    for event in reversed(events):
        action = str(event.get("action", ""))
        details = str(event.get("source") or event.get("destination") or "")
        destination = event.get("destination")
        if event.get("source") and destination:
            details = f"{event.get('source')} → {destination}"
        table.add_row(str(event.get("timestamp", "")), action, details)
    core.console.print(table)


def _choose_trash_event(query: str) -> Optional[Dict[str, object]]:
    events = FILE_MANAGER.trashed(query, limit=25)
    if not events:
        core.console.print(f"[yellow]Nothing matching '{query}' is in Solace Trash.[/]")
        return None
    if len(events) == 1:
        return events[0]
    table = Table(title="Solace Trash", show_lines=True)
    table.add_column("#", justify="right")
    table.add_column("Original path")
    table.add_column("Deleted")
    for index, event in enumerate(events, start=1):
        table.add_row(str(index), str(event.get("source", "")), str(event.get("timestamp", "")))
    core.console.print(table)
    if core.PROMPT_DEFAULTS_ONLY:
        core.console.print("[yellow]Multiple trash matches found; scripted mode will not guess.[/]")
        return None
    choice = Prompt.ask("Choose a number or type cancel")
    if choice.strip().lower() in {"cancel", "c", "quit", "exit"}:
        return None
    if choice.strip().isdigit():
        index = int(choice.strip())
        if 1 <= index <= len(events):
            return events[index - 1]
    core.console.print("[red]Invalid selection.[/]")
    return None


def _file_usage() -> None:
    table = Table(title="Safe file manager")
    table.add_column("Example")
    table.add_column("What Solace does")
    table.add_row("/file find my invoice", "Search home/shared storage by filename")
    table.add_row("/file rename draft.pdf to final.pdf", "Find, confirm, then rename")
    table.add_row("/file copy photo.jpg to ~/Documents", "Copy without overwriting")
    table.add_row("/file move report.xlsx to ~/Documents", "Move without overwriting")
    table.add_row("/file delete old-report.pdf", "Move to Solace Trash, never rm")
    table.add_row("/file restore old-report.pdf", "Restore a trashed item")
    table.add_row("/file make folder Client Assets", "Create a directory")
    table.add_row("/file show 20 largest files", "Find large files")
    table.add_row("/file files modified today", "Show today's changed files")
    table.add_row("/file history", "Show Solace file transactions")
    table.add_row("/file undo", "Undo the latest supported file mutation")
    core.console.print(table)


def _handle_file(args: str) -> None:
    command = args.strip()
    if not command:
        _file_usage()
        return
    intent = parse_intent(command)
    if intent is None:
        core.console.print("[yellow]I couldn't map that to a safe file action.[/]")
        _file_usage()
        return

    try:
        if intent.action == "find":
            _show_file_paths(FILE_MANAGER.find(intent.query, limit=intent.limit), f"Files matching '{intent.query}'")
            return
        if intent.action == "largest":
            _show_file_paths(FILE_MANAGER.largest(intent.limit), "Largest files", show_size=True)
            return
        if intent.action == "modified-today":
            _show_file_paths(FILE_MANAGER.modified_today(), "Files modified today")
            return
        if intent.action == "history":
            _show_file_history()
            return
        if intent.action == "list-trash":
            events = FILE_MANAGER.trashed(limit=25)
            if not events:
                core.console.print("[yellow]Solace Trash is empty.[/]")
                return
            table = Table(title="Solace Trash", show_lines=True)
            table.add_column("Original path")
            table.add_column("Deleted")
            for event in events:
                table.add_row(str(event.get("source", "")), str(event.get("timestamp", "")))
            core.console.print(table)
            return
        if intent.action == "undo":
            if not _confirm_mutation("Undo the latest supported Solace file operation?"):
                return
            message = FILE_MANAGER.undo_last()
            core.console.print(Panel(message, title="File undo", border_style="green"))
            core._log_event("file", "undo")
            return
        if intent.action == "restore":
            event = _choose_trash_event(intent.query)
            if event is None:
                return
            if not _confirm_mutation(f"Restore {event.get('source')}?"):
                return
            restored = FILE_MANAGER.restore_event(event)
            core.console.print(Panel(str(restored), title="Restored", border_style="green"))
            core._log_event("file", f"restore {restored}")
            return
        if intent.action == "mkdir":
            if not _confirm_mutation(f"Create folder '{intent.destination}'?"):
                return
            created = FILE_MANAGER.make_directory(intent.destination)
            core.console.print(Panel(str(created), title="Folder created", border_style="green"))
            core._log_event("file", f"mkdir {created}")
            return

        source = _resolve_file_source(intent.source)
        if source is None:
            return
        if intent.action == "rename":
            if not _confirm_mutation(f"Rename\n{source}\nto\n{intent.destination}?"):
                return
            result = FILE_MANAGER.rename(source, intent.destination)
        elif intent.action == "copy":
            if not _confirm_mutation(f"Copy\n{source}\nto\n{intent.destination}?"):
                return
            result = FILE_MANAGER.copy(source, intent.destination)
        elif intent.action == "move":
            if not _confirm_mutation(f"Move\n{source}\nto\n{intent.destination}?"):
                return
            result = FILE_MANAGER.move(source, intent.destination)
        elif intent.action == "trash":
            if not _confirm_mutation(f"Move this to Solace Trash?\n{source}"):
                return
            result = FILE_MANAGER.trash(source)
            core.console.print(
                Panel(
                    f"Moved safely to Solace Trash:\n{result}\n\nUse /file undo or /file restore <name> to recover it.",
                    title="Trashed",
                    border_style="yellow",
                )
            )
            core._log_event("file", f"trash {source}")
            return
        else:
            _file_usage()
            return
        core.console.print(Panel(str(result), title=intent.action.title(), border_style="green"))
        core._log_event("file", command[:80])
    except (FileExistsError, FileNotFoundError, LookupError, OSError, PermissionError, ValueError) as exc:
        core.console.print(Panel(str(exc), title="File action stopped", border_style="red"))


def _do_usage() -> None:
    table = Table(title="Solace task planner")
    table.add_column("Example")
    table.add_column("What Solace does")
    table.add_row('/do inspect "Lola website"', "Find the folder or ZIP, then detect its tech stack")
    table.add_row('/do find "portfolio.zip"', "Preview safe extraction and inspect the project")
    table.add_row('/do run "Lola website"', "Inspect, then ask before each suggested project command")
    core.console.print(table)
    core.console.print(
        "[dim]/do inspect is read-only. /do run executes only after a separate confirmation for every command.[/]"
    )


def _choose_project(query: str) -> Optional[Path]:
    matches = choose_project_matches(FILE_MANAGER.find(query, limit=25))
    if not matches:
        core.console.print(f"[yellow]I couldn't find a project folder or ZIP matching '{query}'.[/]")
        return None
    if len(matches) == 1:
        return matches[0]
    _show_file_paths(matches, "Possible projects")
    if core.PROMPT_DEFAULTS_ONLY:
        core.console.print("[yellow]Multiple projects found; scripted mode will not guess.[/]")
        return None
    choice = Prompt.ask("Choose a number or type cancel")
    if choice.strip().lower() in {"cancel", "c", "quit", "exit"}:
        return None
    if choice.strip().isdigit():
        index = int(choice.strip())
        if 1 <= index <= len(matches):
            return matches[index - 1]
    core.console.print("[red]Invalid selection.[/]")
    return None


def _show_project_plan(source: Path, *, extraction: Optional[Path] = None) -> None:
    table = Table(title="Project task plan", show_lines=True)
    table.add_column("Step")
    table.add_column("Safety")
    table.add_column("Status")
    table.add_row("Find the requested project", "Read-only", str(source))
    if extraction is not None:
        table.add_row("Validate ZIP paths, links, size and integrity", "Read-only", "Ready")
        table.add_row("Extract to a new directory", "Changes files", str(extraction))
    table.add_row("Detect the tech stack", "Read-only", "Pending")
    table.add_row("Prepare launch guidance", "Read-only", "Pending")
    core.console.print(table)


def _show_project_inspection(result: ProjectInspection) -> None:
    sections = ["[bold]Project[/bold]\n{}".format(result.root)]
    sections.append("[bold]Detected stack[/bold]\n{}".format(", ".join(result.stack) or "Unknown"))
    evidence = "\n".join("- " + item for item in result.evidence) or "- None"
    sections.append("[bold]Evidence[/bold]\n{}".format(evidence))
    if result.next_commands:
        commands = "\n".join(
            "{}. {}".format(index, command) for index, command in enumerate(result.next_commands, 1)
        )
        sections.append("[bold]Suggested commands — not executed[/bold]\n{}".format(commands))
    sections.append("[bold]Notes[/bold]\n{}".format("\n".join("- " + note for note in result.notes)))
    core.console.print(Panel("\n\n".join(sections), title="Project inspection", border_style="green"))


def _handle_do(args: str) -> None:
    request = args.strip()
    if not request:
        _do_usage()
        return
    execute = wants_project_execution(request)
    query = project_query(request)
    if not query:
        core.console.print("[yellow]Tell me the project folder or ZIP name.[/]")
        _do_usage()
        return

    try:
        source = _choose_project(query)
        if source is None:
            return
        root = source
        if source.is_file():
            FILE_MANAGER.assert_allowed(source)
            destination = validate_zip(source)
            FILE_MANAGER.assert_allowed(destination)
            _show_project_plan(source, extraction=destination)
            if not _confirm_mutation("Extract this ZIP to a new folder?\n{}\n→ {}".format(source, destination)):
                core.console.print("[yellow]Stopped before extraction. Nothing was changed.[/]")
                return
            root = extract_zip(source)
            core.console.print(Panel(str(root), title="ZIP extracted", border_style="green"))
        else:
            _show_project_plan(source)
        result = inspect_project(root)
        _show_project_inspection(result)
        if execute:
            if core.PROMPT_DEFAULTS_ONLY:
                core.console.print("[yellow]Scripted mode will not execute project code.[/]")
                return
            if not result.next_commands:
                core.console.print("[yellow]No supported project commands were detected.[/]")
                return
            for suggested in result.next_commands:
                prepared = prepare_project_command(suggested, result)
                core.console.print(
                    Panel(
                        "Command: {}\nDirectory: {}\nRisk: {}".format(
                            prepared.command, result.root, prepared.risk
                        ),
                        title="Execution approval required",
                        border_style="yellow",
                    )
                )
                if not _confirm_mutation("Run this exact command?"):
                    core.console.print("[yellow]Skipped: {}[/]".format(prepared.command))
                    continue
                returncode = execute_project_command(prepared, result.root)
                if returncode != 0:
                    core.console.print(
                        Panel(
                            "Command exited with status {}. Remaining steps were not run.".format(returncode),
                            title="Project command stopped",
                            border_style="red",
                        )
                    )
                    break
        core._log_event("do", "inspect {}".format(result.root.name)[:80])
    except (FileExistsError, OSError, PermissionError, ProjectTaskError, ValueError) as exc:
        core.console.print(Panel(str(exc), title="Project task stopped", border_style="red"))


def _train_usage() -> None:
    table = Table(title="Local conversation training")
    table.add_column("Command")
    table.add_column("Purpose")
    table.add_row("/train chat", "Choose and privately review a WhatsApp/text transcript")
    table.add_row("/train chat <file.txt>", "Import one specific transcript")
    table.add_row("/train status", "List locally stored voice-training profiles")
    core.console.print(table)
    core.console.print("[dim]The original transcript is never changed or copied into Solace.[/]")


def _training_source(value: str) -> Optional[Path]:
    requested = value.strip().strip("\"'")
    if not requested:
        if core.PROMPT_DEFAULTS_ONLY:
            core.console.print("[yellow]Provide a .txt transcript path in scripted mode.[/]")
            return None
        requested = Prompt.ask("Path or filename of the WhatsApp/text export").strip()
    matches = [path for path in FILE_MANAGER.find(requested, limit=25) if path.suffix.casefold() == ".txt"]
    if not matches:
        core.console.print("[yellow]I couldn't find a .txt transcript matching that name or path.[/]")
        return None
    if len(matches) == 1:
        return matches[0]
    _show_file_paths(matches, "Possible conversation transcripts")
    choice = Prompt.ask("Choose a number or type cancel").strip().lower()
    if choice in {"cancel", "c", "quit", "exit"}:
        return None
    if choice.isdigit() and 1 <= int(choice) <= len(matches):
        return matches[int(choice) - 1]
    core.console.print("[red]Invalid selection.[/]")
    return None


def _review_voice_messages(reviews):
    approved = []
    removed = 0
    flagged = [review for review in reviews if review.flags]
    clean = [review for review in reviews if not review.flags]
    approved.extend(review.cleaned for review in clean if review.cleaned)
    core.console.print(
        "[cyan]Privacy scan:[/] {} clean messages; {} need review.".format(len(clean), len(flagged))
    )
    core.console.print(
        "[yellow]Automatic scanning cannot recognise every name, private story, nickname or context-specific insult. "
        "Only approve the final dataset if this assisted review is sufficient for your export.[/]"
    )
    for index, review in enumerate(flagged, start=1):
        changed = review.cleaned != review.original
        body = "Flags: {}\n\nOriginal:\n{}".format(", ".join(review.flags), review.original)
        if changed:
            body += "\n\nAutomatically redacted:\n{}".format(review.cleaned)
        core.console.print(Panel(body, title="Review {} of {}".format(index, len(flagged)), border_style="yellow"))
        default = "redacted" if changed else "remove"
        action = Prompt.ask(
            "Decision",
            choices=["remove", "redacted", "keep", "edit", "cancel"],
            default=default,
        )
        if action == "cancel":
            raise VoiceTrainingError("Import cancelled. No training data was saved.")
        if action == "remove":
            removed += 1
        elif action == "redacted":
            if not changed:
                removed += 1
            else:
                approved.append(review.cleaned)
        elif action == "keep":
            approved.append(review.original)
        else:
            edited = Prompt.ask("Type the safe replacement text").strip()
            if edited:
                approved.append(edited)
            else:
                removed += 1
    return approved, removed


def _train_status() -> None:
    root = get_storage_path(core.CONFIG, "training") / "voice"
    profiles = sorted(path for path in root.glob("*") if path.is_dir()) if root.exists() else []
    if not profiles:
        core.console.print("[yellow]No approved voice-training profiles yet.[/]")
        return
    table = Table(title="Local voice-training profiles")
    table.add_column("Profile")
    table.add_column("Encrypted examples")
    for profile in profiles:
        state = "yes" if (profile / "approved_examples.enc").is_file() else "missing"
        table.add_row(profile.name, state)
    core.console.print(table)


def _handle_train(args: str) -> None:
    action, _, remainder = args.strip().partition(" ")
    if action.casefold() == "status":
        _train_status()
        return
    if action.casefold() != "chat":
        _train_usage()
        return
    if core.PROMPT_DEFAULTS_ONLY:
        core.console.print("[yellow]Conversation imports require interactive local review.[/]")
        return
    try:
        source = _training_source(remainder)
        if source is None:
            return
        FILE_MANAGER.assert_allowed(source)
        messages = parse_transcript(read_transcript(source))
        people = participants(messages)
        table = Table(title="Whose voice should Solace learn?")
        table.add_column("#", justify="right")
        table.add_column("Speaker")
        table.add_column("Messages", justify="right")
        for index, (speaker, count) in enumerate(people, start=1):
            table.add_row(str(index), speaker, str(count))
        core.console.print(table)
        choice = Prompt.ask("Choose the speaker number or type cancel").strip().lower()
        if choice in {"cancel", "c", "quit", "exit"}:
            return
        if not choice.isdigit() or not 1 <= int(choice) <= len(people):
            raise VoiceTrainingError("Invalid speaker selection.")
        speaker = people[int(choice) - 1][0]
        profile = Prompt.ask("Voice profile name", default=speaker).strip()
        reviews = selected_reviews(messages, speaker)
        approved, removed = _review_voice_messages(reviews)
        core.console.print(
            Panel(
                "Source messages: {}\nSelected speaker: {}\nApproved: {}\nRemoved: {}\n"
                "Other speakers' messages will not be stored.\n"
                "The profile name and aggregate report are readable; approved message text is encrypted.".format(
                    len(messages), speaker, len(approved), removed
                ),
                title="Final local training preview",
            )
        )
        if not Confirm.ask("Encrypt and save this approved dataset?", default=False):
            core.console.print("[yellow]Stopped. No training data was saved.[/]")
            return
        summary = make_summary(profile, reviews, approved, removed, len(messages))
        destination = save_voice_dataset(
            get_storage_path(core.CONFIG, "training"),
            profile,
            approved,
            summary,
            get_cipher(core.CONFIG),
        )
        core.console.print(
            Panel(
                "Encrypted approved examples saved under:\n{}\n\nThe original transcript was not modified.".format(
                    destination
                ),
                title="Voice training saved",
                border_style="green",
            )
        )
        core._log_event("train", "chat profile {}".format(profile)[:80])
    except (OSError, PermissionError, ValueError, VoiceTrainingError) as exc:
        core.console.print(Panel(str(exc), title="Conversation training stopped", border_style="red"))


def _excel_usage() -> None:
    table = Table(title="Excel skill")
    table.add_column("Command")
    table.add_column("Purpose")
    table.add_row("/excel XLOOKUP", "Explain a formula with syntax and example")
    table.add_row("/excel functions [search]", "Search the local Excel function-name index")
    table.add_row("/excel pivot table", "Beginner PivotTable setup guide")
    table.add_row("/excel chart", "Chart-selection and setup guide")
    table.add_row("/excel inspect <file>", "Inspect sheets, formulas, tables, charts and pivots")
    table.add_row("/excel set <file> | <sheet> | <cell> | <formula>", "Write a formula to a new workbook copy")
    table.add_row("/excel make-chart <file> | <sheet> | <range> | <type> [| anchor]", "Create bar/column/line/pie chart")
    table.add_row("/excel summarize <file> | <sheet> | <group> | <value> | <sum|count|average>", "Create pivot-style summary sheet")
    core.console.print(table)


def _excel_file(value: str) -> Optional[Path]:
    return _resolve_file_source(value.strip())


def _show_workbook_inspection(path: Path) -> None:
    rows = inspect_workbook(path)
    table = Table(title=f"Workbook: {path.name}", show_lines=True)
    table.add_column("Sheet")
    table.add_column("Rows", justify="right")
    table.add_column("Cols", justify="right")
    table.add_column("Formulas", justify="right")
    table.add_column("Tables", justify="right")
    table.add_column("Charts", justify="right")
    table.add_column("Pivots", justify="right")
    for row in rows:
        table.add_row(
            str(row["sheet"]),
            str(row["rows"]),
            str(row["columns"]),
            str(row["formulas"]),
            str(row["tables"]),
            str(row["charts"]),
            str(row["pivots"]),
        )
    core.console.print(table)


def _excel_qwen_fallback(query: str) -> None:
    ready, message = runtime_status()
    if not ready:
        core.console.print(
            Panel(
                "I don't have a deterministic local guide for that exact Excel question yet.\n\n"
                f"{message}\n\nUse /excel functions <term> to search the local formula index.",
                title="Excel",
                border_style="yellow",
            )
        )
        return
    core.console.print("[dim]Using local Qwen as Solace's Excel explanation layer.[/]")
    try:
        run_qwen(qwen_excel_prompt(query), interactive=False)
    except (KeyboardInterrupt, OSError, RuntimeError, ValueError) as exc:
        core.console.print(Panel(str(exc), title="Excel/Qwen error", border_style="red"))


def _handle_excel(args: str) -> None:
    query = args.strip()
    if not query:
        _excel_usage()
        return
    head, _, rest = query.partition(" ")
    command = head.lower()

    try:
        if command == "functions":
            matches = search_functions(rest, limit=60)
            total = len(known_formula_names())
            table = Table(title=f"Excel function index · {total} known names")
            table.add_column("Function")
            for name in matches:
                table.add_row(name)
            if matches:
                core.console.print(table)
            else:
                core.console.print("[yellow]No function names matched that search.[/]")
            return
        if command == "formula":
            name = rest.strip().upper()
            guide = formula_guide(name)
            if guide:
                answer = answer_excel_query(name)
                core.console.print(Panel(answer or guide.purpose, title="Excel formula"))
            else:
                _excel_qwen_fallback(rest or query)
            return
        if command == "inspect":
            path = _excel_file(rest)
            if path is not None:
                _show_workbook_inspection(path)
            return
        if command == "set":
            parts = [part.strip() for part in rest.split("|")]
            if len(parts) != 4:
                core.console.print("[yellow]Usage: /excel set <file> | <sheet> | <cell> | <formula>[/]")
                return
            path = _excel_file(parts[0])
            if path is None:
                return
            output = set_formula(path, parts[1], parts[2], parts[3])
            core.console.print(Panel(str(output), title="Workbook copy created", border_style="green"))
            return
        if command in {"make-chart", "makechart"}:
            parts = [part.strip() for part in rest.split("|")]
            if len(parts) not in {4, 5}:
                core.console.print(
                    "[yellow]Usage: /excel make-chart <file> | <sheet> | <range> | <bar|column|line|pie> [| anchor][/]"
                )
                return
            path = _excel_file(parts[0])
            if path is None:
                return
            anchor = parts[4] if len(parts) == 5 else "H2"
            output = create_chart(path, parts[1], parts[2], parts[3], anchor=anchor)
            core.console.print(Panel(str(output), title="Chart workbook created", border_style="green"))
            return
        if command == "summarize":
            parts = [part.strip() for part in rest.split("|")]
            if len(parts) != 5:
                core.console.print(
                    "[yellow]Usage: /excel summarize <file> | <sheet> | <group header> | <value header> | <sum|count|average>[/]"
                )
                return
            path = _excel_file(parts[0])
            if path is None:
                return
            output = create_summary(path, parts[1], parts[2], parts[3], parts[4])
            core.console.print(
                Panel(
                    f"Created a pivot-style summary sheet in:\n{output}\n\n"
                    "This is a normal summary worksheet, not a native Excel PivotTable.",
                    title="Summary workbook created",
                    border_style="green",
                )
            )
            return

        answer = answer_excel_query(query)
        if answer:
            core.console.print(Panel(answer, title="Excel"))
            return
        _excel_qwen_fallback(query)
    except (FileExistsError, FileNotFoundError, KeyError, OSError, ValueError) as exc:
        core.console.print(Panel(str(exc), title="Excel action stopped", border_style="red"))


def _extended_help(_: str) -> None:
    core._ORIGINAL_HELP_HANDLER("")
    table = Table(title="Local AI, Excel, files & startup help", show_header=True)
    table.add_column("Command")
    table.add_column("Description")
    table.add_row("/qwen <prompt>", "Open the local Qwen coder with an initial prompt")
    table.add_row("/qwen", "Open an interactive local Qwen chat")
    table.add_row("/qwen status", "Check the llama.cpp runtime and Qwen model paths")
    table.add_row("/excel <question>", "Excel formulas, PivotTables, charts, errors and workbook tools")
    table.add_row("/file <request>", "Safely find/copy/move/rename/trash/restore user files")
    table.add_row("/file history", "Show file operations performed by Solace")
    table.add_row("/file undo", "Undo the latest supported file operation")
    table.add_row("/do inspect <project>", "Find/extract a project, detect its stack, and prepare launch steps")
    table.add_row("/do run <project>", "Inspect, then approve or skip each detected project command")
    table.add_row("/train chat [file.txt]", "Privately review and encrypt a local conversation dataset")
    table.add_row("/train status", "List local voice-training profiles")
    table.add_row("/manual", "Show the tiny startup manual now")
    table.add_row("/manual off", "Hide the manual on future starts")
    table.add_row("/manual on", "Restore the manual on future starts")
    core.console.print(table)


def _register_extensions() -> None:
    if not hasattr(core, "_ORIGINAL_HELP_HANDLER"):
        core._ORIGINAL_HELP_HANDLER = core.COMMANDS["help"]
    core.COMMANDS["help"] = _extended_help
    core.COMMANDS["manual"] = _handle_manual
    core.COMMANDS["qwen"] = _handle_qwen
    core.COMMANDS["excel"] = _handle_excel
    core.COMMANDS["file"] = _handle_file
    core.COMMANDS["do"] = _handle_do
    core.COMMANDS["train"] = _handle_train


def _is_scripted(argv: Sequence[str]) -> bool:
    scripted_flags = {"-c", "--command", "--command-file"}
    return any(arg in scripted_flags or arg.startswith("--command=") for arg in argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "update":
        if len(args) != 1:
            core.console.print("[yellow]Usage: solace update[/]")
            return 2
        core.console.print("[cyan]Checking the canonical Solace repository for updates...[/]")
        try:
            result = update_solace(PROJECT_ROOT)
        except UpdateError as exc:
            core.console.print(Panel(str(exc), title="Solace update stopped", border_style="red"))
            return 1
        if not result.changed:
            core.console.print(Panel("Solace is already up to date. User data was not touched.", title="Solace update"))
            return 0
        preserved = "\n".join(f"- {path}" for path in result.preserved_data)
        core.console.print(
            Panel(
                f"Updated {result.previous_commit[:12]} → {result.current_commit[:12]}.\n\n"
                f"Preserved user data:\n{preserved}",
                title="Solace updated",
                border_style="green",
            )
        )
        return 0
    _register_extensions()
    if not _is_scripted(args) and startup_manual_enabled():
        _show_manual()
    core.main(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
