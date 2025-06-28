from __future__ import annotations

from datetime import datetime
import sys
from . import commands
from .commands import dispatch
from .config import CONFIG_FILE, DEFAULT_MODE, SETTINGS, save_settings, verify_password
from .modes.diary_mode import add_entry
from .modes.chat_mode import chat, ChatLockedError
from .logic.notes import add_note
from .logic.codegen import lookup as code_lookup
from .logic.fallback import log_query
from .utils.datetime import prompt_timestamp
from .devmode import enabled as dev_enabled, populate as dev_populate
from .plugins import load_plugins
from .logic.code_history import add_entry as _hist_add, find_similar
from .logic.knowledge_index import add_entry as knowledge_add
from .utils.voice import print_missing_packages


def _setup() -> None:
    print("First time setup for Solace\n")
    name = input("What is your name? ").strip()
    pronouns = input("Your pronouns: ").strip()
    mode = input("Preferred default mode (diary/chat/code): ").strip() or "diary"
    tts = input("Enable text to speech? (y/n) [y]: ").strip().lower()
    tts_enabled = (tts == "" or tts.startswith("y"))
    stt = input("Enable speech recognition? (y/n) [n]: ").strip().lower()
    stt_enabled = stt.startswith("y")
    theme = input("Theme (light/dark) [light]: ").strip().lower() or "light"
    autosave = input("Enable autosave? (y/n) [y]: ").strip().lower()
    autosave_bool = (autosave.startswith("y") or autosave == "")
    typing_effect = input("Enable typing effect? (y/n) [y]: ").strip().lower()
    typing_bool = (typing_effect.startswith("y") or typing_effect == "")
    encryption = input("Encrypt entries by default? (y/n) [n]: ").strip().lower().startswith("y")
    allow_plugins = input("Allow plugins? (y/n) [n]: ").strip().lower().startswith("y")
    mimic_persona = input("Mimic persona speaker name (optional): ").strip()
    use_password = input("Lock Solace with a password? (y/n) [n]: ").strip().lower().startswith("y")
    password_hash = ""
    password_hint = ""
    if use_password:
        import getpass
        import hashlib
        while True:
            pw1 = getpass.getpass("Set password: ")
            pw2 = getpass.getpass("Confirm password: ")
            if pw1 == pw2:
                password_hash = hashlib.sha256(pw1.encode("utf-8")).hexdigest()
                break
            print("Passwords do not match. Try again.")
        password_hint = input("Password hint (optional): ").strip()
    cfg = {
        "name": name,
        "pronouns": pronouns,
        "default_mode": mode,
        "voice_mode_enabled": tts_enabled or stt_enabled,
        "enable_tts": tts_enabled,
        "enable_stt": stt_enabled,
        "theme": theme,
        "autosave": autosave_bool,
        "typing_effect": typing_bool,
        "encryption": encryption,
        "allow_plugins": allow_plugins,
        "mimic_persona": mimic_persona,
        "password_hash": password_hash,
        "password_hint": password_hint,
    }
    save_settings(cfg)
    if tts_enabled or stt_enabled:
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
    else:
        verify_password(SETTINGS)
    args = sys.argv[1:]
    if "--speak" in args:
        SETTINGS["enable_tts"] = True
    if "--listen" in args:
        SETTINGS["enable_stt"] = True
    if dev_enabled(sys.argv):
        dev_populate()
        print("[Dev mode] Dummy data loaded.")
    if SETTINGS.get("allow_plugins"):
        load_plugins()
    if SETTINGS.get("enable_tts") or SETTINGS.get("enable_stt"):
        print_missing_packages()
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
        elif mode == "chat":
            try:
                resp = chat(line)
                print(resp)
            except ChatLockedError as e:
                print(e)
        elif mode == "code":
            cached = find_similar(line)
            if cached:
                print(cached["code"])
                print(cached["explanation"])
                continue
            result = code_lookup(line)
            if result:
                code, expl = result
                _hist_add(line, code, expl, "")
                knowledge_add(line, "", expl, code, [])
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
