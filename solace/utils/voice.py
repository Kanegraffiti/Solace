import json
import platform
from pathlib import Path

try:
    import pyttsx3  # optional text to speech
except Exception:  # noqa: PIE786
    pyttsx3 = None

try:
    import sounddevice as sd  # optional microphone access
except Exception:  # noqa: PIE786
    sd = None

try:
    import vosk  # optional speech recognition
except Exception:  # noqa: PIE786
    vosk = None

import queue
import time

from ..config import ENABLE_TTS


_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        if pyttsx3 is None:
            raise RuntimeError('pyttsx3 is not available')
        driver = 'sapi5' if platform.system() == 'Windows' else 'espeak'
        _engine = pyttsx3.init(driverName=driver)
    return _engine


def speak(text: str):
    """Speak the given text using pyttsx3 if enabled."""
    if not ENABLE_TTS or pyttsx3 is None:
        return
    engine = _get_engine()
    engine.say(text)
    engine.runAndWait()


def recognize_speech(duration: int = 5) -> str:
    """Listen from microphone and return recognized text using Vosk."""
    if sd is None or vosk is None:
        raise RuntimeError('Speech recognition dependencies not available')
    model_dir = Path(__file__).resolve().parents[1] / 'models' / 'vosk-model-small-en-us-0.15'
    if not model_dir.exists():
        raise FileNotFoundError(f"Vosk model not found in {model_dir}")

    model = vosk.Model(str(model_dir))
    samplerate = 16000
    rec = vosk.KaldiRecognizer(model, samplerate)
    q = queue.Queue()

    def callback(indata, frames, time_info, status):
        q.put(bytes(indata))

    with sd.RawInputStream(samplerate=samplerate, blocksize=8000, dtype='int16',
                           channels=1, callback=callback):
        start = time.time()
        while time.time() - start < duration:
            data = q.get()
            if rec.AcceptWaveform(data):
                break
    result = json.loads(rec.FinalResult())
    return result.get('text', '')
