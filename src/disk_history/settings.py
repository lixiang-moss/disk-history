from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from disk_history.config import (
    DEFAULT_IGNORE_PATTERNS,
    DEFAULT_MONITOR_RULES,
    MonitorRule,
    app_data_dir,
    ensure_data_dir,
)


SETTINGS_NAME = "settings.json"


@dataclass(frozen=True)
class AppSettings:
    monitor_rules: tuple[MonitorRule, ...]
    ignore_patterns: tuple[str, ...]
    language: str = "zh-CN"
    start_on_login: bool = False
    background_snapshot_interval_minutes: int = 10


def settings_path() -> Path:
    return app_data_dir() / SETTINGS_NAME


def default_settings() -> AppSettings:
    return AppSettings(
        monitor_rules=DEFAULT_MONITOR_RULES,
        ignore_patterns=DEFAULT_IGNORE_PATTERNS,
        language="zh-CN",
        start_on_login=False,
        background_snapshot_interval_minutes=10,
    )


def load_settings(create_if_missing: bool = True) -> AppSettings:
    path = settings_path()
    if not path.exists():
        settings = default_settings()
        if create_if_missing:
            save_settings(settings)
        return settings

    raw = json.loads(path.read_text(encoding="utf-8"))
    monitor_rules = tuple(MonitorRule.from_dict(item) for item in raw.get("monitor_rules", []))
    ignore_patterns = tuple(str(item) for item in raw.get("ignore_patterns", []))
    needs_save = any(
        key not in raw
        for key in ("language", "start_on_login", "background_snapshot_interval_minutes")
    )
    if not monitor_rules:
        monitor_rules = DEFAULT_MONITOR_RULES
        needs_save = True
    if not ignore_patterns:
        ignore_patterns = DEFAULT_IGNORE_PATTERNS
        needs_save = True
    settings = AppSettings(
        monitor_rules=monitor_rules,
        ignore_patterns=ignore_patterns,
        language=str(raw.get("language", "zh-CN")),
        start_on_login=bool(raw.get("start_on_login", False)),
        background_snapshot_interval_minutes=max(
            1,
            int(raw.get("background_snapshot_interval_minutes", 10)),
        ),
    )
    if create_if_missing and needs_save:
        save_settings(settings)
    return settings


def save_settings(settings: AppSettings) -> None:
    ensure_data_dir()
    data = {
        "language": settings.language,
        "start_on_login": settings.start_on_login,
        "background_snapshot_interval_minutes": settings.background_snapshot_interval_minutes,
        "monitor_rules": [rule.to_dict() for rule in settings.monitor_rules],
        "ignore_patterns": list(settings.ignore_patterns),
    }
    settings_path().write_text(json.dumps(data, indent=2), encoding="utf-8")
