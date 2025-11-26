# Solace Settings

Settings are stored in `~/.solaceconfig.json`. Solace loads them on startup and writes any changes immediately when you use the `/settings` command.

Run `/settings` inside Solace to see the available subcommands. Each option performs a single action:

- **password** – enable or disable the startup password. When enabled you are prompted to supply it each time Solace starts. The password hash, salt and encryption seed are stored in the config.
- **voice** – toggle text-to-speech (`tts`) and speech recognition (`stt`). Additional Python packages are required for these features. Solace reminds you to restart so the engines can be reloaded.
- **tone** – choose between `friendly`, `quiet` or `verbose` responses for `/mimic`.
- **alias** – update the stored launcher name. Re-run `install.py --alias <name>` to regenerate the shell launcher if desired.
- **backup** – trigger the same encrypted archive creation as `/backup`. Use `--dry-run` to preview the target path and `--no-restore` to omit the bundled restore point.
- **restore <archive>** – unpack a previously created archive into the storage directory. Existing files are overwritten.
- **info** – print the config path, current version and all known storage paths.
- **fallback <mode>** – set the fallback behaviour (`apologise`, `gentle`, `encourage`) used when `/mimic` cannot match a trigger.

The `sync` block in `~/.solaceconfig.json` controls pluggable backends. Networked backends (S3 or WebDAV) stay disabled by default until you set `enabled` to `true` and provide credentials. Dry-run mode defaults to `true` and must be switched off before real archives are written. Restore points are enabled by default so each archive carries a plain text copy of `entries.json` alongside the encrypted payload.

Storage directories defined in the config are created automatically. Deleting `~/.solaceconfig.json` resets the application to defaults.
