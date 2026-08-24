# Termux Setup

The main installer handles Termux dependencies automatically. If you prefer
to set things up manually run:

```bash
pkg update -y
pkg install -y python git espeak portaudio ffmpeg
```

After that run `bash setup/install.sh` from the project directory.

## Optional Termux Toolkit connection

Solace automatically detects Termux Toolkit when `ttk help` works in the same
terminal. No toolkit path needs to be added to Solace's configuration.

Inside Solace, check the connection with:

```text
/toolkit status
/toolkit list
```

Use `/toolkit man files move-files` to read a manual or
`/toolkit run move-files --help` to invoke a toolkit command. Solace calls the
public `ttk` interface and does not access toolkit internals directly.
