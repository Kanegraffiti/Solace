import os
import shutil
import subprocess
from pathlib import Path


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def test_termux_refresh_uses_installed_packages_without_contacting_mirror(tmp_path):
    root = Path(__file__).resolve().parents[1]
    project = tmp_path / "Solace"
    (project / "solace").mkdir(parents=True)
    (project / ".venv" / "bin").mkdir(parents=True)
    shutil.copy2(root / "install.sh", project / "install.sh")
    (project / "requirements-termux.txt").write_text("", encoding="utf-8")
    (project / "install.py").write_text("# placeholder\n", encoding="utf-8")
    (project / "solace" / "termux_compat.py").write_text("# placeholder\n", encoding="utf-8")
    (project / ".venv" / "pyvenv.cfg").write_text(
        "include-system-site-packages = true\n",
        encoding="utf-8",
    )

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    trace = tmp_path / "python-calls.txt"
    package_trace = tmp_path / "pkg-called.txt"
    fake_python = fake_bin / "python3"
    _write_executable(
        fake_python,
        """#!/usr/bin/env bash
set -eu
if [ "${1:-}" = "-c" ]; then
    case "${2:-}" in
        *version_info*) printf '3.12\\n' ;;
    esac
    exit 0
fi
printf '%s\\n' "$*" >> "$SOLACE_TEST_TRACE"
exit 0
""",
    )
    shutil.copy2(fake_python, project / ".venv" / "bin" / "python")
    _write_executable(fake_bin / "pip3", "#!/usr/bin/env bash\nexit 0\n")
    _write_executable(
        fake_bin / "dpkg-query",
        "#!/usr/bin/env bash\nprintf 'install ok installed'\n",
    )
    _write_executable(
        fake_bin / "pkg",
        "#!/usr/bin/env bash\nprintf 'called' > \"$SOLACE_PKG_TRACE\"\nexit 99\n",
    )

    environment = os.environ.copy()
    environment.update(
        {
            "PATH": f"{fake_bin}:{environment['PATH']}",
            "PYTHON": str(fake_python),
            "TERMUX_VERSION": "test",
            "PREFIX": "/data/data/com.termux/files/usr",
            "SOLACE_TEST_TRACE": str(trace),
            "SOLACE_PKG_TRACE": str(package_trace),
        }
    )
    completed = subprocess.run(
        ["bash", str(project / "install.sh"), "--preserve-config"],
        cwd=project,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert not package_trace.exists()
    assert completed.stdout.count("skipping repository download") == 2
    assert f"{project / 'install.py'} --skip-deps --preserve-config" in trace.read_text(encoding="utf-8")
