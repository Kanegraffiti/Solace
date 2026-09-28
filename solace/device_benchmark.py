"""Private, non-destructive acceptance checks for Solace on Termux devices."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Mapping, Optional

from solace.configuration import get_storage_path, load_config
from solace.logic import bash_intel

REPORT_VERSION = 1
PROBE_TIMEOUT_SECONDS = 5.0
OUTPUT_LIMIT_BYTES = 16 * 1024


@dataclass(frozen=True)
class DeviceBenchmarkCase:
    name: str
    category: str
    status: str
    detail: str


@dataclass(frozen=True)
class DeviceBenchmarkReport:
    version: int
    created_at: str
    environment: str
    passed: int
    failed: int
    skipped: int
    cases: List[DeviceBenchmarkCase]
    report_path: Optional[Path] = None


def _case(name: str, category: str, passed: bool, detail: str) -> DeviceBenchmarkCase:
    return DeviceBenchmarkCase(name, category, "pass" if passed else "fail", detail)


def _run_packaged_probe(script: str) -> tuple[int, bytes, bool]:
    """Run a fixed probe and retain only a bounded output tail."""

    bash = shutil.which("bash")
    if bash is None:
        raise RuntimeError("Bash is not installed or is not available on PATH.")
    completed = subprocess.run(
        [bash, "--noprofile", "--norc", "-c", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=PROBE_TIMEOUT_SECONDS,
    )
    output = completed.stdout or b""
    truncated = len(output) > OUTPUT_LIMIT_BYTES
    return completed.returncode, output[-OUTPUT_LIMIT_BYTES:], truncated


def _syntax_cases() -> List[DeviceBenchmarkCase]:
    valid = bash_intel.check_bash('printf "%s\\n" "$HOME"')
    invalid = bash_intel.check_bash("if true; then")
    return [
        _case("valid-syntax", "syntax", valid.syntax_valid, "bash -n accepted valid syntax"),
        _case("invalid-syntax", "syntax", not invalid.syntax_valid, "bash -n rejected invalid syntax"),
    ]


def _execution_cases() -> List[DeviceBenchmarkCase]:
    quote_code, quote_output, _ = _run_packaged_probe("value='two words'; printf '<%s>\\n' \"$value\"")
    pipe_code, pipe_output, _ = _run_packaged_probe(
        "set -o pipefail; printf 'termux-ready\\n' | grep -q '^termux-ready$'"
    )
    _tail_code, tail_output, truncated = _run_packaged_probe(
        "i=0; while [ \"$i\" -lt 2000 ]; do printf '0123456789'; i=$((i + 1)); done"
    )
    return [
        _case(
            "quoted-expansion",
            "execution",
            quote_code == 0 and quote_output == b"<two words>\n",
            "quoted variables retained one argument",
        ),
        _case(
            "pipeline-status",
            "execution",
            pipe_code == 0 and not pipe_output,
            "pipefail and pipeline status behaved correctly",
        ),
        _case(
            "bounded-output",
            "execution",
            truncated and len(tail_output) == OUTPUT_LIMIT_BYTES,
            "diagnostic output was retained within the 16 KiB boundary",
        ),
    ]


def _intelligence_cases() -> List[DeviceBenchmarkCase]:
    diagnosis = bash_intel.debug_bash_error("bash: example-tool: command not found")
    safety = bash_intel.classify_safety("rm -rf /data/data/com.termux/files/home/storage")
    return [
        _case(
            "known-error-diagnosis",
            "diagnosis",
            bool(diagnosis and "Cause:" in diagnosis and "Fix:" in diagnosis),
            "known command failure produced a cause and fix",
        ),
        _case(
            "critical-path-warning",
            "safety",
            bool(safety),
            "critical Android path triggered a safety warning",
        ),
    ]


def _termux_cases(environ: Mapping[str, str]) -> List[DeviceBenchmarkCase]:
    prefix = environ.get("PREFIX", "")
    if "com.termux" not in prefix:
        return [DeviceBenchmarkCase("termux-environment", "termux", "skip", "not running inside Termux")]

    home = Path(environ.get("HOME", str(Path.home()))).expanduser()
    storage_root = home / "storage"
    shared = storage_root / "shared"
    return [
        _case("termux-environment", "termux", True, "Termux environment detected"),
        _case(
            "shared-storage-link",
            "termux",
            storage_root.is_dir() and shared.exists(),
            "Android shared-storage link is available"
            if shared.exists()
            else "shared storage is unavailable; run termux-setup-storage",
        ),
    ]


def _write_report(report: DeviceBenchmarkReport, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = report_dir / f"device-benchmark-{stamp}.json"
    temporary = report_dir / f".{destination.name}.tmp"
    payload = asdict(report)
    payload.pop("report_path", None)
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(destination)
    return destination


def run_device_benchmark(
    *,
    report_dir: Optional[Path] = None,
    environ: Optional[Mapping[str, str]] = None,
    clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> DeviceBenchmarkReport:
    """Run packaged checks and persist an anonymized local report."""

    cases: List[DeviceBenchmarkCase] = []
    try:
        cases.extend(_syntax_cases())
        cases.extend(_execution_cases())
        cases.extend(_intelligence_cases())
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        cases.append(DeviceBenchmarkCase("bash-runtime", "environment", "fail", str(exc)))

    environment = environ if environ is not None else os.environ
    cases.extend(_termux_cases(environment))
    passed = sum(item.status == "pass" for item in cases)
    failed = sum(item.status == "fail" for item in cases)
    skipped = sum(item.status == "skip" for item in cases)
    report = DeviceBenchmarkReport(
        version=REPORT_VERSION,
        created_at=clock().astimezone(timezone.utc).isoformat(timespec="seconds"),
        environment="termux" if "com.termux" in environment.get("PREFIX", "") else "other",
        passed=passed,
        failed=failed,
        skipped=skipped,
        cases=cases,
    )
    if report_dir is None:
        report_dir = get_storage_path(load_config(), "root") / "benchmarks"
    path = _write_report(report, report_dir)
    return replace(report, report_path=path)
