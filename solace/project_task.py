"""Safe project discovery, archive extraction, and stack inspection for ``/do``."""

from __future__ import annotations

import json
import re
import shlex
import stat
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional, Sequence

from solace.logic import bash_intel

MAX_ARCHIVE_MEMBERS = 10_000
MAX_ARCHIVE_BYTES = 1024 * 1024 * 1024
COMMAND_TIMEOUT_SECONDS = 15 * 60
MAX_CAPTURE_BYTES = 16_000
ALLOWED_PROJECT_COMMANDS = {
    "cargo",
    "composer",
    "go",
    "npm",
    "php",
    "pnpm",
    "python",
    "python3",
    "yarn",
}


class ProjectTaskError(RuntimeError):
    """Raised when a project task cannot continue safely."""


@dataclass(frozen=True)
class ProjectInspection:
    root: Path
    stack: Sequence[str]
    evidence: Sequence[str]
    next_commands: Sequence[str]
    notes: Sequence[str]


@dataclass(frozen=True)
class ProjectCommand:
    command: str
    argv: Sequence[str]
    risk: str


@dataclass(frozen=True)
class ProjectCommandResult:
    command: ProjectCommand
    returncode: int
    stdout: str
    stderr: str
    output_truncated: bool


@dataclass(frozen=True)
class ProjectRecovery:
    diagnosis: Optional[str]
    retry_check: bash_intel.BashCheckResult


def _bounded_output(value: str, limit: int = MAX_CAPTURE_BYTES) -> tuple[str, bool]:
    """Keep the useful tail of command output within a predictable boundary."""

    encoded = value.encode("utf-8", errors="replace")
    if len(encoded) <= limit:
        return value, False
    tail = encoded[-limit:].decode("utf-8", errors="replace")
    return "[earlier output omitted]\n" + tail, True


def project_query(request: str) -> str:
    """Extract a conservative project name/path from a supported ``/do`` request."""

    value = request.strip()
    quoted = re.search(r"[\"']([^\"']+)[\"']", value)
    if quoted:
        return quoted.group(1).strip()

    value = re.sub(
        r"^(?:please\s+)?(?:find|locate|inspect|analyse|analyze|check|open|run)\s+",
        "",
        value,
        flags=re.IGNORECASE,
    )
    value = re.split(r",|\s+and\s+(?:then\s+)?", value, maxsplit=1, flags=re.IGNORECASE)[0]
    value = re.sub(r"\s+in\s+(?:my\s+)?(?:downloads?|storage|files?).*$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^(?:the|my|a|an)\s+", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+(?:website|project|folder|zip|archive)$", "", value, flags=re.IGNORECASE)
    return value.strip()


def wants_project_execution(request: str) -> bool:
    """Return whether a request explicitly selects the guarded execution flow."""

    return bool(re.match(r"^\s*run(?:\s+|$)", request, flags=re.IGNORECASE))


def supported_project(path: Path) -> bool:
    return path.is_dir() or (path.is_file() and path.suffix.casefold() == ".zip")


def choose_project_matches(paths: Sequence[Path]) -> List[Path]:
    """Prefer inspectable directories and ZIPs and remove nested duplicates."""

    candidates = sorted(
        (path for path in paths if supported_project(path)),
        key=lambda path: (len(path.parts), str(path)),
    )
    selected: List[Path] = []
    for candidate in candidates:
        if any(parent == candidate or parent in candidate.parents for parent in selected):
            continue
        selected.append(candidate)
    return selected


def archive_destination(archive: Path) -> Path:
    return archive.with_suffix("")


def validate_zip(archive: Path) -> Path:
    """Validate a ZIP without extracting it and return the intended destination."""

    if not archive.is_file() or archive.suffix.casefold() != ".zip":
        raise ProjectTaskError("The selected item is not a ZIP archive.")
    destination = archive_destination(archive)
    if destination.exists():
        raise ProjectTaskError("Extraction stopped because the destination already exists: {}".format(destination))

    total = 0
    try:
        with zipfile.ZipFile(str(archive)) as bundle:
            members = bundle.infolist()
            if len(members) > MAX_ARCHIVE_MEMBERS:
                raise ProjectTaskError("Archive has too many entries to extract safely.")
            for member in members:
                name = member.filename.replace("\\", "/")
                path = PurePosixPath(name)
                if path.is_absolute() or ".." in path.parts:
                    raise ProjectTaskError("Archive contains an unsafe path: {}".format(member.filename))
                mode = member.external_attr >> 16
                if stat.S_ISLNK(mode):
                    raise ProjectTaskError("Archive contains a symbolic link: {}".format(member.filename))
                total += member.file_size
                if total > MAX_ARCHIVE_BYTES:
                    raise ProjectTaskError("Archive expands beyond Solace's 1 GB safety limit.")
            bad_member = bundle.testzip()
            if bad_member:
                raise ProjectTaskError("Archive integrity check failed at: {}".format(bad_member))
    except zipfile.BadZipFile as exc:
        raise ProjectTaskError("The selected ZIP archive is damaged or invalid.") from exc
    return destination


def extract_zip(archive: Path) -> Path:
    """Extract a validated ZIP to a new sibling directory without overwriting."""

    destination = validate_zip(archive)
    destination.mkdir(parents=False, exist_ok=False)
    try:
        with zipfile.ZipFile(str(archive)) as bundle:
            bundle.extractall(str(destination))
    except Exception:
        # Validation prevents path escapes. Leave a failed extraction visible so
        # a later attempt cannot accidentally merge with partial output.
        raise
    return _project_root(destination)


def _project_root(path: Path) -> Path:
    children = [child for child in path.iterdir() if child.name not in {"__MACOSX", ".DS_Store"}]
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return path


def _package_details(path: Path) -> tuple[List[str], List[str], List[str]]:
    stacks: List[str] = ["Node.js"]
    commands: List[str] = []
    notes: List[str] = []
    try:
        package = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return stacks, ["npm install", "npm run dev"], ["package.json could not be parsed; commands are best guesses."]

    dependencies: Dict[str, object] = {}
    dependencies.update(package.get("dependencies", {}) if isinstance(package.get("dependencies"), dict) else {})
    dependencies.update(package.get("devDependencies", {}) if isinstance(package.get("devDependencies"), dict) else {})
    frameworks = {
        "next": "Next.js",
        "vite": "Vite",
        "react": "React",
        "vue": "Vue",
        "svelte": "Svelte",
        "astro": "Astro",
    }
    stacks.extend(label for dependency, label in frameworks.items() if dependency in dependencies)
    scripts = package.get("scripts", {}) if isinstance(package.get("scripts"), dict) else {}
    if (path.parent / "pnpm-lock.yaml").exists():
        installer = "pnpm install"
        runner = "pnpm"
    elif (path.parent / "yarn.lock").exists():
        installer = "yarn install"
        runner = "yarn"
    else:
        installer = "npm install"
        runner = "npm run"
    commands.append(installer)
    for name in ("dev", "start", "serve"):
        if name in scripts:
            commands.append("{} {}".format(runner, name))
            break
    if len(commands) == 1:
        notes.append("No dev, start, or serve script was found in package.json.")
    return stacks, commands, notes


def inspect_project(path: Path) -> ProjectInspection:
    """Detect a project's stack from local marker files without executing it."""

    root = _project_root(path.resolve())
    if not root.is_dir():
        raise ProjectTaskError("Project inspection requires a directory.")

    stack: List[str] = []
    evidence: List[str] = []
    commands: List[str] = []
    notes: List[str] = []

    package_json = root / "package.json"
    if package_json.exists():
        evidence.append("package.json")
        node_stack, node_commands, node_notes = _package_details(package_json)
        stack.extend(node_stack)
        commands.extend(node_commands)
        notes.extend(node_notes)
    if (root / "requirements.txt").exists() or (root / "pyproject.toml").exists():
        markers = [name for name in ("requirements.txt", "pyproject.toml") if (root / name).exists()]
        evidence.extend(markers)
        stack.append("Python")
        commands.append("python -m venv .venv")
        install = "python -m pip install -r requirements.txt"
        commands.append(install if "requirements.txt" in markers else "python -m pip install -e .")
    if (root / "manage.py").exists():
        evidence.append("manage.py")
        stack.append("Django")
        commands.append("python manage.py runserver")
    if (root / "index.html").exists() and "Node.js" not in stack:
        evidence.append("index.html")
        stack.append("Static website")
        commands.append("python -m http.server 8000")
    if (root / "composer.json").exists():
        evidence.append("composer.json")
        stack.append("PHP/Composer")
        commands.extend(["composer install", "php -S localhost:8000"])
    if (root / "Cargo.toml").exists():
        evidence.append("Cargo.toml")
        stack.append("Rust/Cargo")
        commands.append("cargo run")
    if (root / "go.mod").exists():
        evidence.append("go.mod")
        stack.append("Go")
        commands.append("go run .")

    if not stack:
        notes.append("No supported project marker was found at the project root.")
    notes.append("Commands are guidance only. Solace did not install dependencies or execute project code.")
    return ProjectInspection(root, list(dict.fromkeys(stack)), evidence, list(dict.fromkeys(commands)), notes)


def prepare_project_command(command: str, inspection: ProjectInspection) -> ProjectCommand:
    """Validate one detector-produced command and prepare a shell-free invocation."""

    if command not in inspection.next_commands:
        raise ProjectTaskError("Solace will only run commands produced by this project inspection.")
    try:
        argv = shlex.split(command, posix=True)
    except ValueError as exc:
        raise ProjectTaskError("The suggested command could not be parsed safely.") from exc
    if not argv or argv[0] not in ALLOWED_PROJECT_COMMANDS:
        raise ProjectTaskError("This project command is not on Solace's execution allowlist.")
    if any(token in {";", "&&", "||", "|", ">", ">>", "<"} for token in argv):
        raise ProjectTaskError("Shell operators are not allowed in project execution commands.")

    installers = {"install", "-r", "-e"}
    risk = (
        "High — dependency installation can run code supplied by the project."
        if installers.intersection(argv[1:])
        else "High — this starts code supplied by the project."
    )
    return ProjectCommand(command, argv, risk)


def execute_project_command(command: ProjectCommand, root: Path) -> ProjectCommandResult:
    """Run one approved command and return bounded output for local diagnosis."""

    project_root = root.resolve()
    if not project_root.is_dir():
        raise ProjectTaskError("The inspected project directory no longer exists.")
    try:
        completed = subprocess.run(
            list(command.argv),
            cwd=str(project_root),
            check=False,
            shell=False,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        return ProjectCommandResult(
            command,
            127,
            "",
            "{}: command not found".format(command.argv[0]),
            False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ProjectTaskError("Project command stopped after the 15-minute safety timeout.") from exc
    except KeyboardInterrupt:
        return ProjectCommandResult(command, 130, "", "Interrupted by user.", False)
    stdout, stdout_truncated = _bounded_output(completed.stdout or "")
    stderr, stderr_truncated = _bounded_output(completed.stderr or "")
    return ProjectCommandResult(
        command,
        completed.returncode,
        stdout,
        stderr,
        stdout_truncated or stderr_truncated,
    )


def build_project_recovery(result: ProjectCommandResult) -> ProjectRecovery:
    """Diagnose a failed command and validate its exact, allowlisted retry."""

    if result.returncode == 0:
        raise ValueError("Recovery is only available for failed project commands.")
    evidence = result.stderr.strip() or result.stdout.strip()
    diagnosis = bash_intel.debug_bash_error(evidence) if evidence else None
    retry_check = bash_intel.check_bash(result.command.command)
    return ProjectRecovery(diagnosis=diagnosis, retry_check=retry_check)


__all__ = [
    "ProjectInspection",
    "ProjectCommand",
    "ProjectCommandResult",
    "ProjectRecovery",
    "ProjectTaskError",
    "archive_destination",
    "build_project_recovery",
    "choose_project_matches",
    "extract_zip",
    "execute_project_command",
    "inspect_project",
    "project_query",
    "prepare_project_command",
    "supported_project",
    "validate_zip",
    "wants_project_execution",
]
