from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from disk_history.analytics import parse_time


@dataclass(frozen=True)
class TrendPoint:
    label: str
    size_bytes: int


def drive_subjects(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    return sorted({str(row["drive"]) for row in rows})


def tree_subjects(rows: Sequence[Mapping[str, Any]], limit: int = 200) -> list[str]:
    latest: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        path = str(row["path"])
        current = latest.get(path)
        if current is None or parse_time(str(row["captured_at"])) > parse_time(str(current["captured_at"])):
            latest[path] = row
    subjects = sorted(latest.values(), key=lambda row: int(row["size_bytes"] or 0), reverse=True)
    return [str(row["path"]) for row in subjects[:limit]]


def drive_trend(rows: Sequence[Mapping[str, Any]], drive: str) -> list[TrendPoint]:
    points = [
        TrendPoint(parse_time(str(row["captured_at"])).strftime("%m-%d %H:%M"), int(row["used_bytes"] or 0))
        for row in rows
        if str(row["drive"]) == drive
    ]
    return _dedupe_sorted(points)


def tree_trend(rows: Sequence[Mapping[str, Any]], path: str) -> list[TrendPoint]:
    points = [
        TrendPoint(parse_time(str(row["captured_at"])).strftime("%m-%d %H:%M"), int(row["size_bytes"] or 0))
        for row in rows
        if str(row["path"]) == path
    ]
    return _dedupe_sorted(points)


def latest_tree_growth(rows: Sequence[Mapping[str, Any]], limit: int = 100) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["path"])].append(row)

    growth_rows: list[dict[str, Any]] = []
    for path, items in grouped.items():
        ordered = sorted(items, key=lambda row: parse_time(str(row["captured_at"])))
        if len(ordered) < 2:
            continue
        start = ordered[0]
        end = ordered[-1]
        delta = int(end["size_bytes"] or 0) - int(start["size_bytes"] or 0)
        if delta <= 0:
            continue
        growth_rows.append(
            {
                "scope": "tree",
                "subject": path,
                "delta_bytes": delta,
                "start_time": start["captured_at"],
                "end_time": end["captured_at"],
                "start_size_bytes": int(start["size_bytes"] or 0),
                "end_size_bytes": int(end["size_bytes"] or 0),
            }
        )
    growth_rows.sort(key=lambda row: int(row["delta_bytes"]), reverse=True)
    return growth_rows[:limit]


def _dedupe_sorted(points: list[TrendPoint]) -> list[TrendPoint]:
    deduped: dict[str, TrendPoint] = {}
    for point in points:
        deduped[point.label] = point
    return [deduped[label] for label in sorted(deduped)]
