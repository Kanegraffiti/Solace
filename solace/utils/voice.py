import platform
import importlib

VOICE_RECOGNITION_AVAILABLE = True

try:
    pyttsx3 = importlib.import_module('pyttsx3')
except Exception:  # noqa: PIE786
    pyttsx3 = None


try:
    sd = importlib.import_module('sounddevice')
except Exception:  # noqa: PIE786
    sd = None
    VOICE_RECOGNITION_AVAILABLE = False

try:
    sr = importlib.import_module('speech_recognition')
except Exception:  # noqa: PIE786
    sr = None
    VOICE_RECOGNITION_AVAILABLE = False

try:
    import pyaudio  # noqa: F401
except Exception:  # noqa: PIE786
    VOICE_RECOGNITION_AVAILABLE = False

try:
    import pocketsphinx  # noqa: F401
except Exception:  # noqa: PIE786
    VOICE_RECOGNITION_AVAILABLE = False


def missing_packages() -> list[str]:
    """Return a list of required voice packages that are not installed."""
    missing = []
    if pyttsx3 is None:
        missing.append("pyttsx3")
    if sd is None:
        missing.append("sounddevice")
    if sr is None:
        missing.append("speechrecognition")
    try:
        import pocketsphinx  # noqa: F401
    except Exception:
        missing.append("pocketsphinx")
    return missing


def print_missing_packages() -> None:
    """Print a helpful message about missing voice packages."""
    miss = missing_packages()
    if miss:
        print("Missing voice packages: " + ", ".join(miss))
        print("Run /install voice to install them.")

from ..config import VOICE_MODE_ENABLED


_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        if pyttsx3 is None:
            raise RuntimeError('pyttsx3 is not available')
        driver = 'sapi5' if platform.system() == 'Windows' else 'espeak'
        _engine = pyttsx3.init(driverName=driver)
    return _engine


def speak_text(text: str) -> None:
    """Speak the given text using pyttsx3 if available."""
    if not VOICE_MODE_ENABLED:
        return
    if pyttsx3 is None:
        print("pyttsx3 is missing. Install voice packages with /install voice.")
        return
    try:
        engine = _get_engine()
        engine.say(text)
        engine.runAndWait()
    except Exception:  # noqa: BLE001
        print("Unable to speak. Please check TTS dependencies.")


# backward compatibility
speak = speak_text


def recognize_speech(duration: int = 5) -> str | None:
    """Listen from microphone and return recognized text using PocketSphinx."""
    if not VOICE_MODE_ENABLED or not VOICE_RECOGNITION_AVAILABLE:
        print("Voice recognition is not available on this system.")
        return None
    if sd is None or sr is None:
        print("Missing speech packages. Install with /install voice.")
        return None
    samplerate = 16000
    try:
        recording = sd.rec(int(duration * samplerate), samplerate=samplerate,
                           channels=1, dtype='int16')
        sd.wait()
        recognizer = sr.Recognizer()
        audio_data = sr.AudioData(recording.tobytes(), samplerate, 2)
        return recognizer.recognize_sphinx(audio_data)
    except sr.UnknownValueError:
        return ''
    except Exception as e:  # noqa: BLE001
        print(f"Speech recognition error: {e}")
        return None


