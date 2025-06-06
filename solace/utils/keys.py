from pathlib import Path
from .encryption import load_key

KEY_FILE = Path(__file__).resolve().parents[2] / 'storage' / '.key'


def get_key() -> bytes:
    """Return the Fernet key, generating it if necessary."""
    return load_key(KEY_FILE)
