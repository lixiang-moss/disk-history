from __future__ import annotations

import os
from pathlib import Path


def is_path_within(path: Path, root: Path) -> bool:
    normalized_path = _normalized_path(path)
    normalized_root = _normalized_path(root)
    if normalized_path == normalized_root:
        return True
    root_prefix = normalized_root.rstrip("\\/") + os.sep
    return normalized_path.startswith(root_prefix)


def is_path_excluded(path: Path, excluded_roots: tuple[Path, ...]) -> bool:
    return any(is_path_within(path, root) for root in excluded_roots)


def _normalized_path(path: Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))
