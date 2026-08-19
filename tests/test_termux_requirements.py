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
