# Solace Settings

Settings are stored in `~/.solaceconfig.json`. Solace loads them on startup and writes any changes immediately when you use the `/settings` command.

Run `/settings` inside Solace to see the available subcommands. Each option performs a single action:

- **password** – enable or disable the startup password. When enabled you are prompted to supply it each time Solace starts. The password hash, salt and encryption seed are stored in the config.
- **voice** – toggle text-to-speech (`tts`) and speech recognition (`stt`). Additional Python packages are required for these features. Solace reminds you to restart so the engines can be reloaded.
- **tone** – choose between `friendly`, `quiet` or `verbose` responses for `/mimic`.
- **alias** – update the stored launcher name. Re-run `install.py --alias <name>` to regenerate the shell launcher if desired.
- **backup** – create a timestamped ZIP archive of the storage directory and remind you to copy the config file as well.
- **restore <archive>** – unpack a previously created archive into the storage directory. Existing files are overwritten.
- **info** – print the config path, current version and all known storage paths.
- **fallback <mode>** – set the fallback behaviour (`apologise`, `gentle`, `encourage`) used when `/mimic` cannot match a trigger.

Storage directories defined in the config are created automatically. Deleting `~/.solaceconfig.json` resets the application to defaults.
