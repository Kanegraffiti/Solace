# Bash Knowledge Schema

All files here are local, static knowledge used by deterministic matching in `solace.logic.bash_intel`.

- `examples.json`: general bash snippets used by legacy lookup fallback.
- `commands.json`: command metadata (`command`, `description`, `common_flags`, `safe_notes`, `examples`).
- `flags.json`: map of flag token to plain-language meaning.
- `patterns.json`: intent-to-command mappings with keywords and optional placeholders.
- `scripts.json`: reusable multi-line scripts (`name`, `script`, `explanation`, `placeholders`, `safety`).
- `topics.json`: concept-level explanations for `/ask bash ...`.
- `errors.json`: deterministic error matching (`patterns`, `cause`, `fix`).
- `safety.json`: risky pattern rules (`pattern`, `severity`, `message`, `safer_alternative`).

These files are intentionally lightweight JSON for low-resource offline systems (including Termux).
