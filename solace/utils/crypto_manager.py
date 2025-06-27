"""High level encryption helpers using Fernet with PBKDF2."""

from __future__ import annotations

import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from ..settings_manager import SETTINGS


def generate_key(password: str, salt: str) -> bytes:
    """Derive a Fernet key from ``password`` and ``salt``."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=base64.b64decode(salt),
        iterations=390000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


def encrypt_data(data: str, password: str) -> str:
    salt = SETTINGS.get("salt")
    if not salt:
        raise ValueError("Encryption salt is not configured")
    key = generate_key(password, salt)
    return Fernet(key).encrypt(data.encode("utf-8")).decode("utf-8")


def decrypt_data(encrypted: str, password: str) -> str:
    salt = SETTINGS.get("salt")
    if not salt:
        raise ValueError("Encryption salt is not configured")
    key = generate_key(password, salt)
    return Fernet(key).decrypt(encrypted.encode("utf-8")).decode("utf-8")
