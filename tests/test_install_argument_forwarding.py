import os
import shutil
import subprocess
from pathlib import Path


def test_install_shell_forwards_preserve_config_to_python_installer(tmp_path):
    """Cover the same shell-to-Python handoff used by ``solace update``."""

    root = Path(__file__).resolve().parents[1]
    project = tmp_path / "Solace"
    project.mkdir()
    shutil.copy2(root / "install.sh", project / "install.sh")
    (project / "install.py").write_text("# installer placeholder\n", encoding="utf-8")

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_python = fake_bin / "python3"
    fake_python.write_text(
        """#!/usr/bin/env bash
set -eu
if [ "${1:-}" = "-m" ] && [ "${2:-}" = "venv" ]; then
    target="${@: -1}"
    mkdir -p "$target/bin"
    cp "$0" "$target/bin/python"
    exit 0
fi
if [ "${1:-}" = "-c" ]; then
    printf '3.12\\n'
    exit 0
fi
printf '%s\\n' "$*" >> "$SOLACE_TEST_TRACE"
""",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    trace = tmp_path / "calls.txt"
    environment = os.environ.copy()
    environment.update(
        {
            "PATH": f"{fake_bin}:{environment['PATH']}",
            "PYTHON": str(fake_python),
            "SOLACE_TEST_TRACE": str(trace),
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
    calls = trace.read_text(encoding="utf-8").splitlines()
    assert calls[-1] == f"{project / 'install.py'} --skip-deps --preserve-config"
