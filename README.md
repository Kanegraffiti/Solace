<p align="center">
  <img src="assets/banner.png" alt="Solace banner" style="width:100%;max-width:100%;height:auto;" />
</p>

# Solace

Solace is a calm command line companion for journaling, note taking and managing a small knowledge base. Everything runs offline so your private thoughts stay on your device. The tool is designed for neurodivergent users, journalers and anyone who wants a distraction free interface.

## Key Features

* **Privacy first** – diary entries and notes live locally and can be secured with password-based encryption.
* **Low resource** – works on Linux and Android (Termux) with minimal dependencies.
* **Flexible storage** – save diary pages, markdown notes, code snippets and short facts in one place.
* **Knowledge graph** – a lightweight graph keeps track of entities you mention in chats.
* **Search everything** – quickly find past entries, notes or facts with the `/recall` command.
* **Optional voice mode** – basic text to speech and speech recognition are supported when extra packages are installed.
* **Customisable settings** – adjust themes, autosave, encryption and more in `/mode settings`, including an optional password lock.

## Installation

1. Clone this repository and run the installer:
   ```bash
   git clone <repo-url>
   cd Solace
   bash install.sh
   ```
   This creates a virtual environment and installs dependencies with retry logic. The script also sets up a global `solace` command so you can start the program from anywhere.
   On Termux you may need system packages first:
   ```bash
   pkg install -y python git espeak portaudio ffmpeg
   ```
   On Debian/Ubuntu based systems you can use:
   ```bash
   sudo apt-get install -y python3 python3-pip espeak portaudio19-dev ffmpeg
   ```
2. If needed run the NLTK installer for offline speech models:
   ```bash
   bash solace/nltk-install.sh
   ```
3. Launch the application:
   ```bash
   solace
   ```
4. Type `/help` inside Solace to see all commands and `/mode settings` to customise preferences. See [docs/settings.md](docs/settings.md) for details.

Use `/unlock <file>` to decrypt diary entries from the command line. The full user guide lives in [docs/user_guide.md](docs/user_guide.md).

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

See [docs/developer_guide.md](docs/developer_guide.md) for information on contributing or extending the project.

Solace is intentionally minimal. Features like image attachments and advanced pattern tracking are still on the roadmap. Pull requests are welcome!

Additional setup help is available in [docs/termux_setup.md](docs/termux_setup.md) and [docs/linux_setup.md](docs/linux_setup.md).
