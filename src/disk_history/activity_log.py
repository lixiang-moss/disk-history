from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping

from disk_history.analytics import snapshot_deltas
from disk_history.database import DirectorySnapshot, format_time
from disk_history.scanner import format_bytes
from disk_history.settings import AppSettings, resolved_log_directory


@dataclass(frozen=True)
class GrowthAlert:
    happened_at: datetime
    window_minutes: int
    threshold_bytes: int
    net_growth_bytes: int
    top_growth: list[dict[str, Any]]


class ActivityLogWriter:
    def __init__(self, log_root: Path) -> None:
        self.log_root = log_root

    def day_dir(self, moment: datetime) -> Path:
        local_moment = moment.astimezone() if moment.tzinfo else moment
        return self.log_root / local_moment.strftime("%Y-%m-%d")

    def ensure_day_files(self, moment: datetime) -> Path:
        day_dir = self.day_dir(moment)
        day_dir.mkdir(parents=True, exist_ok=True)
        for name in ("snapshots.jsonl", "events.jsonl", "alerts.jsonl"):
            (day_dir / name).touch(exist_ok=True)
        summary = day_dir / "summary.md"
        if not summary.exists():
            summary.write_text(
                "# Disk History 日志摘要\n\n"
                "本文件用于复制给 AI 或人工分析。它只记录磁盘变化元数据，"
                "不包含文件内容，也不会执行清理操作。\n\n",
                encoding="utf-8",
            )
        return day_dir

    def append_snapshots(self, snapshots: Iterable[DirectorySnapshot]) -> None:
        snapshots = list(snapshots)
        if not snapshots:
            return
        moment = snapshots[0].captured_at
        day_dir = self.ensure_day_files(moment)
        with (day_dir / "snapshots.jsonl").open("a", encoding="utf-8") as handle:
            for snapshot in snapshots:
                handle.write(json.dumps(_snapshot_record(snapshot), ensure_ascii=False) + "\n")
        self._append_summary(moment, f"- {moment.isoformat()} 记录了 {len(snapshots)} 条目录快照。\n")

    def append_event_rows(self, rows: Iterable[Mapping[str, Any]], moment: datetime) -> None:
        day_dir = self.ensure_day_files(moment)
        with (day_dir / "events.jsonl").open("a", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(dict(row), ensure_ascii=False) + "\n")

    def append_alert(self, alert: GrowthAlert) -> None:
        day_dir = self.ensure_day_files(alert.happened_at)
        record = {
            "happened_at": format_time(alert.happened_at),
            "window_minutes": alert.window_minutes,
            "threshold_bytes": alert.threshold_bytes,
            "net_growth_bytes": alert.net_growth_bytes,
            "top_growth": alert.top_growth,
        }
        with (day_dir / "alerts.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

        top_lines = "\n".join(
            f"  - {item['rule_name']}: {format_bytes(int(item['delta_bytes']))}"
            for item in alert.top_growth
        )
        self._append_summary(
            alert.happened_at,
            "\n".join(
                [
                    f"## 增长提醒 {alert.happened_at.isoformat()}",
                    "",
                    (
                        f"- 最近 {alert.window_minutes} 分钟监控目录净增长 "
                        f"{format_bytes(alert.net_growth_bytes)}，超过阈值 "
                        f"{format_bytes(alert.threshold_bytes)}。"
                    ),
                    "- 增长最多的目录：",
                    top_lines or "  - 暂无目录明细",
                    "",
                ]
            ),
        )

    def _append_summary(self, moment: datetime, text: str) -> None:
        day_dir = self.ensure_day_files(moment)
        with (day_dir / "summary.md").open("a", encoding="utf-8") as handle:
            handle.write(text)
            if not text.endswith("\n"):
                handle.write("\n")


def detect_growth_alert(
    snapshot_rows: list[Mapping[str, Any]],
    *,
    settings: AppSettings,
    now: datetime,
) -> GrowthAlert | None:
    if not settings.enable_growth_alerts:
        return None

    now = now.astimezone(UTC) if now.tzinfo else now.replace(tzinfo=UTC)
    threshold_bytes = settings.alert_growth_threshold_mb * 1024 * 1024
    start = now - timedelta(minutes=settings.alert_window_minutes)
    deltas = snapshot_deltas(snapshot_rows, start_at=start, end_at=now, limit=1000)
    net_growth = sum(delta.delta_bytes for delta in deltas)
    if net_growth < threshold_bytes:
        return None

    top_growth = [
        {
            "rule_name": delta.rule_name,
            "delta_bytes": delta.delta_bytes,
            "start_size_bytes": delta.start_size_bytes,
            "end_size_bytes": delta.end_size_bytes,
            "start_time": format_time(delta.start_time),
            "end_time": format_time(delta.end_time),
        }
        for delta in deltas
        if delta.delta_bytes > 0
    ][:5]
    return GrowthAlert(
        happened_at=now,
        window_minutes=settings.alert_window_minutes,
        threshold_bytes=threshold_bytes,
        net_growth_bytes=net_growth,
        top_growth=top_growth,
    )


def activity_log_writer(settings: AppSettings) -> ActivityLogWriter:
    return ActivityLogWriter(resolved_log_directory(settings))


def _snapshot_record(snapshot: DirectorySnapshot) -> dict[str, Any]:
    return {
        "captured_at": format_time(snapshot.captured_at),
        "rule_name": snapshot.rule_name,
        "path_template": snapshot.path_template,
        "privacy_mode": snapshot.privacy_mode,
        "exists": snapshot.exists,
        "size_bytes": snapshot.size_bytes,
        "file_count": snapshot.file_count,
        "error_count": snapshot.error_count,
    }
