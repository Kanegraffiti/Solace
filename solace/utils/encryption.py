from pathlib import Path
from cryptography.fernet import Fernet


def load_key(path: Path) -> bytes:
    """Load a Fernet key from ``path`` or generate one if missing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        key = Fernet.generate_key()
        path.write_bytes(key)
        return key
    return path.read_bytes()


def encrypt_bytes(data: bytes, key: bytes) -> bytes:
    return Fernet(key).encrypt(data)


def decrypt_bytes(data: bytes, key: bytes) -> bytes:
    return Fernet(key).decrypt(data)
