"""Unified installer for Solace.

The script merges the previous assortment of platform specific snippets into a
single offline friendly workflow.  The installer performs the following
operations:

* Detect the host environment (Termux, standard Linux, macOS, Windows Git Bash)
* Install Python dependencies from ``requirements.txt``
* Create a launcher script or alias named ``solace`` that dispatches to the
  local repository
* Set up the ``~/.solaceconfig.json`` file and prompt for optional password
* Provide clear fallbacks when automation is not possible
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable

from solace.configuration import (
    CONFIG_PATH,
    DEFAULT_ALIAS_NAME,
    DEFAULT_CONFIG,
    ensure_storage_dirs,
    load_config,
    save_config,
    set_password,
)


PROJECT_ROOT = Path(__file__).resolve().parent


def _detect_environment() -> str:
    system = platform.system().lower()
    if "microsoft" in platform.platform().lower() or system == "windows":
        return "windows"
    if "darwin" in system:
        return "macos"
    if "linux" in system:
        # Termux sets an environment variable
        if os.getenv("TERMUX_VERSION"):
            return "termux"
        return "linux"
    return "unknown"


def _pip_install(requirements: Iterable[Path]) -> None:
    python = sys.executable or shutil.which("python3") or "python3"
    for req in requirements:
        if not req.exists():
            continue
        print(f"Installing dependencies from {req} ...")
        subprocess.check_call([python, "-m", "pip", "install", "-r", str(req)])


def _launcher_dir() -> Path:
    if os.name == "nt":
        return Path.home() / "AppData" / "Local" / "solace"
    return Path.home() / ".local" / "bin"


def _create_launcher(env_name: str, alias: str) -> Path | None:
    bin_dir = _launcher_dir()
    try:
        bin_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:  # noqa: PERF203 - small function
        print(f"Could not create launcher directory {bin_dir}: {exc}")
        return None

    python_exe = sys.executable or shutil.which("python3") or "python3"
    target = PROJECT_ROOT / "main.py"

    if os.name == "nt":
        launcher = bin_dir / f"{alias}.bat"
        launcher.write_text(f'@echo off\n"{python_exe}" "{target}" %*\n', encoding="utf-8")
        return launcher

    launcher = bin_dir / alias
    launcher.write_text(
        "#!/usr/bin/env bash\n"
        "SCRIPT=\"" + str(target) + "\"\n"
        "PY=\"${PYTHON:-" + python_exe + "}\"\n"
        "exec \"$PY\" \"$SCRIPT\" \"$@\"\n",
        encoding="utf-8",
    )
    launcher.chmod(0o755)
    return launcher


def _ensure_alias(alias: str, env_name: str) -> None:
    launcher = _create_launcher(env_name, alias)
    if launcher is None:
        print("Falling back to manual launch: run `python main.py`")
        return
    path_env = os.getenv("PATH", "")
    if str(launcher.parent) not in path_env.split(os.pathsep):
        shell_rc_candidates = [
            Path.home() / ".bashrc",
            Path.home() / ".zshrc",
            Path.home() / ".profile",
        ]
        export_line = f"export PATH=\"{launcher.parent}:${{PATH}}\"\n"
        for candidate in shell_rc_candidates:
            try:
                with candidate.open("a", encoding="utf-8") as handle:
                    handle.write(f"\n# Added by Solace installer\n{export_line}")
                print(f"Updated {candidate} to include launcher directory.")
                break
            except OSError:
                continue
        else:
            print(
                "Please add "
                f"{launcher.parent} to your PATH manually to use the `{alias}` command."
            )
    print(f"Launcher available: {launcher}")


def _initialise_config(alias: str) -> None:
    if CONFIG_PATH.exists():
        config = load_config()
    else:
        config = json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy
    profile = config.setdefault("profile", {})
    if not profile.get("name"):
        profile["name"] = input("What should Solace call you? [Friend] ") or "Friend"
    if not profile.get("goal"):
        profile["goal"] = input("What do you want to focus on? [journal] ") or "journal"
    config["alias"] = alias
    save_config(config)
    ensure_storage_dirs(config)
    set_password(config)


def main() -> None:
    parser = argparse.ArgumentParser(description="Install Solace in the current environment")
    parser.add_argument("--alias", default=DEFAULT_ALIAS_NAME, help="Command name to use (default: solace)")
    parser.add_argument(
        "--skip-deps", action="store_true", help="Skip dependency installation"
    )
    args = parser.parse_args()

    env_name = _detect_environment()
    print(f"Detected environment: {env_name}")
    if env_name == "unknown":
        print("Proceeding with generic installation steps. Some features may require manual setup.")

    if not args.skip_deps:
        requirements = [PROJECT_ROOT / "requirements.txt", PROJECT_ROOT / "requirements-extra.txt"]
        _pip_install(requirements)
    else:
        print("Skipping dependency installation per --skip-deps")

    _ensure_alias(args.alias, env_name)
    _initialise_config(args.alias)
    print("Solace installation complete. Run `solace` to start your assistant.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Installation aborted by user.")
        sys.exit(1)
    except subprocess.CalledProcessError as exc:
        print(f"A command failed: {exc}")
        sys.exit(exc.returncode or 1)
