from __future__ import annotations

import difflib
from pathlib import Path
from typing import Callable, Dict, Optional

from .modes.diary_mode import add_entry
from .logic.notes import add_note
from .logic.todo import add_task, list_tasks, mark_complete, delete_task
from .logic.codegen import lookup as code_lookup, explain as code_explain, add_example
from .logic.debugger import lookup as debug_lookup
from .logic.memory import load_memory
from .logic.summary import get_summary
from .logic.fallback import log_query
from .utils.datetime import prompt_timestamp
from .utils.voice import speak
from .utils.encryption import decrypt_bytes
from .utils.keys import get_key

try:
    from rich.console import Console
    _console = Console()

    def _cprint(msg: str, style: str = ""):
        _console.print(msg, style=style)
except Exception:  # rich not available
    def _cprint(msg: str, style: str = ""):
        print(msg)


CommandFunc = Callable[[str], Optional[str]]


HELP_TEXT = """Available commands:
/diary        - add a diary entry
/notes        - create a note
/todo         - manage todo list
/ask <q>      - ask how to code something
/code <task>  - generate code snippet
/debug <err>  - search for error fix
/teachcode    - teach a coding example
/memory       - list remembered items
/summary      - show data summary
/speak [txt]  - speak text aloud
/unlock <f>   - decrypt file
/demo         - show a quick demo
/help         - show this help
/exit         - exit program
"""


def cmd_help(_: str) -> None:
    _cprint(HELP_TEXT, "cyan")


def cmd_exit(_: str) -> str:
    ans = input("Are you sure you want to exit Solace? (y/n): ").strip().lower()
    if ans.startswith("y"):
        return "EXIT"
    return None


def cmd_diary(args: str) -> None:
    text = args
    if not text:
        _cprint("Enter diary text (end with blank line):", "cyan")
        lines = []
        while True:
            ln = input()
            if not ln:
                break
            lines.append(ln)
        text = "\n".join(lines)
    ts = prompt_timestamp()
    tag_line = input("Tags (space separated, optional): ").strip()
    tags = tag_line.split() if tag_line else []
    important = input("Mark as important? [y/N]: ").strip().lower().startswith("y")
    private = input("Encrypt this entry? (y/n): ").strip().lower().startswith("y")
    mood = add_entry(text, ts, tags, important, private)
    _cprint(f"Entry saved. Detected mood: {mood}", "green")


def cmd_notes(_: str) -> None:
    title = input("Title: ").strip()
    _cprint("Enter note text (end with blank line):", "cyan")
    lines = []
    while True:
        ln = input()
        if not ln:
            break
        lines.append(ln)
    text = "\n".join(lines)
    ts = prompt_timestamp()
    tag_line = input("Tags (space separated, optional): ").strip()
    tags = tag_line.split() if tag_line else []
    private = input("Encrypt this note? (y/n): ").strip().lower().startswith("y")
    add_note(title, text, ts, tags, private)
    _cprint("Note saved.", "green")


def cmd_todo(args: str) -> None:
    parts = args.split()
    if not parts:
        _cprint("Usage: /todo add <task> | /todo list | /todo done <id> | /todo delete <id>", "yellow")
        return
    sub = parts[0]
    if sub == "add" and len(parts) > 1:
        task_text = " ".join(parts[1:])
        ts = prompt_timestamp()
        private = input("Encrypt this item? (y/n): ").strip().lower().startswith("y")
        item = add_task(task_text, ts, private)
        _cprint(f"Added: {item['task']}", "green")
    elif sub == "list":
        tasks = list_tasks()
        for i, t in enumerate(tasks):
            mark = "x" if t.get("status") == "complete" else " "
            _cprint(f"[{mark}] {i}: {t['task']}")
    elif sub == "done" and len(parts) > 1:
        try:
            idx = int(parts[1])
        except ValueError:
            _cprint("Invalid id", "red")
            return
        if mark_complete(idx):
            _cprint("Task marked complete.", "green")
        else:
            _cprint("Task not found.", "red")
    elif sub == "delete" and len(parts) > 1:
        try:
            idx = int(parts[1])
        except ValueError:
            _cprint("Invalid id", "red")
            return
        if delete_task(idx):
            _cprint("Task deleted.", "green")
        else:
            _cprint("Task not found.", "red")
    else:
        _cprint("Usage: /todo add <task> | /todo list | /todo done <id> | /todo delete <id>", "yellow")


def _teach_missing(kind: str, query: str) -> None:
    log_query(kind, query)
    _cprint("I'm not sure yet. Would you like to teach me this?", "yellow")
    ans = input("[y/N]: ").strip().lower()
    if ans.startswith("y"):
        lang = input("Language: ").strip()
        desc = query
        _cprint("Enter code (end with blank line):", "cyan")
        lines: list[str] = []
        while True:
            ln = input()
            if not ln:
                break
            lines.append(ln)
        code_text = "\n".join(lines)
        explanation = input("Explanation: ").strip()
        add_example(lang, desc, code_text, explanation)
        _cprint("Thanks, stored!", "green")


def cmd_ask(args: str) -> Optional[str]:
    result = code_explain(args)
    if result:
        code, expl = result
        _cprint(code)
        _cprint(expl)
        return f"{code}\n{expl}"
    _teach_missing("ask", args)
    return None


def cmd_code(args: str) -> Optional[str]:
    result = code_lookup(args)
    if result:
        code, expl = result
        _cprint(code)
        _cprint(expl)
        return f"{code}\n{expl}"
    _teach_missing("code", args)
    return None


def cmd_debug(args: str) -> Optional[str]:
    fix = debug_lookup(args)
    if fix:
        _cprint(fix)
        return fix
    log_query("debug", args)
    _cprint("I don't know this error yet.", "yellow")
    return None


def cmd_teachcode(_: str) -> None:
    lang = input("Language: ").strip()
    desc = input("Description: ").strip()
    _cprint("Enter code (end with blank line):", "cyan")
    lines = []
    while True:
        ln = input()
        if not ln:
            break
        lines.append(ln)
    code_text = "\n".join(lines)
    explanation = input("Explanation: ").strip()
    add_example(lang, desc, code_text, explanation)
    _cprint("Example saved.", "green")


def cmd_memory(_: str) -> None:
    mem = load_memory()
    _cprint("Always:")
    for m in mem.get("always", []):
        _cprint(" - " + m)
    _cprint("Never:")
    for m in mem.get("never", []):
        _cprint(" - " + m)


def cmd_summary(_: str) -> None:
    info = get_summary()
    _cprint(f"Diary entries: {info['diary']}")
    _cprint(f"Code examples: {info['examples']}")
    _cprint(f"Knowledge pieces: {info['knowledge']}")
    _cprint(f"Unanswered fallbacks: {info['fallbacks']}")


def cmd_speak(args: str) -> None:
    text = args
    if not text:
        text = input("Text to speak: ").strip()
    if text:
        speak(text)


def cmd_unlock(args: str) -> None:
    path = args or input("File to unlock: ").strip()
    try:
        data = Path(path).read_bytes()
        text = decrypt_bytes(data, get_key()).decode("utf-8")
        _cprint(text)
    except Exception as e:  # noqa: BLE001
        _cprint(f"Error: {e}", "red")


def cmd_demo(_: str) -> None:
    _cprint("Solace demo:\n- try /diary to record a thought\n- use /notes to save markdown notes\n- /todo helps track tasks\n- ask coding questions with /ask", "cyan")


COMMAND_MAP: Dict[str, CommandFunc] = {
    "help": cmd_help,
    "exit": cmd_exit,
    "diary": cmd_diary,
    "notes": cmd_notes,
    "todo": cmd_todo,
    "ask": cmd_ask,
    "code": cmd_code,
    "debug": cmd_debug,
    "teachcode": cmd_teachcode,
    "memory": cmd_memory,
    "summary": cmd_summary,
    "speak": cmd_speak,
    "unlock": cmd_unlock,
    "demo": cmd_demo,
}


def dispatch(line: str) -> Optional[str | bool]:
    if not line.startswith("/"):
        return False
    parts = line[1:].split(maxsplit=1)
    cmd = parts[0]
    args = parts[1] if len(parts) > 1 else ""
    if cmd not in COMMAND_MAP:
        matches = [c for c in COMMAND_MAP if c.startswith(cmd)]
        if len(matches) == 1:
            cmd = matches[0]
        else:
            close = difflib.get_close_matches(cmd, COMMAND_MAP.keys(), n=1)
            if close:
                _cprint(f"Unknown command. Did you mean /{close[0]}?", "yellow")
            else:
                _cprint("Unknown command. Type /help for list.", "yellow")
            return True
    func = COMMAND_MAP.get(cmd)
    if not func:
        return True
    result = func(args)
    if result == "EXIT":
        return "EXIT"
    return result or True

