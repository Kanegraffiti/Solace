import json
from datetime import datetime, timezone

from solace import device_benchmark


def test_device_benchmark_runs_safe_checks_and_saves_private_report(tmp_path):
    report = device_benchmark.run_device_benchmark(
        report_dir=tmp_path,
        environ={"HOME": str(tmp_path), "PREFIX": "/usr"},
        clock=lambda: datetime(2026, 9, 28, 17, 30, tzinfo=timezone.utc),
    )

    assert report.failed == 0
    assert report.passed == 7
    assert report.skipped == 1
    assert report.report_path is not None
    assert report.report_path.parent == tmp_path
    assert report.report_path.stat().st_mode & 0o777 == 0o600
    assert all(isinstance(case, device_benchmark.DeviceBenchmarkCase) for case in report.cases)

    payload = json.loads(report.report_path.read_text(encoding="utf-8"))
    serialized = json.dumps(payload)
    assert payload["environment"] == "other"
    assert "command_contents" not in payload
    assert str(tmp_path) not in serialized
    assert "termux-environment" in serialized


def test_termux_storage_probe_reports_availability_without_path(tmp_path):
    storage = tmp_path / "storage"
    storage.mkdir()
    (storage / "shared").mkdir()

    cases = device_benchmark._termux_cases(
        {"HOME": str(tmp_path), "PREFIX": "/data/data/com.termux/files/usr"}
    )

    assert [case.status for case in cases] == ["pass", "pass"]
    assert str(tmp_path) not in " ".join(case.detail for case in cases)


def test_output_probe_retains_only_fixed_tail():
    _code, output, truncated = device_benchmark._run_packaged_probe(
        "i=0; while [ \"$i\" -lt 2000 ]; do printf '0123456789'; i=$((i + 1)); done"
    )

    assert truncated is True
    assert len(output) == device_benchmark.OUTPUT_LIMIT_BYTES


def test_cli_device_benchmark_prints_summary(main_module, monkeypatch, tmp_path):
    printed = []
    monkeypatch.setattr(main_module.console, "print", lambda *args, **kwargs: printed.append(args[0]))
    monkeypatch.setattr(
        main_module,
        "run_device_benchmark",
        lambda: device_benchmark.DeviceBenchmarkReport(
            version=1,
            created_at="2026-09-28T17:30:00+00:00",
            environment="termux",
            passed=1,
            failed=0,
            skipped=0,
            cases=[device_benchmark.DeviceBenchmarkCase("valid-syntax", "syntax", "pass", "valid")],
            report_path=tmp_path / "report.json",
        ),
    )

    keep_running = main_module._process_command("/bash benchmark device")

    assert keep_running is True
    assert printed
    assert printed[0].title == "Bash device benchmark"
    assert "No filenames" in printed[0].renderable
