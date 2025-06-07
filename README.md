# Solace

Solace is a calm command line companion for keeping a private diary and small knowledge base. It runs entirely offline so your thoughts stay on your device. The tool is aimed at neurodivergent users, journalers and anyone who prefers a minimal interface without online distractions.

## Why Solace?

* **Privacy first** – every entry and note lives locally and can be encrypted with a personal key.
* **Low resource** – works on Linux and Android (Termux) with minimal dependencies.
* **Familiar writing style** – after several diary entries Solace can imitate your tone for short chats.
* **Flexible storage** – save diary pages, markdown notes and coding snippets in one place.
* **Optional voice mode** – text to speech and basic speech recognition are supported when the required packages are installed.

## Installation

1. Clone this repository and enter the folder:
   ```bash
   git clone <repo-url>
   cd Solace
   ```
2. Install the Python dependencies:
   ```bash
   pip install -r requirements.txt
   bash solace/nltk-install.sh
   ```
3. Run the program:
   ```bash
   python main.py
   ```
4. Type `/help` inside Solace to see all commands.

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

