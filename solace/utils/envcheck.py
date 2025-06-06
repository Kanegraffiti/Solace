import importlib.util
import ctypes.util
import shutil


def check_voice_dependencies() -> None:
    """Warn about missing optional voice dependencies."""
    modules = [
        "pyttsx3",
        "sounddevice",
        "speechrecognition",
        "pocketsphinx",
    ]
    missing = [m for m in modules if importlib.util.find_spec(m) is None]
    if missing:
        print("Missing voice modules: " + ", ".join(missing))
    lib_missing = []
    if ctypes.util.find_library("portaudio") is None:
        lib_missing.append("portaudio")
    if shutil.which("espeak") is None and shutil.which("espeak-ng") is None:
        lib_missing.append("espeak")
    if ctypes.util.find_library("asound") is None:
        lib_missing.append("alsa")
    if lib_missing:
        print("Warning: missing system libraries: " + ", ".join(lib_missing))

