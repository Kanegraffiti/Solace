# Solace

Solace is a calm command line companion for keeping a private diary and small knowledge base. It runs entirely offline so your thoughts stay on your device. The tool is aimed at neurodivergent users, journalers and anyone who prefers a minimal interface without online distractions.

## Why Solace?

* **Privacy first** – every entry and note lives locally and can be encrypted with a personal key.
* **Low resource** – works on Linux and Android (Termux) with minimal dependencies.
* **Familiar writing style** – after several diary entries Solace can imitate your tone for short chats.
* **Flexible storage** – save diary pages, markdown notes and coding snippets in one place.
* **Optional voice mode** – text to speech and basic speech recognition are supported when the required packages are installed. Extra packages for voice features can be found in `requirements-extra.txt`.
* **Customizable settings** – adjust themes, autosave and encryption with `/mode settings`, including optional password lock.

## Installation

1. Clone this repository and enter the folder:
   ```bash
   git clone <repo-url>
   cd Solace
   ```
   On Termux you may need to install some additional system packages first:
   ```bash
   pkg install -y python git espeak portaudio ffmpeg
   ```
   (You can run `bash termux-setup.sh` to automate the above.)
   On Debian/Ubuntu based Linux systems you can use:
   ```bash
   sudo apt-get install -y python3 python3-pip espeak portaudio19-dev ffmpeg
   ```
   (Automated script: `bash linux-setup.sh`)
2. Install the Python dependencies (use the helper script for a resilient install):
   ```bash
   bash install-safe.sh
   bash solace/nltk-install.sh
   ```
   Optional packages for voice features are listed in `requirements-extra.txt`.
3. Run the program:
   ```bash
   python main.py
   ```
4. Type `/help` inside Solace to see all commands.
5. Run `/mode settings` to customise Solace preferences at any time. See
   [docs/settings.md](docs/settings.md) for details on each option and how to
   reset the password if you ever forget it.

Use `/unlock <file>` to read encrypted diary entries from the command line.
Detailed usage instructions are available in [docs/user_guide.md](docs/user_guide.md).

## Project Structure
```text
solace/
  main.py             # command loop and startup logic
  commands.py         # command handlers
  modes/              # diary, teaching and chat modes
  logic/              # diary storage, notes, code examples, helpers
  utils/              # encryption, voice and file utilities
  models/             # optional speech model data
storage/              # created at runtime for your entries and notes
```

See [docs/developer_guide.md](docs/developer_guide.md) for more information on contributing or extending the project.

Solace is intentionally minimal. Some features from the broader project plan—such as image attachments and advanced pattern tracking—are not implemented yet. Pull requests are welcome!

Additional setup help is provided in [docs/termux_setup.md](docs/termux_setup.md) and [docs/linux_setup.md](docs/linux_setup.md).

