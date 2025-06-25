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
from .logic.recall import search as recall_search
from .logic.summary import get_summary
from .logic.fallback import log_query
from .utils.datetime import prompt_timestamp
from .utils.voice import speak
from .utils.encryption import decrypt_bytes
from .utils.keys import get_key
from .config import SETTINGS, save_settings

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
/recall <q>   - search diary and notes
/summary      - show data summary
/speak [txt]  - speak text aloud
/unlock <f>   - decrypt file
/demo         - show a quick demo
/mode settings- configure preferences
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


def cmd_recall(args: str) -> None:
    query = args or input("Search query: ").strip()
    if not query:
        _cprint("Please provide a search term or #tag", "yellow")
        return
    results = recall_search(query)
    if not results:
        _cprint("No matches found.", "yellow")
        return
    for item in results:
        ts = item.get("timestamp", "")
        title = item.get("title", "(untitled)")
        tags = " ".join(item.get("tags", []))
        snippet = item.get("text", "").splitlines()[0][:80]
        _cprint(f"{ts} {title} [{tags}]", "green")
        if snippet:
            _cprint(f"  {snippet}")

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


def _ask_yes_no(prompt: str, current: bool) -> bool:
    default = "Y" if current else "N"
    ans = input(f"{prompt} [y/n] ({default}): ").strip().lower()
    if not ans:
        return current
    return ans.startswith("y")


def _ask_choice(prompt: str, options: list[str], current: str) -> str:
    opts = "/".join(options)
    ans = input(f"{prompt} ({opts}) [{current}]: ").strip().lower()
    return ans if ans in options else current


def cmd_mode(args: str) -> None:
    if args.strip().lower() != "settings":
        _cprint("Usage: /mode settings", "yellow")
        return
    _cprint("Configure Solace settings. Leave blank to keep current values.", "cyan")
    theme = _ask_choice("Theme", ["light", "dark"], SETTINGS.get("theme", "light"))
    autosave = _ask_yes_no("Autosave", SETTINGS.get("autosave", True))
    typing = _ask_yes_no("Typing effect", SETTINGS.get("typing_effect", True))
    default = _ask_choice("Default mode", ["diary", "chat", "code"], SETTINGS.get("default_mode", "diary"))
    encrypt = _ask_yes_no("Encrypt by default", SETTINGS.get("encryption", False))
    plugins = _ask_yes_no("Allow plugins", SETTINGS.get("allow_plugins", False))
    mimic = input(f"Mimic persona speaker name [{SETTINGS.get('mimic_persona','')}] : ").strip() or SETTINGS.get("mimic_persona", "")
    use_pass = _ask_yes_no("Password lock", bool(SETTINGS.get("password_hash")))
    pwd_hash = SETTINGS.get("password_hash", "")
    hint = SETTINGS.get("password_hint", "")
    if use_pass:
        import getpass, hashlib
        if not pwd_hash:
            while True:
                p1 = getpass.getpass("Set password: ")
                p2 = getpass.getpass("Confirm password: ")
                if p1 == p2:
                    pwd_hash = hashlib.sha256(p1.encode("utf-8")).hexdigest()
                    break
                print("Passwords do not match.")
            hint = input("Password hint (optional): ").strip()
        else:
            change = _ask_yes_no("Change password", False)
            if change:
                old = getpass.getpass("Current password: ")
                if hashlib.sha256(old.encode("utf-8")).hexdigest() == pwd_hash:
                    while True:
                        n1 = getpass.getpass("New password: ")
                        n2 = getpass.getpass("Confirm password: ")
                        if n1 == n2:
                            pwd_hash = hashlib.sha256(n1.encode("utf-8")).hexdigest()
                            break
                        print("Passwords do not match.")
                    hint = input("Password hint (optional): ").strip()
                else:
                    print("Incorrect password. Keeping existing.")
    else:
        pwd_hash = ""
        hint = ""
    SETTINGS.update({
        "theme": theme,
        "autosave": autosave,
        "typing_effect": typing,
        "default_mode": default,
        "encryption": encrypt,
        "allow_plugins": plugins,
        "mimic_persona": mimic,
        "password_hash": pwd_hash,
        "password_hint": hint,
    })
    save_settings(SETTINGS)
    _cprint("Settings saved.", "green")


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
    "recall": cmd_recall,
    "summary": cmd_summary,
    "speak": cmd_speak,
    "unlock": cmd_unlock,
    "demo": cmd_demo,
    "mode": cmd_mode,
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

