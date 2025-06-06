from __future__ import annotations

from pathlib import Path
from getpass import getpass
from .encryption import encrypt_bytes, decrypt_bytes, load_key

KEY_FILE = Path(__file__).resolve().parents[2] / 'storage' / '.key'


def get_key() -> bytes:
    return load_key(KEY_FILE)


def encrypt_text(text: str, key: bytes | None = None) -> bytes:
    key = key or get_key()
    return encrypt_bytes(text.encode('utf-8'), key)


def decrypt_text(data: bytes, key: bytes | None = None) -> str:
    key = key or get_key()
    return decrypt_bytes(data, key).decode('utf-8')


def password_prompt(prompt: str = 'Password: ') -> str:
    return getpass(prompt)

