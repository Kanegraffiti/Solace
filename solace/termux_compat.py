"""Runtime compatibility helpers for native Python modules in Termux.

Current Termux/Python builds can load extension modules whose unresolved CPython
symbols are not visible through the Android dynamic linker. ``cryptography``'s
Rust extension is one affected module.

The least invasive workaround is to promote the already-installed active
``libpython`` into the process-wide loader namespace with ``RTLD_GLOBAL`` before
cryptography is imported. This leaves Termux's own ``libtermux-exec`` preload
untouched. If Android still refuses the import, a bounded re-exec fallback tries
the libpython-first preload arrangement documented to work in Termux reports.
"""

from __future__ import annotations

import ctypes
import importlib
import os
import sys
import sysconfig
from pathlib import Path
from typing import Mapping, Optional

_REEXEC_MODE = "SOLACE_TERMUX_LIBPYTHON_MODE"
_ORIGINAL_PRELOAD = "SOLACE_TERMUX_ORIGINAL_LD_PRELOAD"


def is_termux(env: Optional[Mapping[str, str]] = None) -> bool:
    values = os.environ if env is None else env
    prefix = values.get("PREFIX", "")
    return bool(values.get("TERMUX_VERSION")) or "com.termux" in prefix


def active_libpython() -> Optional[Path]:
    """Return the shared library for the running CPython interpreter, if found."""

    libdir = sysconfig.get_config_var("LIBDIR")
    library = sysconfig.get_config_var("LDLIBRARY")
    if not libdir or not library:
        return None
    path = Path(str(libdir)) / str(library)
    return path if path.is_file() else None


def merge_preload(libpython: str, existing: str, *, prepend: bool = False) -> str:
    """Add libpython to a colon-delimited preload list without duplicates."""

    parts = [part for part in existing.split(":") if part]
    if libpython in parts:
        return ":".join(parts)
    if prepend:
        parts.insert(0, libpython)
    else:
        parts.append(libpython)
    return ":".join(parts)


def load_libpython_global(libpython: Optional[Path] = None) -> Optional[Path]:
    """Make CPython symbols globally visible without changing ``LD_PRELOAD``.

    Python exposes the platform-correct ``RTLD_GLOBAL`` value through ctypes;
    that matters on Android because its dynamic-linker flag values differ from
    glibc Linux.
    """

    path = active_libpython() if libpython is None else libpython
    if path is None:
        return None
    ctypes.CDLL(str(path), mode=ctypes.RTLD_GLOBAL)
    return path


def _cryptography_probe() -> None:
    importlib.import_module("cryptography.hazmat.bindings._rust")


def _restore_original_preload() -> None:
    original = os.environ.pop(_ORIGINAL_PRELOAD, None)
    os.environ.pop(_REEXEC_MODE, None)
    if original is None:
        return
    if original:
        os.environ["LD_PRELOAD"] = original
    else:
        os.environ.pop("LD_PRELOAD", None)


def _reexec_argv() -> list[str]:
    """Return a reproducible argv for file-based Solace entry points."""

    if not sys.argv or sys.argv[0] in {"", "-", "-c"}:
        raise RuntimeError(
            "The Termux libpython fallback needs a file-based Python entry point; "
            "it cannot safely reproduce `python -c` or stdin code after re-exec."
        )
    return [sys.executable, *sys.argv]


def _reexec_with_preload(libpython: Path, existing: str, mode: str) -> None:
    env = os.environ.copy()
    env.setdefault(_ORIGINAL_PRELOAD, existing)
    env[_REEXEC_MODE] = mode
    if mode == "prepend":
        env["LD_PRELOAD"] = merge_preload(str(libpython), existing, prepend=True)
    elif mode == "libpython-only":
        env["LD_PRELOAD"] = str(libpython)
    else:
        raise ValueError(f"Unknown Termux preload mode: {mode}")
    os.execve(sys.executable, _reexec_argv(), env)


def ensure_termux_cryptography_compatible() -> None:
    """Prepare the Termux process so cryptography's native module can import.

    Order of operations:

    1. If cryptography already imports, make no changes.
    2. Promote the active libpython with ``ctypes.CDLL(..., RTLD_GLOBAL)``.
    3. If needed, re-exec once with libpython before the existing Termux preload.
    4. As a final fallback, re-exec with only libpython, matching the published
       Termux workaround, then restore the original LD_PRELOAD for child
       processes after startup.

    The fallback is bounded by ``SOLACE_TERMUX_LIBPYTHON_MODE`` so it cannot
    loop indefinitely.
    """

    if not is_termux():
        return

    mode = os.environ.get(_REEXEC_MODE, "")
    try:
        _cryptography_probe()
    except ModuleNotFoundError as exc:
        if exc.name and exc.name.startswith("cryptography"):
            return
        raise
    except ImportError as initial_error:
        libpython = active_libpython()
        if libpython is None:
            raise RuntimeError(
                "Termux cryptography import failed and Solace could not locate the active libpython. "
                f"Original error: {initial_error}"
            ) from initial_error

        if not mode:
            try:
                load_libpython_global(libpython)
                _cryptography_probe()
            except (ImportError, OSError) as global_error:
                existing = os.environ.get("LD_PRELOAD", "")
                try:
                    _reexec_with_preload(libpython, existing, "prepend")
                except (OSError, RuntimeError) as exec_error:
                    raise RuntimeError(
                        "Termux cryptography import failed after RTLD_GLOBAL and Solace could not "
                        "re-exec with the libpython preload. "
                        f"Import error: {global_error}; re-exec error: {exec_error}"
                    ) from exec_error
            else:
                return

        existing = os.environ.get(_ORIGINAL_PRELOAD, os.environ.get("LD_PRELOAD", ""))
        if mode == "prepend":
            try:
                _reexec_with_preload(libpython, existing, "libpython-only")
            except (OSError, RuntimeError) as exec_error:
                raise RuntimeError(
                    "Termux cryptography import still failed with libpython first in LD_PRELOAD, "
                    f"and the final fallback could not start: {exec_error}. Original import: {initial_error}"
                ) from exec_error

        raise RuntimeError(
            "Termux cryptography still cannot import after RTLD_GLOBAL, a libpython-first preload, "
            "and the documented libpython-only preload fallback. "
            f"Final import error: {initial_error}"
        ) from initial_error
    else:
        if mode:
            _restore_original_preload()


# Backward-compatible name for callers on older Solace branches.
def ensure_termux_libpython_preloaded() -> None:
    ensure_termux_cryptography_compatible()


def _self_check() -> None:
    ensure_termux_cryptography_compatible()
    from cryptography.fernet import Fernet  # noqa: F401

    print("Termux cryptography compatibility check passed.")


if __name__ == "__main__":
    _self_check()


__all__ = [
    "active_libpython",
    "ensure_termux_cryptography_compatible",
    "ensure_termux_libpython_preloaded",
    "is_termux",
    "load_libpython_global",
    "merge_preload",
]
