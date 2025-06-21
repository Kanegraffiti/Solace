# Termux Setup

These commands install the system dependencies required for Solace on Termux.
Run them before installing the Python packages.

```bash
pkg update -y
pkg install -y python git espeak portaudio ffmpeg
```

After that run `bash install-safe.sh` from the project directory.

