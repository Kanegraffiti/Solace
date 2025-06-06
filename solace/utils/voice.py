import platform

try:
    import pyttsx3  # optional text to speech
except Exception:  # noqa: PIE786
    pyttsx3 = None

try:
    import sounddevice as sd  # optional microphone access
except Exception:  # noqa: PIE786
    sd = None

try:
    import speech_recognition as sr  # optional speech recognition
except Exception:  # noqa: PIE786
    sr = None

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
    """Listen from microphone and return recognized text using PocketSphinx."""
    if sd is None or sr is None:
        raise RuntimeError('Speech recognition dependencies not available')
    samplerate = 16000
    recording = sd.rec(int(duration * samplerate), samplerate=samplerate,
                       channels=1, dtype='int16')
    sd.wait()
    recognizer = sr.Recognizer()
    audio_data = sr.AudioData(recording.tobytes(), samplerate, 2)
    try:
        return recognizer.recognize_sphinx(audio_data)
    except sr.UnknownValueError:
        return ''
    except sr.RequestError as e:
        raise RuntimeError(f'Speech recognition error: {e}')
