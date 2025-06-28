#!/usr/bin/env python3
"""Cross-platform launcher setup for Solace."""
from __future__ import annotations

import os
import platform
import shutil
import sys
from pathlib import Path


def find_writable_dir() -> Path:
    """Return a writable directory from PATH or create one in the user's home."""
    paths = os.environ.get("PATH", "").split(os.pathsep)
    for p in paths:
        path = Path(p)
        if path.is_dir() and os.access(str(path), os.W_OK):
            return path
    home = Path.home()
    if platform.system() == "Windows":
        target = home / "bin"
    else:
        target = home / ".local" / "bin"
    target.mkdir(parents=True, exist_ok=True)
    return target


def install_posix(script_dir: Path, bin_dir: Path) -> None:
    target = bin_dir / "solace"
    source = script_dir / "solace.sh"
    if target.exists():
        try:
            if target.resolve() == source.resolve():
                print(f"solace command already installed at {target}")
                return
        except Exception:
            pass
        ans = input("solace command exists. Replace it? [y/N] ")
        if ans.lower() != "y":
            return
        try:
            target.unlink()
        except OSError:
            pass
    try:
        rel = os.path.relpath(source, bin_dir)
        target.symlink_to(rel)
        print(f"Symlinked launcher to {target}")
    except OSError:
        shutil.copy2(source, target)
        print(f"Copied launcher to {target}")
    target.chmod(0o755)


def install_windows(script_dir: Path, bin_dir: Path) -> None:
    for name in ("solace.cmd", "solace.ps1"):
        source = script_dir / name
        target = bin_dir / name
        if target.exists():
            try:
                if target.resolve() == source.resolve():
                    print(f"{name} already installed at {target}")
                    continue
            except Exception:
                pass
            ans = input(f"{name} exists. Replace it? [y/N] ")
            if ans.lower() != "y":
                continue
            try:
                target.unlink()
            except OSError:
                pass
        shutil.copy2(source, target)
        print(f"Installed {target}")


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    bin_dir = find_writable_dir()
    system = platform.system()
    if system == "Windows":
        install_windows(script_dir, bin_dir)
    else:
        install_posix(script_dir, bin_dir)
    if str(bin_dir) not in os.environ.get("PATH", ""):
        print(f"Warning: {bin_dir} is not on your PATH.")
        print("Add it to your shell configuration or create a manual alias pointing to" \
              f" {script_dir/'solace.sh'}")
    else:
        print(f"Launcher installed in {bin_dir}")
    print("Installation complete. Relaunch your shell to use 'solace'.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error setting up CLI: {exc}", file=sys.stderr)
        sys.exit(1)

