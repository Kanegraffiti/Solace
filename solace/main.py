from __future__ import annotations

from datetime import datetime
from . import commands
from .commands import dispatch
from .config import CONFIG_FILE, DEFAULT_MODE, SETTINGS, save_settings
from .modes.diary_mode import add_entry
from .logic.notes import add_note
from .logic.codegen import lookup as code_lookup
from .logic.fallback import log_query
from .utils.datetime import prompt_timestamp


def _setup() -> None:
    print("First time setup for Solace\n")
    name = input("What is your name? ").strip()
    pronouns = input("Your pronouns: ").strip()
    mode = input("Preferred default mode (diary/code/notes): ").strip() or "diary"
    voice_mode = input("Enable voice mode? (y/n): ").strip().lower().startswith("y")
    cfg = {
        "name": name,
        "pronouns": pronouns,
        "default_mode": mode,
        "voice_mode_enabled": voice_mode,
    }
    save_settings(cfg)
    if voice_mode:
        from .utils.envcheck import check_voice_dependencies
        check_voice_dependencies()
    _demo_seed()


def _demo_seed() -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    add_entry("[DEMO] This is a sample diary entry.", ts, ["demo"], False, False)
    add_note("Demo note", "This is a sample note.", ts, ["demo"], False)
    add_task = commands.COMMAND_MAP.get("todo")  # type: ignore
    if callable(add_task):
        add_task("add Demo todo item")  # type: ignore


def main() -> None:
    if not CONFIG_FILE.exists():
        _setup()
    mode = SETTINGS.get("default_mode", DEFAULT_MODE)
    print("Welcome to Solace. Type /help for commands.")
    last_response = ""
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if line.startswith('/'):
            result = dispatch(line)
            if result == "EXIT":
                break
            if isinstance(result, str):
                last_response = result
            continue
        if mode == "diary":
            ts = prompt_timestamp()
            mood = add_entry(line, ts, [], False, False)
            print(f"Entry saved. Detected mood: {mood}")
        elif mode == "notes":
            ts = prompt_timestamp()
            add_note("Quick note", line, ts, [], False)
            print("Note saved.")
        elif mode == "code":
            result = code_lookup(line)
            if result:
                code, expl = result
                print(code)
                print(expl)
            else:
                log_query("code", line)
                print("I don't know this one yet.")
        else:
            print("Unknown mode")
    print("Goodbye!")


if __name__ == "__main__":
    main()
