from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from disk_history.analytics import SnapshotDelta, parse_time, snapshot_deltas
from disk_history.database import format_time
from disk_history.scanner import format_bytes


def default_report_path(base_dir: Path, moment: datetime | None = None) -> Path:
    moment = moment or datetime.now(UTC)
    return base_dir / "exports" / f"disk-history-report-{moment.strftime('%Y%m%d-%H%M%S')}.md"


def build_investigation_report(
    snapshot_rows: Sequence[Mapping[str, Any]],
    event_rows: Sequence[Mapping[str, Any]],
    *,
    start_at: datetime,
    end_at: datetime,
    redact_private_paths: bool = True,
) -> str:
    deltas = snapshot_deltas(snapshot_rows, start_at=start_at, end_at=end_at, limit=50)
    lines = [
        "# Disk History 调查报告",
        "",
        f"- 起始时间：{format_time(start_at)}",
        f"- 结束时间：{format_time(end_at)}",
        f"- 路径处理：{'已隐藏常见私人路径' if redact_private_paths else '保留原始路径'}",
        "",
        "## 目录变化排行",
        "",
    ]
    lines.extend(_delta_lines(deltas, redact_private_paths))
    lines.extend(["", "## 文件事件线索", ""])
    lines.extend(_event_lines(event_rows, redact_private_paths))
    lines.extend(
        [
            "",
            "## 说明",
            "",
            "- 本报告只基于 Disk History 已记录的目录快照和文件事件元数据。",
            "- 文件事件是辅助线索，不保证覆盖所有短暂文件变化。",
            "- 本报告不包含文件内容，也不代表工具已经自动判断出最终原因。",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def redact_path(value: object) -> str:
    text = "" if value is None else str(value)
    replacements = {
        "{USERPROFILE}": os.environ.get("USERPROFILE", ""),
        "{LOCALAPPDATA}": os.environ.get("LOCALAPPDATA", ""),
        "{APPDATA}": os.environ.get("APPDATA", ""),
        "{PROGRAMDATA}": os.environ.get("PROGRAMDATA", ""),
        "{SYSTEMROOT}": os.environ.get("SYSTEMROOT", ""),
    }
    for token, path in sorted(replacements.items(), key=lambda item: len(item[1]), reverse=True):
        if path:
            text = text.replace(path, token)
            text = text.replace(path.replace("\\", "/"), token)
    return text


def _delta_lines(deltas: Sequence[SnapshotDelta], redact: bool) -> list[str]:
    if not deltas:
        return ["暂无足够快照可对比。"]
    lines = [
        "| 规则 | 净变化 | 起始大小 | 结束大小 | 起始快照 | 结束快照 |",
        "| --- | ---: | ---: | ---: | --- | --- |",
    ]
    for delta in deltas:
        rule_name = redact_path(delta.rule_name) if redact else delta.rule_name
        lines.append(
            " | ".join(
                [
                    f"| {rule_name}",
                    format_bytes(delta.delta_bytes),
                    format_bytes(delta.start_size_bytes),
                    format_bytes(delta.end_size_bytes),
                    format_time(delta.start_time),
                    f"{format_time(delta.end_time)} |",
                ]
            )
        )
    return lines


def _event_lines(event_rows: Sequence[Mapping[str, Any]], redact: bool) -> list[str]:
    filtered = [
        row
        for row in event_rows
        if row.get("happened_at") is not None and _safe_delta(row) != 0
    ][:200]
    if not filtered:
        return ["暂无文件事件线索。"]
    lines = [
        "| 时间 | 事件 | 变化 | 分类 | 路径 |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for row in filtered:
        display_path = str(row.get("display_path", ""))
        category = str(row.get("category", ""))
        if redact:
            display_path = redact_path(display_path)
            category = redact_path(category)
        lines.append(
            " | ".join(
                [
                    f"| {row.get('happened_at', '')}",
                    str(row.get("event_type", "")),
                    format_bytes(_safe_delta(row)),
                    category,
                    f"{display_path} |",
                ]
            )
        )
    return lines


def _safe_delta(row: Mapping[str, Any]) -> int:
    try:
        return int(row.get("delta_bytes") or 0)
    except (TypeError, ValueError):
        return 0


def report_range_from_rows(snapshot_rows: Sequence[Mapping[str, Any]]) -> tuple[datetime, datetime]:
    moments = [parse_time(str(row["captured_at"])) for row in snapshot_rows]
    if not moments:
        now = datetime.now(UTC)
        return now, now
    return min(moments), max(moments)
