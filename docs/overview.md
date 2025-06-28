# Solace Overview

Solace is a lightweight command line diary and knowledge assistant. It was designed with privacy in mind so all data lives locally on your device. The project is aimed at neurodivergent users and anyone who wants an offline place to collect their thoughts.

The application supports three main modes:

- **Diary mode** – capture daily entries and tag them with optional moods or keywords.
- **Teaching mode** – store facts, code snippets or reference material for quick lookup.
- **Chat mode** – once enough diary text has been collected Solace can imitate your writing style for short conversations.

Data is stored as simple JSON files and text documents inside the `storage/` folder. Sensitive items can be encrypted with a local key. No internet connection is required after installation.

Solace includes an interactive settings menu accessible with `/mode settings`. Here you can toggle themes, autosave, encryption and even set a password lock for the app. See [settings.md](settings.md) for a complete list of options.

The installer creates a `solace` command that works on Linux, Windows and Termux so you can launch the assistant from any terminal. Enabling `allow_plugins` lets you extend Solace with custom commands stored in `solace/plugins`.
