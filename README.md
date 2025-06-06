# Solace

Solace is a lightweight offline companion that runs entirely in your terminal. It stores diary entries, personal notes and small coding facts on your local machine. No internet connection or AI services are required.

## Features
- **Diary mode** – save text entries with simple mood detection.
- **Teaching mode** – store facts or code snippets for later reference.
- **Chat mode** – after ten diary entries Solace can mimic your writing style for short conversations.
- **Import** – pull notes from `.txt`, `.md`, `.rst`, `.pdf` or `.epub` files into the fact store (PDF/EPUB support requires optional packages).
- **Voice** – optional text‑to‑speech and speech recognition if the necessary libraries are available.
- **Private entries** – diary and knowledge items can be encrypted with a local key.
- **Memory tracker** – `/remember` and `/forget` manage personal reminders.
- **Function reference** – `/func` shows arguments and docs for known functions.
- **Summary** – `/summary` shows how much you have taught Solace.
- **Fallback log** – unanswered questions are stored for later review.

## Requirements
- Python 3.10 or newer
- `pip` for installing dependencies
- On Termux: package manager (`pkg`) for system libraries

Voice features rely on `pyttsx3`, `sounddevice` and `vosk`. These require system audio libraries such as `espeak` and `portaudio`. If they are missing, Solace will still run but `/speak` and `/listen` commands will be disabled.

## Quick start
1. Clone this repository and change into the folder:
   ```bash
   git clone <repo-url>
   cd Solace
   ```
2. Install the Python dependencies:
   ```bash
   pip install -r requirements.txt
   bash solace/nltk-install.sh
   ```
3. The first private entry will generate `storage/keys/key.key`. Back this file up if you plan to encrypt notes.
4. (Optional) Download a Vosk English model from [alphacephei.com/vosk/models](https://alphacephei.com/vosk/models) and extract it into `solace/models/` so that the path looks like `solace/models/vosk-model-small-en-us-0.15`.
5. Run the program:
   ```bash
   python main.py
   ```
6. Type `/help` inside the program to see the available commands.
7. Use `import_openbooks.py <file> <language>` to bulk add example code from cleaned tutorials.

### Running on Termux (Android)
1. Install Python: `pkg install python`.
2. Optionally install audio packages for voice features: `pkg install espeak ffmpeg portaudio`.
3. Follow the **Quick start** steps above inside your Termux session.

### Running on Git Bash (Windows)
1. Install Python from [python.org](https://www.python.org/downloads/) and ensure `python` and `pip` are in your `PATH`.
2. Open Git Bash and follow the **Quick start** steps.
3. Voice features work with the default Windows speech API if the optional dependencies are installed.

## Project structure
```
solace/
  main.py             # command loop and command handling
  modes/              # diary, teaching and chat mode implementations
  logic/              # helper modules for coding, import, conversation, etc.
  utils/              # storage, file tools and optional voice utilities
  models/             # place Vosk speech model here (optional)
```
All saved data lives in the `data/` directory as simple JSON files so you can back them up or edit them manually.

Solace is intentionally minimal. It is designed for local, private note keeping and experiments with simple text processing.
