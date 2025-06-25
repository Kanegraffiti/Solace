# Solace Settings

Solace stores user preferences in `settings/settings.json`. The settings are loaded on startup so changes take effect the next time you run the program.

Run `/mode settings` from inside Solace to open an interactive configuration menu. You can toggle options with `y`/`n`, pick values from a list or type text.

Available options:

- **Theme** – choose between `light` and `dark` display styles.
- **Autosave** – automatically save diary entries without confirmation.
- **Typing effect** – print responses character by character.
- **Default mode** – initial mode when Solace starts (`diary`, `chat` or `code`).
- **Encryption** – enable encryption for new entries by default.
- **Allow plugins** – permit loading third‑party plugin modules.
- **Mimic persona** – speaker name for imitation mode.
- **Password lock** – require a password when starting Solace. The password is hashed before being stored. A hint can be saved to help you remember it.

If you forget the password you can remove `settings/settings.json` to reset all preferences.

