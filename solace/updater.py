"""Safe, fast-forward-only updater for an installed Solace checkout."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List

CANONICAL_REPOSITORY = "Kanegraffiti/Solace"
PRESERVED_DATA = (
    "~/.solaceconfig.json",
    "~/.solace/",
    "~/models/",
    "~/llama.cpp/",
)


class UpdateError(RuntimeError):
    """Raised when updating would be unsafe or cannot be completed."""


@dataclass
class UpdateResult:
    changed: bool
    previous_commit: str
    current_commit: str
    preserved_data: List[str]


def _run_git(project_root: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess:
    git = shutil.which("git")
    if git is None:
        raise UpdateError("Git is not installed or is not available on PATH.")
    result = subprocess.run(
        [git, *arguments],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "Git command failed."
        raise UpdateError(message)
    return result


def _is_canonical_remote(remote: str) -> bool:
    normalized = remote.strip().lower().removesuffix(".git").rstrip("/")
    return normalized in {
        "https://github.com/kanegraffiti/solace",
        "http://github.com/kanegraffiti/solace",
        "ssh://git@github.com/kanegraffiti/solace",
        "git@github.com:kanegraffiti/solace",
    }


def update_solace(project_root: Path) -> UpdateResult:
    """Update Solace from its canonical main branch without touching user data."""

    root = project_root.resolve()
    if not (root / ".git").exists():
        raise UpdateError("This Solace installation is not a Git checkout; automatic update is unavailable.")

    remote = _run_git(root, "remote", "get-url", "origin").stdout.strip()
    if not _is_canonical_remote(remote):
        raise UpdateError(
            f"Origin is not the canonical {CANONICAL_REPOSITORY} repository. "
            "Update stopped to avoid replacing this checkout from an unexpected source."
        )

    branch = _run_git(root, "branch", "--show-current").stdout.strip()
    if branch != "main":
        raise UpdateError(
            f"Solace is on branch {branch or '(detached)'}, not main. Update stopped without changing files."
        )

    status = _run_git(root, "status", "--porcelain", "--untracked-files=all").stdout.strip()
    if status:
        raise UpdateError(
            "The Solace checkout has local or untracked changes. Update stopped so nothing is overwritten. "
            "Commit, move, or remove those checkout-only changes first. User data under ~/.solace is unaffected."
        )

    previous = _run_git(root, "rev-parse", "HEAD").stdout.strip()
    _run_git(root, "fetch", "--prune", "origin", "main")

    relation = _run_git(root, "rev-list", "--left-right", "--count", "HEAD...origin/main").stdout.split()
    if len(relation) != 2:
        raise UpdateError("Could not determine whether the local checkout can be safely updated.")
    ahead, behind = (int(value) for value in relation)
    if ahead:
        raise UpdateError(
            "The local main branch contains commits that are not in origin/main. "
            "Update stopped instead of overwriting or merging them."
        )
    if behind == 0:
        return UpdateResult(False, previous, previous, list(PRESERVED_DATA))

    _run_git(root, "merge", "--ff-only", "origin/main")
    current = _run_git(root, "rev-parse", "HEAD").stdout.strip()

    bash = shutil.which("bash")
    installer = root / "install.sh"
    if bash is None or not installer.is_file():
        raise UpdateError(
            f"Solace code updated to {current[:12]}, but install.sh could not be run. "
            "Your user data remains untouched."
        )
    completed = subprocess.run([bash, str(installer)], cwd=root, check=False)
    if completed.returncode != 0:
        raise UpdateError(
            f"Solace code updated to {current[:12]}, but dependency/launcher refresh failed. "
            "Your user data remains untouched; rerun `bash install.sh` after resolving the reported error."
        )

    return UpdateResult(True, previous, current, list(PRESERVED_DATA))


__all__ = ["CANONICAL_REPOSITORY", "PRESERVED_DATA", "UpdateError", "UpdateResult", "update_solace"]
