"""Unified installer for Solace.

The installer detects the host, installs the requested Python dependencies,
creates a real ``solace`` launcher, initialises local configuration, and can
optionally prepare the local Qwen backend on Termux.

Termux uses its packaged ``python-cryptography`` build rather than asking pip to
compile cryptography/maturin on-device. The recommended Termux entry point is
``bash install.sh`` because it also creates a virtual environment with access to
those Android-patched system packages.
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
from typing import Iterable, Optional

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
    prefix = os.getenv("PREFIX", "")
    if os.getenv("TERMUX_VERSION") or "com.termux" in prefix:
        return "termux"
    if "microsoft" in platform.platform().lower() or system == "windows":
        return "windows"
    if "darwin" in system:
        return "macos"
    if "linux" in system:
        return "linux"
    return "unknown"


def _pip_install(requirements: Iterable[Path]) -> None:
    python = sys.executable or shutil.which("python3") or "python3"
    for req in requirements:
        if not req.exists():
            continue
        print(f"Installing dependencies from {req} ...")
        subprocess.check_call([python, "-m", "pip", "install", "-r", str(req)])


def _install_termux_dependencies(*, include_ml: bool = False) -> None:
    """Install the Android-safe Termux dependency set.

    cryptography is provided by the Termux package repository because its build
    includes Android-specific linking fixes. Pip is used only for the lightweight
    CLI dependencies in requirements-termux.txt.
    """

    pkg = shutil.which("pkg")
    if pkg is None:
        raise SystemExit("Termux package manager `pkg` was not found.")

    print("Installing Termux's Android-patched python-cryptography package ...")
    subprocess.check_call([pkg, "install", "-y", "python-cryptography"])

    try:
        from cryptography.fernet import Fernet  # noqa: F401
    except ImportError as exc:
        in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
        if in_venv:
            raise SystemExit(
                "python-cryptography is installed by Termux but this virtual environment "
                "cannot see system packages. Run `bash install.sh` from the Solace repo; "
                "it will safely rebuild the disposable .venv with --system-site-packages."
            ) from exc
        raise SystemExit(
            "Termux python-cryptography could not be imported. Run `pkg upgrade` and retry."
        ) from exc

    requirements = [PROJECT_ROOT / "requirements-termux.txt"]
    if include_ml:
        requirements.append(PROJECT_ROOT / "requirements-ml.txt")
    _pip_install(requirements)
    print("Skipping optional web/voice native stacks during the Termux core install.")


def _launcher_dir(env_name: str) -> Path:
    if env_name == "termux":
        prefix = os.getenv("PREFIX")
        if prefix:
            return Path(prefix) / "bin"
    if os.name == "nt":
        return Path.home() / "AppData" / "Local" / "solace"
    return Path.home() / ".local" / "bin"


def _create_launcher(env_name: str, alias: str) -> Optional[Path]:
    bin_dir = _launcher_dir(env_name)
    try:
        bin_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"Could not create launcher directory {bin_dir}: {exc}")
        return None

    python_exe = sys.executable or shutil.which("python3") or "python3"
    target = PROJECT_ROOT / "solace" / "launcher.py"

    if os.name == "nt":
        launcher = bin_dir / f"{alias}.bat"
        launcher.write_text(f'@echo off\n"{python_exe}" "{target}" %*\n', encoding="utf-8")
        return launcher

    launcher = bin_dir / alias
    launcher.write_text(
        "#!/usr/bin/env bash\n"
        f'exec "{python_exe}" "{target}" "$@"\n',
        encoding="utf-8",
    )
    launcher.chmod(0o755)
    return launcher


def _create_qwen_launcher(env_name: str) -> Optional[Path]:
    if env_name != "termux":
        return None

    bin_dir = _launcher_dir(env_name)
    script = PROJECT_ROOT / "scripts" / "qwen.sh"
    launcher = bin_dir / "qwen"
    try:
        launcher.write_text(
            "#!/data/data/com.termux/files/usr/bin/bash\n"
            f'exec bash "{script}" "$@"\n',
            encoding="utf-8",
        )
        launcher.chmod(0o700)
    except OSError as exc:
        print(f"Could not create Qwen launcher {launcher}: {exc}")
        return None
    return launcher


def _ensure_path(launcher: Path, env_name: str) -> None:
    if env_name == "termux":
        # $PREFIX/bin is part of Termux PATH by default.
        return

    path_env = os.getenv("PATH", "")
    if str(launcher.parent) in path_env.split(os.pathsep):
        return

    shell_rc_candidates = [
        Path.home() / ".bashrc",
        Path.home() / ".zshrc",
        Path.home() / ".profile",
    ]
    export_line = f'export PATH="{launcher.parent}:${{PATH}}"\n'
    for candidate in shell_rc_candidates:
        try:
            with candidate.open("a", encoding="utf-8") as handle:
                handle.write(f"\n# Added by Solace installer\n{export_line}")
            print(f"Updated {candidate} to include launcher directory.")
            return
        except OSError:
            continue
    print(f"Please add {launcher.parent} to PATH manually to use the launcher.")


def _ensure_launchers(alias: str, env_name: str) -> None:
    launcher = _create_launcher(env_name, alias)
    if launcher is None:
        print("Falling back to manual launch: run `python3 solace/launcher.py`")
    else:
        _ensure_path(launcher, env_name)
        print(f"Solace launcher available: {launcher}")

    qwen_launcher = _create_qwen_launcher(env_name)
    if qwen_launcher is not None:
        print(f"Qwen launcher available: {qwen_launcher}")


def _initialise_config(alias: str) -> None:
    if CONFIG_PATH.exists():
        config = load_config()
    else:
        config = json.loads(json.dumps(DEFAULT_CONFIG))

    profile = config.setdefault("profile", {})
    if not profile.get("name"):
        profile["name"] = input("What should Solace call you? [Friend] ") or "Friend"
    if not profile.get("goal"):
        profile["goal"] = input("What do you want to focus on? [journal] ") or "journal"
    config["alias"] = alias
    config.setdefault("ui", {}).setdefault("show_startup_manual", True)
    save_config(config)
    ensure_storage_dirs(config)
    set_password(config)


def _setup_qwen(env_name: str) -> None:
    if env_name != "termux":
        raise SystemExit("--setup-qwen is currently supported only in Termux.")
    helper = PROJECT_ROOT / "scripts" / "setup-qwen-termux.sh"
    subprocess.check_call(["bash", str(helper)])


def main() -> None:
    parser = argparse.ArgumentParser(description="Install Solace in the current environment")
    parser.add_argument("--alias", default=DEFAULT_ALIAS_NAME, help="Command name to use (default: solace)")
    parser.add_argument("--skip-deps", action="store_true", help="Skip dependency installation")
    parser.add_argument(
        "--extras",
        nargs="*",
        choices=["ml"],
        default=[],
        help="Optional extra dependency sets to install (e.g. --extras ml)",
    )
    parser.add_argument(
        "--setup-qwen",
        action="store_true",
        help="On Termux, explicitly build llama.cpp and download/verify the local Qwen model",
    )
    args = parser.parse_args()

    env_name = _detect_environment()
    print(f"Detected environment: {env_name}")
    if env_name == "unknown":
        print("Proceeding with generic installation steps. Some features may require manual setup.")

    if not args.skip_deps:
        if env_name == "termux":
            _install_termux_dependencies(include_ml="ml" in args.extras)
        else:
            requirements = [PROJECT_ROOT / "requirements.txt", PROJECT_ROOT / "requirements-extra.txt"]
            if "ml" in args.extras:
                requirements.append(PROJECT_ROOT / "requirements-ml.txt")
            else:
                print("Skipping ML extras. Use --extras ml to install semantic and summarisation models.")
            _pip_install(requirements)
    else:
        print("Skipping dependency installation per --skip-deps")

    _ensure_launchers(args.alias, env_name)
    _initialise_config(args.alias)

    if args.setup_qwen:
        _setup_qwen(env_name)
    elif env_name == "termux":
        print(
            "Local Qwen is optional. Run `python3 install.py --skip-deps --setup-qwen` "
            "or `bash scripts/setup-qwen-termux.sh` when you want to configure it."
        )

    print(f"Solace installation complete. Run `{args.alias}` to start your assistant.")
    print("The startup mini-manual explains the basics; use `/manual off` to hide it later.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Installation aborted by user.")
        sys.exit(1)
    except subprocess.CalledProcessError as exc:
        print(f"A command failed: {exc}")
        sys.exit(exc.returncode or 1)
