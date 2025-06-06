import json
from pathlib import Path

CONFIG_FILE = Path(__file__).resolve().parents[1] / 'storage' / 'config.json'

DEFAULT_CONFIG = {
    "name": "",
    "pronouns": "",
    "default_mode": "diary",
    "voice": False,
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


SETTINGS = load_settings()

# voice toggle
ENABLE_TTS = SETTINGS.get("voice", False)

# new toggles for manual timestamp prompts and tagging features
ENABLE_TIMESTAMP_REQUEST = True
ENABLE_TAGGING = True

# default start mode
DEFAULT_MODE = SETTINGS.get("default_mode", "diary")

