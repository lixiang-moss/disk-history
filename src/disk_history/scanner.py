from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from disk_history.config import (
    DEFAULT_EXCLUDED_PATHS,
    DEFAULT_MONITOR_RULES,
    DEFAULT_NOISE_RULES,
    MonitorRule,
    NoiseRule,
    expand_path_template,
)
from disk_history.database import (
    DirectorySnapshot,
    DriveSnapshot,
    FocusSnapshot,
    TreeSnapshot,
    utc_now,
)
from disk_history.focus_targets import is_focus_target_expired, normalized_focus_target
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


@dataclass(frozen=True)
class TreeRoot:
    name: str
    path: Path
    drive: str
    strategy: str


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


def default_excluded_roots(extra_roots: tuple[Path, ...] = ()) -> tuple[Path, ...]:
    roots = [expand_path_template(template) for template in DEFAULT_EXCLUDED_PATHS]
    roots.extend(extra_roots)
    return tuple(roots)


def capture_drive_snapshots(drives: tuple[str, ...]) -> list[DriveSnapshot]:
    captured_at = utc_now()
    snapshots: list[DriveSnapshot] = []
    for drive in drives:
        drive_name = drive.rstrip("\\/")
        root = Path(f"{drive_name}\\")
        if not root.exists():
            continue
        try:
            usage = shutil.disk_usage(root)
        except OSError:
            continue
        snapshots.append(
            DriveSnapshot(
                captured_at=captured_at,
                drive=drive_name,
                total_bytes=usage.total,
                used_bytes=usage.total - usage.free,
                free_bytes=usage.free,
            )
        )
    return snapshots


def capture_tree_snapshots(
    roots: tuple[TreeRoot, ...],
    *,
    max_depth: int,
    excluded_roots: tuple[Path, ...] = (),
) -> list[TreeSnapshot]:
    captured_at = utc_now()
    snapshots: list[TreeSnapshot] = []
    for root in roots:
        if is_path_excluded(root.path, excluded_roots) or not root.path.exists():
            continue
        stats = tree_size_index(root.path, max_depth, excluded_roots)
        for path, (depth, size_bytes, file_count, error_count) in stats.items():
            snapshots.append(
                TreeSnapshot(
                    captured_at=captured_at,
                    drive=root.drive,
                    path=str(path),
                    relative_path=relative_to_root(path, root.path),
                    depth=depth,
                    size_bytes=size_bytes,
                    file_count=file_count,
                    error_count=error_count,
                    strategy=root.strategy,
                )
            )
    return snapshots


def capture_noise_snapshots(
    noise_rules: tuple[NoiseRule, ...] = DEFAULT_NOISE_RULES,
    *,
    excluded_roots: tuple[Path, ...] = (),
) -> list[TreeSnapshot]:
    roots = tuple(
        TreeRoot(rule.name, rule.resolved_path(), drive_for_path(rule.resolved_path()), "noise_snapshot_only")
        for rule in noise_rules
        if rule.enabled
    )
    return capture_tree_snapshots(roots, max_depth=0, excluded_roots=excluded_roots)


def capture_focus_snapshots(
    focus_targets: tuple[dict[str, object], ...],
    *,
    max_depth: int,
    excluded_roots: tuple[Path, ...] = (),
) -> list[FocusSnapshot]:
    captured_at = utc_now()
    snapshots: list[FocusSnapshot] = []
    for index, target in enumerate(focus_targets):
        target = normalized_focus_target(target, index=index, default_depth=max_depth)
        if not bool(target.get("enabled", True)) or is_focus_target_expired(target):
            continue
        target_id = str(target.get("id") or target.get("name") or target.get("path_template"))
        target_name = str(target.get("name") or target_id)
        path_template = str(target.get("path_template") or target.get("path") or "")
        if not path_template:
            continue
        root = expand_path_template(path_template)
        if is_path_excluded(root, excluded_roots) or not root.exists():
            continue
        depth_limit = int(target.get("max_depth") or max_depth)
        for path, depth in iter_tree_paths(root, depth_limit, excluded_roots):
            result = directory_size(path, excluded_roots)
            snapshots.append(
                FocusSnapshot(
                    captured_at=captured_at,
                    target_id=target_id,
                    target_name=target_name,
                    path=str(path),
                    relative_path=relative_to_root(path, root),
                    depth=depth,
                    size_bytes=result.size_bytes,
                    file_count=result.file_count,
                    error_count=result.error_count,
                )
            )
    return snapshots


def tree_roots_from_monitor_rules(
    monitor_rules: tuple[MonitorRule, ...],
    excluded_roots: tuple[Path, ...] = (),
) -> tuple[TreeRoot, ...]:
    roots: list[TreeRoot] = []
    for rule in monitor_rules:
        if not rule.enabled:
            continue
        path = rule.resolved_path()
        if is_path_excluded(path, excluded_roots) or not path.exists():
            continue
        roots.append(TreeRoot(rule.name, path, drive_for_path(path), "standard"))
    return tuple(roots)


def iter_tree_paths(
    root: Path,
    max_depth: int,
    excluded_roots: tuple[Path, ...] = (),
) -> list[tuple[Path, int]]:
    paths: list[tuple[Path, int]] = []
    stack: list[tuple[Path, int]] = [(root, 0)]
    while stack:
        current, depth = stack.pop()
        if is_path_excluded(current, excluded_roots):
            continue
        paths.append((current, depth))
        if depth >= max_depth or not current.is_dir():
            continue
        try:
            children = sorted(current.iterdir(), key=lambda item: item.name.lower(), reverse=True)
        except OSError:
            continue
        for child in children:
            if child.is_dir() and not is_path_excluded(child, excluded_roots):
                stack.append((child, depth + 1))
    return paths


def tree_size_index(
    root: Path,
    max_depth: int,
    excluded_roots: tuple[Path, ...] = (),
) -> dict[Path, tuple[int, int, int, int]]:
    stats: dict[Path, list[int]] = {root: [0, 0, 0, 0]}
    if root.is_file():
        try:
            return {root: (0, root.stat().st_size, 1, 0)}
        except OSError:
            return {root: (0, 0, 0, 1)}

    stack: list[tuple[Path, int]] = [(root, 0)]
    while stack:
        current, depth = stack.pop()
        if is_path_excluded(current, excluded_roots):
            continue
        if depth <= max_depth:
            stats.setdefault(current, [depth, 0, 0, 0])
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    try:
                        entry_path = Path(entry.path)
                        if is_path_excluded(entry_path, excluded_roots):
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            if depth + 1 <= max_depth:
                                stats.setdefault(entry_path, [depth + 1, 0, 0, 0])
                            stack.append((entry_path, depth + 1))
                        elif entry.is_file(follow_symlinks=False):
                            size = entry.stat(follow_symlinks=False).st_size
                            for ancestor in monitored_ancestors(entry_path.parent, root, max_depth):
                                stats[ancestor][1] += size
                                stats[ancestor][2] += 1
                    except OSError:
                        for ancestor in monitored_ancestors(current, root, max_depth):
                            stats[ancestor][3] += 1
        except OSError:
            for ancestor in monitored_ancestors(current, root, max_depth):
                stats[ancestor][3] += 1

    return {
        path: (values[0], values[1], values[2], values[3])
        for path, values in sorted(stats.items(), key=lambda item: (item[1][0], str(item[0]).lower()))
    }


def monitored_ancestors(path: Path, root: Path, max_depth: int) -> list[Path]:
    ancestors: list[Path] = []
    current = path
    while True:
        try:
            relative = current.relative_to(root)
        except ValueError:
            break
        depth = 0 if str(relative) == "." else len(relative.parts)
        if depth <= max_depth:
            ancestors.append(current)
        if current == root:
            break
        current = current.parent
    return ancestors


def relative_to_root(path: Path, root: Path) -> str:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return str(path)
    return "." if str(relative) == "." else str(relative)


def drive_for_path(path: Path) -> str:
    anchor = path.anchor
    if anchor:
        return anchor.rstrip("\\/")
    return ""


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
