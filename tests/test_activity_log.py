from datetime import UTC, datetime, timedelta
import json

from disk_history.activity_log import (
    GrowthAlert,
    activity_log_writer,
    detect_growth_alert,
)
from disk_history.config import MonitorRule
from disk_history.database import DirectorySnapshot, format_time
from disk_history.settings import AppSettings, resolved_log_directory


def test_activity_log_writes_daily_files(tmp_path):
    settings = AppSettings(
        monitor_rules=(MonitorRule("Watched", str(tmp_path / "watched"), "detailed"),),
        ignore_patterns=(),
        log_directory=str(tmp_path / "logs"),
    )
    moment = datetime(2026, 5, 8, 10, tzinfo=UTC)
    writer = activity_log_writer(settings)

    writer.append_snapshots(
        [
            DirectorySnapshot(
                captured_at=moment,
                rule_name="Watched",
                path_template=str(tmp_path / "watched"),
                privacy_mode="detailed",
                exists=True,
                size_bytes=10,
                file_count=1,
            )
        ]
    )
    writer.append_event_rows([{"happened_at": format_time(moment), "delta_bytes": 10}], moment)
    writer.append_alert(
        GrowthAlert(
            happened_at=moment,
            window_minutes=30,
            threshold_bytes=5,
            net_growth_bytes=10,
            top_growth=[{"rule_name": "Watched", "delta_bytes": 10}],
        )
    )

    day_dir = tmp_path / "logs" / "2026-05-08"
    assert (day_dir / "summary.md").exists()
    assert (day_dir / "snapshots.jsonl").exists()
    assert (day_dir / "events.jsonl").exists()
    assert (day_dir / "alerts.jsonl").exists()
    assert json.loads((day_dir / "snapshots.jsonl").read_text(encoding="utf-8").splitlines()[0])[
        "rule_name"
    ] == "Watched"
    assert "增长提醒" in (day_dir / "summary.md").read_text(encoding="utf-8")


def test_detect_growth_alert_uses_configured_window_and_threshold(tmp_path):
    settings = AppSettings(
        monitor_rules=(MonitorRule("Watched", str(tmp_path / "watched"), "detailed"),),
        ignore_patterns=(),
        log_directory=str(tmp_path / "logs"),
        alert_window_minutes=30,
        alert_growth_threshold_mb=1,
    )
    now = datetime(2026, 5, 8, 10, tzinfo=UTC)
    rows = [
        _snapshot("Watched", 1_000_000, now - timedelta(minutes=25)),
        _snapshot("Watched", 2_500_000, now),
    ]

    alert = detect_growth_alert(rows, settings=settings, now=now)

    assert alert is not None
    assert alert.net_growth_bytes == 1_500_000
    assert alert.top_growth[0]["rule_name"] == "Watched"


def test_detect_growth_alert_respects_disabled_setting(tmp_path):
    settings = AppSettings(
        monitor_rules=(MonitorRule("Watched", str(tmp_path / "watched"), "detailed"),),
        ignore_patterns=(),
        enable_growth_alerts=False,
    )

    alert = detect_growth_alert([], settings=settings, now=datetime(2026, 5, 8, 10, tzinfo=UTC))

    assert alert is None


def test_resolved_log_directory_expands_templates(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    settings = AppSettings(monitor_rules=(), ignore_patterns=())

    assert resolved_log_directory(settings) == tmp_path / "DiskHistory" / "logs"


def _snapshot(rule_name: str, size_bytes: int, captured_at: datetime) -> dict[str, object]:
    return {
        "captured_at": format_time(captured_at),
        "rule_name": rule_name,
        "size_bytes": size_bytes,
        "file_count": 1,
        "privacy_mode": "detailed",
        "exists_on_disk": 1,
    }
