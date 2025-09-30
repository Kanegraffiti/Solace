"""Central configuration management for the Solace CLI.

This module unifies all runtime configuration handling in a single place so
that the rest of the application can focus on features.  The configuration is
stored inside ``~/.solaceconfig.json`` to make it easy to inspect and back up
by hand.  The structure is deliberately human readable and resilient to
missing values – unknown keys are ignored while defaults are automatically
merged in when loading.

The module also implements lightweight password management and exposes helper
utilities for deriving Fernet keys that are shared by the journaling,
knowledge, and memory subsystems.  Passwords are hashed using SHA-256 so that
the clear text is never written to disk.  A dedicated 32-byte salt is stored
alongside the config for key derivation with PBKDF2.
"""

from __future__ import annotations

import getpass
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable

from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet


CONFIG_PATH = Path.home() / ".solaceconfig.json"
STORAGE_DIR = Path.home() / ".solace"
DEFAULT_ALIAS_NAME = "solace"


def _default_storage_paths() -> Dict[str, str]:
    return {
        "root": str(STORAGE_DIR),
        "journal": str(STORAGE_DIR / "journal"),
        "knowledge": str(STORAGE_DIR / "knowledge"),
        "training": str(STORAGE_DIR / "training"),
        "conversation": str(STORAGE_DIR / "conversation"),
        "cache": str(STORAGE_DIR / "cache"),
    }


DEFAULT_CONFIG: Dict[str, Any] = {
    "version": "2.0",
    "alias": DEFAULT_ALIAS_NAME,
    "tone": "friendly",
    "voice": {
        "tts": False,
        "stt": False,
    },
    "security": {
        "password_enabled": False,
        "password_hash": "",
        "salt": "",
        "encryption_enabled": True,
        "key_seed": "",
    },
    "paths": _default_storage_paths(),
    "profile": {
        "name": "Friend",
        "goal": "journal",
    },
    "memory": {
        "fallback_mode": "apologise",
        "autosave": True,
    },
}


def _merge_dict(base: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in incoming.items():
        if key not in base:
            base[key] = value
            continue
        if isinstance(base[key], dict) and isinstance(value, dict):
            _merge_dict(base[key], value)
        else:
            base[key] = value
    return base


def load_config() -> Dict[str, Any]:
    """Load the Solace configuration, merging it with defaults."""

    config = json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy via serialise
    if CONFIG_PATH.exists():
        try:
            stored = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            stored = {}
        _merge_dict(config, stored)
    return config


def save_config(config: Dict[str, Any]) -> None:
    """Persist ``config`` to disk and ensure storage directories exist."""

    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
    for path in config.get("paths", {}).values():
        Path(path).expanduser().mkdir(parents=True, exist_ok=True)


def ensure_storage_dirs(config: Dict[str, Any]) -> None:
    """Create all storage directories declared inside the configuration."""

    for path in config.get("paths", {}).values():
        Path(path).expanduser().mkdir(parents=True, exist_ok=True)


def _ensure_salt(config: Dict[str, Any]) -> str:
    security = config.setdefault("security", {})
    salt = security.get("salt")
    if not salt:
        salt = os.urandom(32).hex()
        security["salt"] = salt
        save_config(config)
    return salt


def _ensure_key_seed(config: Dict[str, Any]) -> str:
    security = config.setdefault("security", {})
    seed = security.get("key_seed")
    if not seed:
        seed = os.urandom(32).hex()
        security["key_seed"] = seed
        save_config(config)
    return seed


def _derive_key(password: str, salt_hex: str) -> bytes:
    salt = bytes.fromhex(salt_hex)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=390_000,
        backend=default_backend(),
    )
    return base64_urlsafe(kdf.derive(password.encode("utf-8")))


def base64_urlsafe(raw: bytes) -> bytes:
    """Return a urlsafe base64 representation that Fernet expects."""

    import base64

    return base64.urlsafe_b64encode(raw)


def is_password_enabled(config: Dict[str, Any]) -> bool:
    return bool(config.get("security", {}).get("password_enabled"))


def verify_password(config: Dict[str, Any]) -> str | None:
    """Prompt the user for their password if security is enabled."""

    security = config.get("security", {})
    if not security.get("password_enabled"):
        return None
    stored_hash = security.get("password_hash") or ""
    if not stored_hash:
        return None
    for attempt in range(3):
        guess = getpass.getpass("Enter Solace password: ")
        if hashlib.sha256(guess.encode("utf-8")).hexdigest() == stored_hash:
            return guess
        print("Incorrect password. Try again.")
    raise PermissionError("Maximum password attempts exceeded")


def set_password(config: Dict[str, Any]) -> Dict[str, Any]:
    """Interactively ask the user to set or remove a password."""

    security = config.setdefault("security", {})
    choice = input("Protect Solace with a password? (y/n) ").strip().lower()
    if choice not in {"y", "yes"}:
        security["password_enabled"] = False
        security["password_hash"] = ""
        save_config(config)
        return config

    while True:
        pw = getpass.getpass("Choose a password (leave blank to cancel): ")
        if not pw:
            print("Password unchanged.")
            return config
        confirm = getpass.getpass("Confirm password: ")
        if pw != confirm:
            print("Passwords do not match. Try again.")
            continue
        security["password_enabled"] = True
        security["password_hash"] = hashlib.sha256(pw.encode("utf-8")).hexdigest()
        _ensure_salt(config)
        save_config(config)
        print("Password saved.")
        return config


def get_cipher(config: Dict[str, Any], password: str | None = None) -> Fernet:
    """Return a Fernet instance based on the user password settings."""

    security = config.get("security", {})
    if not security.get("encryption_enabled", True):
        raise ValueError("Encryption disabled in config")
    if security.get("password_enabled"):
        if password is None:
            password = verify_password(config)
        if password is None:
            raise PermissionError("Password required but not provided")
    else:
        password = _ensure_key_seed(config)
    salt = _ensure_salt(config)
    key = _derive_key(password, salt)
    return Fernet(key)


def toggle_voice(config: Dict[str, Any], *, tts: bool | None = None, stt: bool | None = None) -> Dict[str, Any]:
    voice = config.setdefault("voice", {})
    if tts is not None:
        voice["tts"] = bool(tts)
    if stt is not None:
        voice["stt"] = bool(stt)
    save_config(config)
    return config


def update_tone(config: Dict[str, Any], tone: str) -> Dict[str, Any]:
    config["tone"] = tone
    save_config(config)
    return config


def update_alias(config: Dict[str, Any], alias: str) -> Dict[str, Any]:
    config["alias"] = alias
    save_config(config)
    return config


def get_storage_path(config: Dict[str, Any], key: str) -> Path:
    return Path(config.get("paths", {}).get(key, STORAGE_DIR / key)).expanduser()


def list_known_paths(config: Dict[str, Any]) -> Iterable[Path]:
    for value in config.get("paths", {}).values():
        yield Path(value).expanduser()


__all__ = [
    "CONFIG_PATH",
    "DEFAULT_CONFIG",
    "STORAGE_DIR",
    "load_config",
    "save_config",
    "ensure_storage_dirs",
    "verify_password",
    "set_password",
    "get_cipher",
    "toggle_voice",
    "update_tone",
    "update_alias",
    "get_storage_path",
    "list_known_paths",
    "is_password_enabled",
]

