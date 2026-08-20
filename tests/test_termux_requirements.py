from pathlib import Path


def _dependency_names(path: Path) -> set[str]:
    names = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        names.add(line.split("[", 1)[0].split("=", 1)[0].split("<", 1)[0].split(">", 1)[0].lower())
    return names


def test_termux_core_requirements_avoid_native_crypto_build():
    requirements = Path(__file__).resolve().parents[1] / "requirements-termux.txt"
    names = _dependency_names(requirements)

    assert "cryptography" not in names
    assert {"rich", "textual", "networkx", "nltk", "fpdf"}.issubset(names)


def test_termux_core_requirements_skip_optional_native_stacks():
    requirements = Path(__file__).resolve().parents[1] / "requirements-termux.txt"
    names = _dependency_names(requirements)

    assert "sounddevice" not in names
    assert "speechrecognition" not in names
    assert "pocketsphinx" not in names
    assert "uvicorn" not in names


def test_termux_installer_sets_up_pip_before_cryptography():
    installer = (Path(__file__).resolve().parents[1] / "install.sh").read_text(encoding="utf-8")

    pip_install = installer.index("termux_pkg_install python-pip")
    pip3_check = installer.index("command -v pip3")
    crypto_install = installer.index("termux_pkg_install python-cryptography")

    assert pip_install < pip3_check < crypto_install


def test_termux_installer_repairs_missing_cffi_after_failed_postinst():
    installer = (Path(__file__).resolve().parents[1] / "install.sh").read_text(encoding="utf-8")

    cffi_probe = installer.index("termux_cffi_ready")
    reinstall = installer.index("termux_pkg_reinstall python-cryptography")
    crypto_check = installer.index('info "Checking Termux cryptography runtime compatibility"')

    assert "import _cffi_backend" in installer
    assert "pkg reinstall -y" in installer
    assert cffi_probe < reinstall < crypto_check


def test_termux_installer_avoids_full_mirror_sweep():
    installer = (Path(__file__).resolve().parents[1] / "install.sh").read_text(encoding="utf-8")

    assert "TERMUX_PKG_NO_MIRROR_SELECT=1 pkg install" in installer
    assert "TERMUX_PKG_NO_MIRROR_SELECT=1 pkg reinstall" in installer
    assert "termux-change-repo" in installer


def test_termux_installer_uses_file_based_crypto_compatibility_check():
    root = Path(__file__).resolve().parents[1]
    installer = (root / "install.sh").read_text(encoding="utf-8")
    compatibility = (root / "solace" / "termux_compat.py").read_text(encoding="utf-8")

    assert '"$PROJECT_DIR/solace/termux_compat.py"' in installer
    assert "termux_crypto_check" in installer
    assert "RTLD_GLOBAL" in compatibility
    assert "ctypes.CDLL" in compatibility
    assert '"libpython-only"' in compatibility
    assert "Run `pkg upgrade` and retry" not in installer
    assert "termux_python_exec" not in installer
