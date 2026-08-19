# Termux install notes

Solace uses Termux's packaged `python-cryptography` build instead of compiling
cryptography with pip on Android. The package carries Termux-specific Rust and
linker handling that a generic pip source build does not.

The recommended entry point is:

```bash
bash install.sh
```

The installer creates `.venv` with `--system-site-packages`, installs only the
Termux-safe CLI dependency set from `requirements-termux.txt`, and recreates the
venv when the Termux Python major/minor version changes.

Optional web and voice dependencies are not part of the default Termux core
install because their transitive native builds can be expensive or unsupported
on-device.
