import json
import hashlib
import hmac
import os
import getpass
import sys
from pathlib import Path

CONFIG_FILE = Path(__file__).resolve().parents[1] / "settings" / "settings.json"

DEFAULT_CONFIG = {
    "name": "",
    "pronouns": "",
    "default_mode": "diary",
    "voice_mode_enabled": True,
    "enable_tts": True,
    "enable_stt": False,
    "theme": "light",
    "autosave": True,
    "typing_effect": True,
    "encryption": False,
    "allow_plugins": False,
    "mimic_persona": "",
    "password_hash": "",
    "password_hint": "",
    "password_salt": "",
}


def load_settings() -> dict:
    data = DEFAULT_CONFIG.copy()
    if CONFIG_FILE.exists():
        try:
            stored = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            stored = {}
        data.update(stored)
    return data


def save_settings(data: dict) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    SETTINGS.update(data)




def _ensure_password_salt(settings: dict) -> str:
    salt = settings.get("password_salt", "")
    if not salt:
        salt = os.urandom(16).hex()
        settings["password_salt"] = salt
        save_settings(settings)
    return salt


def _hash_password(password: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), 210_000).hex()

def verify_password(settings: dict) -> None:
    """Prompt for the password if enabled."""
    hash_val = settings.get("password_hash")
    if not hash_val:
        return
    hint = settings.get("password_hint", "")
    for _ in range(3):
        pw = getpass.getpass("Enter Solace password: ")
        salt = _ensure_password_salt(settings)
        if hmac.compare_digest(_hash_password(pw, salt), hash_val):
            return
        # Backwards compatibility with legacy SHA-256 hashes.
        if hmac.compare_digest(hashlib.sha256(pw.encode("utf-8")).hexdigest(), hash_val):
            settings["password_hash"] = _hash_password(pw, salt)
            save_settings(settings)
            return
        print("Incorrect password.")
        if hint:
            print(f"Hint: {hint}")
    print(f"Forgot the password? Delete {CONFIG_FILE} to reset.")
    sys.exit(1)


SETTINGS = load_settings()

# voice toggle
VOICE_MODE_ENABLED = SETTINGS.get("enable_tts", True) or SETTINGS.get("enable_stt", False)

# new toggles for manual timestamp prompts and tagging features
ENABLE_TIMESTAMP_REQUEST = True
ENABLE_TAGGING = True

# default start mode
DEFAULT_MODE = SETTINGS.get("default_mode", "diary")

