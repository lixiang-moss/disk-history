from __future__ import annotations

from pathlib import Path


def is_path_within(path: Path, root: Path) -> bool:
    try:
        resolved_path = path.resolve()
        resolved_root = root.resolve()
    except OSError:
        resolved_path = path.absolute()
        resolved_root = root.absolute()

    return resolved_path == resolved_root or resolved_root in resolved_path.parents


def is_path_excluded(path: Path, excluded_roots: tuple[Path, ...]) -> bool:
    return any(is_path_within(path, root) for root in excluded_roots)

