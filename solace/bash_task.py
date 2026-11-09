"""Deterministic, approval-first terminal task planning for ``/bash do``."""

from __future__ import annotations

import re
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence
from urllib.parse import urlparse

from solace.logic import bash_intel

COMMAND_TIMEOUT_SECONDS = 15 * 60
MAX_OUTPUT_BYTES = 16_000


class BashTaskError(RuntimeError):
    """Raised when a terminal request cannot be planned or run safely."""


@dataclass(frozen=True)
class BashTaskPlan:
    request: str
    command: str
    argv: Sequence[str]
    cwd: Path
    risk: str
    effect: str
    check: bash_intel.BashCheckResult


@dataclass(frozen=True)
class BashTaskResult:
    returncode: int
    output: str
    output_truncated: bool


def _home_path(value: str, home: Path, *, must_exist: bool = True) -> Path:
    raw = value.strip().strip("\"'")
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = home / candidate
    resolved = candidate.resolve()
    home_resolved = home.resolve()
    if resolved != home_resolved and home_resolved not in resolved.parents:
        raise BashTaskError("The requested path is outside your home directory.")
    if must_exist and not resolved.exists():
        raise BashTaskError("Path not found: {}".format(resolved))
    return resolved


def _argument_after(request: str, pattern: str) -> str:
    match = re.match(pattern, request.strip(), flags=re.IGNORECASE)
    return (match.group(1) or "").strip() if match else ""


def _plan_parts(request: str, home: Path) -> tuple[List[str], Path, str, str]:
    clean = request.strip()
    lower = clean.casefold()

    if re.match(r"^(?:find|locate|search for)\s+", lower):
        query = _argument_after(clean, r"^(?:find|locate|search for)\s+(.+)$").strip("\"'")
        if not query or "/" in query or query in {".", "*"}:
            raise BashTaskError("Give a filename or a distinctive part of one to find.")
        return ["find", str(home), "-iname", "*{}*".format(query)], home, "Low", "Read-only file search"

    if re.match(r"^(?:list|show)\s+(?:my\s+)?(?:downloads?|storage)(?:\s+files?)?$", lower):
        target = home / "storage" / "downloads"
        if not target.is_dir():
            target = home / "storage"
        target = _home_path(str(target), home)
        return ["ls", "-la", str(target)], home, "Low", "Read-only directory listing"

    if re.match(r"^(?:inspect|list|preview)\s+(?:the\s+)?(?:zip|archive)\s+", lower):
        value = _argument_after(clean, r"^(?:inspect|list|preview)\s+(?:the\s+)?(?:zip|archive)\s+(.+)$")
        archive = _home_path(value, home)
        if archive.suffix.casefold() != ".zip" or not archive.is_file():
            raise BashTaskError("ZIP inspection requires an existing .zip file.")
        return ["unzip", "-l", str(archive)], archive.parent, "Low", "Read-only archive inspection"

    if re.match(r"^(?:git\s+)?status(?:\s+.+)?$", lower):
        value = _argument_after(clean, r"^(?:git\s+)?status(?:\s+(.+))?$")
        root = _home_path(value or ".", home)
        if not root.is_dir():
            raise BashTaskError("Git status requires a project directory.")
        return ["git", "status", "--short", "--branch"], root, "Low", "Read-only Git status"

    if re.match(r"^(?:git\s+)?pull(?:\s+.+)?$", lower):
        value = _argument_after(clean, r"^(?:git\s+)?pull(?:\s+(.+))?$")
        root = _home_path(value or ".", home)
        if not root.is_dir():
            raise BashTaskError("Git pull requires a project directory.")
        return ["git", "pull", "--ff-only"], root, "Medium", "Downloads and fast-forwards tracked project files"

    if re.match(r"^(?:find|show|list)\s+(?:the\s+)?process(?:es)?\s+", lower):
        name = _argument_after(clean, r"^(?:find|show|list)\s+(?:the\s+)?process(?:es)?\s+(.+)$")
        if not re.fullmatch(r"[A-Za-z0-9_.+-]{1,80}", name):
            raise BashTaskError(
                "Give a simple process name containing letters, numbers, dot, plus, dash, or underscore."
            )
        return ["pgrep", "-af", name], home, "Low", "Read-only process lookup"

    if lower.startswith("download "):
        url = _argument_after(clean, r"^download\s+(.+)$").strip("\"'")
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise BashTaskError("Downloads require a public HTTPS URL without embedded credentials.")
        target = home / "storage" / "downloads"
        if not target.is_dir():
            target = home
        return (
            ["curl", "--fail", "--location", "--remote-name", "--", url],
            target,
            "Medium",
            "Downloads one file into {}".format(target),
        )

    if lower.startswith("backup "):
        source_text = _argument_after(clean, r"^backup\s+(.+)$")
        source = _home_path(source_text, home)
        destination = source.parent / "{}-solace-backup.tar.gz".format(source.name)
        if destination.exists():
            raise BashTaskError("Backup destination already exists: {}".format(destination))
        return (
            ["tar", "-czf", str(destination), "-C", str(source.parent), source.name],
            home,
            "Medium",
            "Creates a new backup archive; never overwrites",
        )

    if re.match(r"^(?:run|launch)\s+(?:script\s+)?", lower):
        value = _argument_after(clean, r"^(?:run|launch)\s+(?:script\s+)?(.+)$")
        script = _home_path(value, home)
        if script.suffix.casefold() not in {".sh", ".bash"} or not script.is_file():
            raise BashTaskError("Script launch requires an existing .sh or .bash file.")
        return (
            ["bash", str(script)],
            script.parent,
            "High",
            "Executes a local script that may change files or system state",
        )

    raise BashTaskError(
        "No deterministic terminal recipe matched. Try find, list downloads, inspect zip, "
        "git status, git pull, show process, download, backup, or run script."
    )


def plan_bash_task(request: str, *, home: Optional[Path] = None) -> BashTaskPlan:
    """Turn one supported natural-language request into an inspectable plan."""

    clean = request.strip()
    if not clean:
        raise BashTaskError("Tell Solace what terminal task to do.")
    user_home = (home or Path.home()).resolve()
    argv, cwd, risk, effect = _plan_parts(clean, user_home)
    command = shlex.join(argv)
    # A trailing no-op keeps check_bash from mistaking a complete command that
    # ends in ``.sh`` for a script-file path. The displayed/executed argv is
    # unchanged.
    check = bash_intel.check_bash(command + "\n:")
    if not check.syntax_valid:
        raise BashTaskError("Generated command failed Bash validation: {}".format(check.diagnostics))
    return BashTaskPlan(clean, command, argv, cwd, risk, effect, check)


def execute_bash_task(
    plan: BashTaskPlan,
    *,
    timeout: float = COMMAND_TIMEOUT_SECONDS,
    max_output_bytes: int = MAX_OUTPUT_BYTES,
) -> BashTaskResult:
    """Execute an already approved plan without invoking a shell."""

    if max_output_bytes <= 0:
        raise ValueError("Output limit must be greater than zero.")
    try:
        completed = subprocess.run(
            list(plan.argv),
            cwd=str(plan.cwd),
            shell=False,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise BashTaskError("Required command is not installed: {}".format(plan.argv[0])) from exc
    except subprocess.TimeoutExpired as exc:
        raise BashTaskError("Terminal task stopped after the 15-minute safety timeout.") from exc
    data = completed.stdout + completed.stderr
    truncated = len(data) > max_output_bytes
    if truncated:
        data = data[-max_output_bytes:]
    output = data.decode("utf-8", errors="replace").strip()
    if truncated:
        output = "[earlier output omitted]\n" + output
    return BashTaskResult(completed.returncode, output, truncated)


__all__ = [
    "BashTaskError",
    "BashTaskPlan",
    "BashTaskResult",
    "execute_bash_task",
    "plan_bash_task",
]
