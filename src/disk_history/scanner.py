from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from disk_history.config import DEFAULT_MONITOR_RULES, MonitorRule
from disk_history.database import DirectorySnapshot, utc_now
from disk_history.paths import is_path_excluded


@dataclass(frozen=True)
class DirectorySize:
    exists: bool
    size_bytes: int
    file_count: int
    error_count: int


@dataclass(frozen=True)
class ChildSize:
    name: str
    path: Path
    is_directory: bool
    size_bytes: int
    file_count: int
    error_count: int


def directory_size(path: Path, excluded_roots: tuple[Path, ...] = ()) -> DirectorySize:
    if is_path_excluded(path, excluded_roots):
        return DirectorySize(False, 0, 0, 0)

    if not path.exists():
        return DirectorySize(False, 0, 0, 0)

    if path.is_file():
        try:
            return DirectorySize(True, path.stat().st_size, 1, 0)
        except OSError:
            return DirectorySize(True, 0, 0, 1)

    total = 0
    files = 0
    errors = 0
    stack = [path]

    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    try:
                        entry_path = Path(entry.path)
                        if is_path_excluded(entry_path, excluded_roots):
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(entry_path)
                        elif entry.is_file(follow_symlinks=False):
                            total += entry.stat(follow_symlinks=False).st_size
                            files += 1
                    except OSError:
                        errors += 1
        except OSError:
            errors += 1

    return DirectorySize(True, total, files, errors)


def capture_snapshots(
    monitor_rules: tuple[MonitorRule, ...] = DEFAULT_MONITOR_RULES,
    excluded_roots: tuple[Path, ...] = (),
) -> list[DirectorySnapshot]:
    captured_at = utc_now()
    snapshots: list[DirectorySnapshot] = []

    for rule in monitor_rules:
        if not rule.enabled:
            continue
        result = directory_size(rule.resolved_path(), excluded_roots)
        snapshots.append(
            DirectorySnapshot(
                captured_at=captured_at,
                rule_name=rule.name,
                path_template=rule.path_template,
                privacy_mode=rule.privacy_mode,
                exists=result.exists,
                size_bytes=result.size_bytes,
                file_count=result.file_count,
                error_count=result.error_count,
            )
        )

    return snapshots


def child_size_rankings(
    path: Path,
    excluded_roots: tuple[Path, ...] = (),
    *,
    limit: int = 50,
) -> list[ChildSize]:
    if is_path_excluded(path, excluded_roots) or not path.exists() or not path.is_dir():
        return []

    children: list[ChildSize] = []
    try:
        entries = sorted(path.iterdir(), key=lambda item: item.name.lower())
    except OSError:
        return []

    for entry in entries:
        if is_path_excluded(entry, excluded_roots):
            continue
        result = directory_size(entry, excluded_roots)
        children.append(
            ChildSize(
                name=entry.name,
                path=entry,
                is_directory=entry.is_dir(),
                size_bytes=result.size_bytes,
                file_count=result.file_count,
                error_count=result.error_count,
            )
        )

    children.sort(key=lambda item: item.size_bytes, reverse=True)
    return children[:limit]


def format_bytes(value: int | None) -> str:
    if value is None:
        return "unknown"
    sign = "-" if value < 0 else ""
    size = abs(float(value))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            if unit == "B":
                return f"{sign}{int(size)} {unit}"
            return f"{sign}{size:.1f} {unit}"
        size /= 1024
    return f"{sign}{size:.1f} TB"
