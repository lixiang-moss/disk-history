from datetime import UTC, datetime

from disk_history.database import format_time
from disk_history.reports import build_investigation_report, redact_path


def test_redact_path_replaces_common_private_roots(monkeypatch, tmp_path):
    user_root = tmp_path / "User"
    monkeypatch.setenv("USERPROFILE", str(user_root))

    redacted = redact_path(user_root / "Downloads" / "file.zip")

    assert redacted == r"{USERPROFILE}\Downloads\file.zip"


def test_build_investigation_report_contains_deltas_and_events(monkeypatch, tmp_path):
    user_root = tmp_path / "User"
    monkeypatch.setenv("USERPROFILE", str(user_root))
    start = datetime(2026, 5, 8, 8, tzinfo=UTC)
    end = datetime(2026, 5, 8, 10, tzinfo=UTC)
    rows = [
        _snapshot("Downloads", 100, start),
        _snapshot("Downloads", 180, end),
    ]
    events = [
        {
            "happened_at": format_time(datetime(2026, 5, 8, 9, tzinfo=UTC)),
            "event_type": "created",
            "delta_bytes": 80,
            "category": "Downloads",
            "display_path": str(user_root / "Downloads" / "file.zip"),
        }
    ]

    report = build_investigation_report(
        rows,
        events,
        start_at=start,
        end_at=end,
        redact_private_paths=True,
    )

    assert "# Disk History 调查报告" in report
    assert "Downloads" in report
    assert "80 B" in report
    assert "{USERPROFILE}" in report


def _snapshot(rule_name: str, size_bytes: int, captured_at: datetime) -> dict[str, object]:
    return {
        "captured_at": format_time(captured_at),
        "rule_name": rule_name,
        "size_bytes": size_bytes,
        "file_count": 1,
        "privacy_mode": "detailed",
        "exists_on_disk": 1,
    }
