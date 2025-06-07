import json
import hashlib
import getpass
import sys
from pathlib import Path

CONFIG_FILE = Path(__file__).resolve().parents[1] / "settings" / "settings.json"

DEFAULT_CONFIG = {
    "name": "",
    "pronouns": "",
    "default_mode": "diary",
    "voice_mode_enabled": True,
    "theme": "light",
    "autosave": True,
    "typing_effect": True,
    "encryption": False,
    "allow_plugins": False,
    "mimic_persona": "",
    "password_hash": "",
    "password_hint": "",
}


def load_settings() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return DEFAULT_CONFIG.copy()


def save_settings(data: dict) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    SETTINGS.update(data)


def verify_password(settings: dict) -> None:
    """Prompt for the password if enabled."""
    hash_val = settings.get("password_hash")
    if not hash_val:
        return
    hint = settings.get("password_hint", "")
    for _ in range(3):
        pw = getpass.getpass("Enter Solace password: ")
        if hashlib.sha256(pw.encode("utf-8")).hexdigest() == hash_val:
            return
        print("Incorrect password.")
        if hint:
            print(f"Hint: {hint}")
    print(f"Forgot the password? Delete {CONFIG_FILE} to reset.")
    sys.exit(1)


SETTINGS = load_settings()

# voice toggle
VOICE_MODE_ENABLED = SETTINGS.get("voice_mode_enabled", True)

# new toggles for manual timestamp prompts and tagging features
ENABLE_TIMESTAMP_REQUEST = True
ENABLE_TAGGING = True

# default start mode
DEFAULT_MODE = SETTINGS.get("default_mode", "diary")

