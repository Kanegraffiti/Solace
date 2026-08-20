from pathlib import Path

import pytest

import solace.termux_compat as compat
from solace.termux_compat import is_termux, merge_preload


def test_is_termux_uses_termux_version_or_prefix():
    assert is_termux({"TERMUX_VERSION": "0.118.3", "PREFIX": "/tmp"})
    assert is_termux({"PREFIX": "/data/data/com.termux/files/usr"})
    assert not is_termux({"PREFIX": "/usr/local"})


def test_merge_preload_preserves_termux_exec_order():
    libpython = "/data/data/com.termux/files/usr/lib/libpython3.14.so"
    termux_exec = "/data/data/com.termux/files/usr/lib/libtermux-exec-ld-preload.so"

    merged = merge_preload(libpython, termux_exec)

    assert merged == f"{termux_exec}:{libpython}"


def test_merge_preload_can_put_libpython_first_for_fallback():
    libpython = "/data/data/com.termux/files/usr/lib/libpython3.14.so"
    termux_exec = "/data/data/com.termux/files/usr/lib/libtermux-exec-ld-preload.so"

    merged = merge_preload(libpython, termux_exec, prepend=True)

    assert merged == f"{libpython}:{termux_exec}"


def test_merge_preload_does_not_duplicate_libpython():
    libpython = "/data/data/com.termux/files/usr/lib/libpython3.14.so"
    termux_exec = "/data/data/com.termux/files/usr/lib/libtermux-exec-ld-preload.so"
    existing = f"{termux_exec}:{libpython}"

    assert merge_preload(libpython, existing) == existing


def test_load_libpython_global_uses_platform_rtld_global(monkeypatch):
    calls = []
    libpython = Path("/data/data/com.termux/files/usr/lib/libpython3.14.so")

    def fake_cdll(path, *, mode):
        calls.append((path, mode))
        return object()

    monkeypatch.setattr(compat.ctypes, "CDLL", fake_cdll)

    assert compat.load_libpython_global(libpython) == libpython
    assert calls == [(str(libpython), compat.ctypes.RTLD_GLOBAL)]


def test_reexec_guard_rejects_python_dash_c(monkeypatch):
    monkeypatch.setattr(compat.sys, "argv", ["-c"])

    with pytest.raises(RuntimeError, match="file-based Python entry point"):
        compat._reexec_argv()
