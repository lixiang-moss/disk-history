from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class DirectoryRank:
    name: str
    size_bytes: int
    file_count: int
    privacy_mode: str


@dataclass(frozen=True)
class SnapshotSummary:
    total_size_bytes: int
    total_file_count: int
    rule_count: int
    latest_time: datetime | None


@dataclass(frozen=True)
class TimelinePoint:
    label: str
    delta_bytes: int


@dataclass(frozen=True)
class CategoryShare:
    category: str
    growth_bytes: int


@dataclass(frozen=True)
class HeatmapCell:
    day_label: str
    hour: int
    event_count: int
    activity_bytes: int
    intensity: float


@dataclass(frozen=True)
class CleanupRecommendation:
    rule_name: str
    size_bytes: int
    risk: str
    suggestion_key: str


Row = Mapping[str, Any]


def snapshot_summary(snapshot_rows: Sequence[Row]) -> SnapshotSummary:
    total_size = sum(int(row["size_bytes"] or 0) for row in snapshot_rows)
    total_files = sum(int(row["file_count"] or 0) for row in snapshot_rows)
    latest_time = max(
        (parse_time(str(row["captured_at"])) for row in snapshot_rows),
        default=None,
    )
    return SnapshotSummary(total_size, total_files, len(snapshot_rows), latest_time)


def directory_rankings(snapshot_rows: Sequence[Row], limit: int = 8) -> list[DirectoryRank]:
    rankings = [
        DirectoryRank(
            name=str(row["rule_name"]),
            size_bytes=int(row["size_bytes"] or 0),
            file_count=int(row["file_count"] or 0),
            privacy_mode=str(row["privacy_mode"]),
        )
        for row in snapshot_rows
        if int(row["exists_on_disk"] or 0)
    ]
    rankings.sort(key=lambda item: item.size_bytes, reverse=True)
    return rankings[:limit]


def category_growth(
    event_rows: Sequence[Row],
    *,
    hours: int = 24,
    now: datetime | None = None,
    limit: int = 8,
) -> list[CategoryShare]:
    cutoff = _cutoff(event_rows, hours, now)
    totals: dict[str, int] = defaultdict(int)
    for row in event_rows:
        happened_at = parse_time(str(row["happened_at"]))
        delta = int(row["delta_bytes"] or 0)
        if happened_at >= cutoff and delta > 0:
            totals[str(row["category"])] += delta
    shares = [CategoryShare(category, size) for category, size in totals.items()]
    shares.sort(key=lambda item: item.growth_bytes, reverse=True)
    return shares[:limit]


def timeline_by_hour(
    event_rows: Sequence[Row],
    *,
    hours: int = 24,
    now: datetime | None = None,
) -> list[TimelinePoint]:
    if hours <= 0:
        return []
    end = _analysis_now(event_rows, now).replace(minute=0, second=0, microsecond=0)
    start = end - timedelta(hours=hours - 1)
    totals = {start + timedelta(hours=index): 0 for index in range(hours)}

    for row in event_rows:
        happened_at = parse_time(str(row["happened_at"])).replace(minute=0, second=0, microsecond=0)
        if start <= happened_at <= end:
            totals[happened_at] += int(row["delta_bytes"] or 0)

    return [
        TimelinePoint(label=moment.strftime("%m-%d %H:00"), delta_bytes=totals[moment])
        for moment in sorted(totals)
    ]


def heatmap_cells(
    event_rows: Sequence[Row],
    *,
    days: int = 7,
    now: datetime | None = None,
) -> list[HeatmapCell]:
    if days <= 0:
        return []
    end = _analysis_now(event_rows, now).date()
    start = end - timedelta(days=days - 1)
    buckets: dict[tuple[str, int], tuple[int, int]] = {}

    for row in event_rows:
        happened_at = parse_time(str(row["happened_at"]))
        event_date = happened_at.date()
        if start <= event_date <= end:
            key = (event_date.strftime("%m-%d"), happened_at.hour)
            count, activity = buckets.get(key, (0, 0))
            buckets[key] = (count + 1, activity + abs(int(row["delta_bytes"] or 0)))

    max_activity = max((activity for _, activity in buckets.values()), default=0)
    cells: list[HeatmapCell] = []
    for day_index in range(days):
        day_label = (start + timedelta(days=day_index)).strftime("%m-%d")
        for hour in range(24):
            count, activity = buckets.get((day_label, hour), (0, 0))
            intensity = 0.0 if max_activity == 0 else activity / max_activity
            cells.append(HeatmapCell(day_label, hour, count, activity, intensity))
    return cells


def cleanup_recommendations(snapshot_rows: Sequence[Row]) -> list[CleanupRecommendation]:
    recommendations = []
    for row in snapshot_rows:
        rule_name = str(row["rule_name"])
        size_bytes = int(row["size_bytes"] or 0)
        lower_name = rule_name.lower()
        if "download" in lower_name:
            risk, suggestion = "safe", "downloads"
        elif "temp" in lower_name:
            risk, suggestion = "safe", "temp"
        elif "package cache" in lower_name:
            risk, suggestion = "caution", "package_cache"
        elif "windows update" in lower_name:
            risk, suggestion = "caution", "windows_update"
        elif "vs code" in lower_name:
            risk, suggestion = "caution", "dev_tools"
        elif "local programs" in lower_name:
            risk, suggestion = "protected", "local_programs"
        else:
            risk, suggestion = "protected", "personal"
        recommendations.append(CleanupRecommendation(rule_name, size_bytes, risk, suggestion))
    recommendations.sort(key=lambda item: item.size_bytes, reverse=True)
    return recommendations


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _analysis_now(event_rows: Sequence[Row], now: datetime | None) -> datetime:
    if now is not None:
        return now.astimezone(UTC) if now.tzinfo else now.replace(tzinfo=UTC)
    latest = max((parse_time(str(row["happened_at"])) for row in event_rows), default=None)
    return latest or datetime.now(UTC)


def _cutoff(event_rows: Sequence[Row], hours: int, now: datetime | None) -> datetime:
    return _analysis_now(event_rows, now) - timedelta(hours=hours)

