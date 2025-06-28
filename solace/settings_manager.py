"""Manage Solace user settings with encryption support."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any, Dict

SETTINGS_FILE = Path(__file__).resolve().parents[1] / "settings" / "settings.json"

DEFAULT_SETTINGS: Dict[str, Any] = {
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
    "password_enabled": False,
    "password_hash": "",
    "password_hint": "",
    "encryption_enabled": False,
    "salt": "",
}


def load_settings() -> Dict[str, Any]:
    data = DEFAULT_SETTINGS.copy()
    if SETTINGS_FILE.exists():
        try:
            stored = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            stored = {}
        data.update(stored)
    return data


def save_settings(data: Dict[str, Any]) -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    SETTINGS.update(data)


def enable_encryption() -> None:
    """Turn on encryption and generate a salt if missing."""
    if not SETTINGS.get("salt"):
        SETTINGS["salt"] = base64.b64encode(os.urandom(16)).decode("utf-8")
    SETTINGS["encryption_enabled"] = True
    save_settings(SETTINGS)


SETTINGS = load_settings()
