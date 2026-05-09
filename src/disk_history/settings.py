from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from disk_history.config import (
    DEFAULT_IGNORE_PATTERNS,
    DEFAULT_MONITOR_RULES,
    DEFAULT_NOISE_RULES,
    MonitorRule,
    NoiseRule,
    app_data_dir,
    ensure_data_dir,
    existing_fixed_drives,
    expand_path_template,
)
from disk_history.focus_targets import normalized_focus_target


SETTINGS_NAME = "settings.json"


@dataclass(frozen=True)
class AppSettings:
    monitor_rules: tuple[MonitorRule, ...]
    ignore_patterns: tuple[str, ...]
    noise_rules: tuple[NoiseRule, ...] = DEFAULT_NOISE_RULES
    focus_targets: tuple[dict[str, object], ...] = ()
    language: str = "zh-CN"
    start_on_login: bool = False
    background_snapshot_interval_minutes: int = 10
    log_directory: str = r"{LOCALAPPDATA}\DiskHistory\logs"
    enable_growth_alerts: bool = True
    alert_window_minutes: int = 30
    alert_growth_threshold_mb: int = 5120
    drive_monitoring_enabled: bool = True
    monitored_drives: tuple[str, ...] = ("C:", "D:")
    standard_realtime_enabled: bool = True
    standard_tree_depth: int = 4
    standard_snapshot_interval_minutes: int = 30
    noise_snapshot_interval_minutes: int = 3
    focus_monitoring_enabled: bool = True
    focus_snapshot_interval_minutes: int = 1
    focus_tree_depth: int = 8
    focus_default_ttl_hours: int = 24


def settings_path() -> Path:
    return app_data_dir() / SETTINGS_NAME


def default_settings() -> AppSettings:
    return AppSettings(
        monitor_rules=DEFAULT_MONITOR_RULES,
        ignore_patterns=DEFAULT_IGNORE_PATTERNS,
        noise_rules=DEFAULT_NOISE_RULES,
        focus_targets=(),
        language="zh-CN",
        start_on_login=False,
        background_snapshot_interval_minutes=10,
        log_directory=r"{LOCALAPPDATA}\DiskHistory\logs",
        enable_growth_alerts=True,
        alert_window_minutes=30,
        alert_growth_threshold_mb=5120,
        drive_monitoring_enabled=True,
        monitored_drives=existing_fixed_drives(),
        standard_realtime_enabled=True,
        standard_tree_depth=4,
        standard_snapshot_interval_minutes=30,
        noise_snapshot_interval_minutes=3,
        focus_monitoring_enabled=True,
        focus_snapshot_interval_minutes=1,
        focus_tree_depth=8,
        focus_default_ttl_hours=24,
    )


def load_settings(create_if_missing: bool = True) -> AppSettings:
    path = settings_path()
    if not path.exists():
        settings = default_settings()
        if create_if_missing:
            save_settings(settings)
        return settings

    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    monitor_rules = tuple(MonitorRule.from_dict(item) for item in raw.get("monitor_rules", []))
    ignore_patterns = tuple(str(item) for item in raw.get("ignore_patterns", []))
    noise_rules = tuple(NoiseRule.from_dict(item) for item in raw.get("noise_rules", []))
    focus_targets = tuple(
        normalized_focus_target(
            dict(item),
            index=index,
            default_depth=max(1, int(raw.get("focus_tree_depth", 8))),
            default_interval_minutes=max(1, int(raw.get("focus_snapshot_interval_minutes", 1))),
            default_ttl_hours=max(1, int(raw.get("focus_default_ttl_hours", 24))),
        )
        for index, item in enumerate(raw.get("focus_targets", []))
    )
    needs_save = any(
        key not in raw
        for key in (
            "language",
            "start_on_login",
            "background_snapshot_interval_minutes",
            "log_directory",
            "enable_growth_alerts",
            "alert_window_minutes",
            "alert_growth_threshold_mb",
            "noise_rules",
            "focus_targets",
            "drive_monitoring_enabled",
            "monitored_drives",
            "standard_realtime_enabled",
            "standard_tree_depth",
            "standard_snapshot_interval_minutes",
            "noise_snapshot_interval_minutes",
            "focus_monitoring_enabled",
            "focus_snapshot_interval_minutes",
            "focus_tree_depth",
            "focus_default_ttl_hours",
        )
    )
    if not monitor_rules:
        monitor_rules = DEFAULT_MONITOR_RULES
        needs_save = True
    if not ignore_patterns:
        ignore_patterns = DEFAULT_IGNORE_PATTERNS
        needs_save = True
    if not noise_rules:
        noise_rules = DEFAULT_NOISE_RULES
        needs_save = True
    settings = AppSettings(
        monitor_rules=monitor_rules,
        ignore_patterns=ignore_patterns,
        noise_rules=noise_rules,
        focus_targets=focus_targets,
        language=str(raw.get("language", "zh-CN")),
        start_on_login=bool(raw.get("start_on_login", False)),
        background_snapshot_interval_minutes=max(
            1,
            int(raw.get("background_snapshot_interval_minutes", 10)),
        ),
        log_directory=str(raw.get("log_directory", r"{LOCALAPPDATA}\DiskHistory\logs")),
        enable_growth_alerts=bool(raw.get("enable_growth_alerts", True)),
        alert_window_minutes=max(1, int(raw.get("alert_window_minutes", 30))),
        alert_growth_threshold_mb=max(1, int(raw.get("alert_growth_threshold_mb", 5120))),
        drive_monitoring_enabled=bool(raw.get("drive_monitoring_enabled", True)),
        monitored_drives=tuple(str(item) for item in raw.get("monitored_drives", existing_fixed_drives())),
        standard_realtime_enabled=bool(raw.get("standard_realtime_enabled", True)),
        standard_tree_depth=max(1, int(raw.get("standard_tree_depth", 4))),
        standard_snapshot_interval_minutes=max(
            1,
            int(raw.get("standard_snapshot_interval_minutes", 30)),
        ),
        noise_snapshot_interval_minutes=max(1, int(raw.get("noise_snapshot_interval_minutes", 3))),
        focus_monitoring_enabled=bool(raw.get("focus_monitoring_enabled", True)),
        focus_snapshot_interval_minutes=max(1, int(raw.get("focus_snapshot_interval_minutes", 1))),
        focus_tree_depth=max(1, int(raw.get("focus_tree_depth", 8))),
        focus_default_ttl_hours=max(1, int(raw.get("focus_default_ttl_hours", 24))),
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
        "log_directory": settings.log_directory,
        "enable_growth_alerts": settings.enable_growth_alerts,
        "alert_window_minutes": settings.alert_window_minutes,
        "alert_growth_threshold_mb": settings.alert_growth_threshold_mb,
        "monitor_rules": [rule.to_dict() for rule in settings.monitor_rules],
        "ignore_patterns": list(settings.ignore_patterns),
        "noise_rules": [rule.to_dict() for rule in settings.noise_rules],
        "focus_targets": list(settings.focus_targets),
        "drive_monitoring_enabled": settings.drive_monitoring_enabled,
        "monitored_drives": list(settings.monitored_drives),
        "standard_realtime_enabled": settings.standard_realtime_enabled,
        "standard_tree_depth": settings.standard_tree_depth,
        "standard_snapshot_interval_minutes": settings.standard_snapshot_interval_minutes,
        "noise_snapshot_interval_minutes": settings.noise_snapshot_interval_minutes,
        "focus_monitoring_enabled": settings.focus_monitoring_enabled,
        "focus_snapshot_interval_minutes": settings.focus_snapshot_interval_minutes,
        "focus_tree_depth": settings.focus_tree_depth,
        "focus_default_ttl_hours": settings.focus_default_ttl_hours,
    }
    settings_path().write_text(json.dumps(data, indent=2), encoding="utf-8")


def resolved_log_directory(settings: AppSettings) -> Path:
    return expand_path_template(settings.log_directory)


def resolved_focus_log_directory() -> Path:
    return app_data_dir() / "focus_logs"
