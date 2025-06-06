from .filetools import *
from .storage import *
try:
    from .voice import speak, recognize_speech
    VOICE_AVAILABLE = True
except Exception:  # noqa: PIE786
    VOICE_AVAILABLE = False

    def speak(text: str):  # type: ignore
        """Fallback speak that does nothing when voice is unavailable."""
        return

    def recognize_speech(duration: int = 5) -> str:  # type: ignore
        """Fallback recognizer raising an error when voice is unavailable."""
        raise RuntimeError('Speech recognition not available')
