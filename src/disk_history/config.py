from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from string import ascii_uppercase


APP_NAME = "DiskHistory"
DB_NAME = "disk_history.sqlite3"


@dataclass(frozen=True)
class MonitorRule:
    name: str
    path_template: str
    privacy_mode: str
    enabled: bool = True
    recursive: bool = True

    def resolved_path(self) -> Path:
        return expand_path_template(self.path_template)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "path_template": self.path_template,
            "privacy_mode": self.privacy_mode,
            "enabled": self.enabled,
            "recursive": self.recursive,
        }

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> "MonitorRule":
        return cls(
            name=str(value["name"]),
            path_template=str(value["path_template"]),
            privacy_mode=str(value["privacy_mode"]),
            enabled=bool(value.get("enabled", True)),
            recursive=bool(value.get("recursive", True)),
        )


@dataclass(frozen=True)
class NoiseRule:
    name: str
    path_template: str
    enabled: bool = True

    def resolved_path(self) -> Path:
        return expand_path_template(self.path_template)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "path_template": self.path_template,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> "NoiseRule":
        return cls(
            name=str(value["name"]),
            path_template=str(value["path_template"]),
            enabled=bool(value.get("enabled", True)),
        )


@dataclass(frozen=True)
class FocusTargetConfig:
    name: str
    path_template: str
    enabled: bool = True
    max_depth: int = 8
    snapshot_interval_minutes: int = 1
    ttl_hours: int = 24

    def resolved_path(self) -> Path:
        return expand_path_template(self.path_template)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "path_template": self.path_template,
            "enabled": self.enabled,
            "max_depth": self.max_depth,
            "snapshot_interval_minutes": self.snapshot_interval_minutes,
            "ttl_hours": self.ttl_hours,
        }

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> "FocusTargetConfig":
        return cls(
            name=str(value["name"]),
            path_template=str(value["path_template"]),
            enabled=bool(value.get("enabled", True)),
            max_depth=max(1, int(value.get("max_depth", 8))),
            snapshot_interval_minutes=max(1, int(value.get("snapshot_interval_minutes", 1))),
            ttl_hours=max(1, int(value.get("ttl_hours", 24))),
        )


DEFAULT_MONITOR_RULES: tuple[MonitorRule, ...] = (
    MonitorRule("C Drive", "C:\\", "detailed"),
    MonitorRule("D Drive", "D:\\", "detailed"),
)


DEFAULT_IGNORE_PATTERNS: tuple[str, ...] = (
    "*.tmp",
    "*.lock",
)


DEFAULT_NOISE_RULES: tuple[NoiseRule, ...] = (
    NoiseRule("User Temp", r"{LOCALAPPDATA}\Temp"),
    NoiseRule("Windows Temp", r"{SYSTEMROOT}\Temp"),
    NoiseRule("Browser Cache", r"Cache"),
    NoiseRule("Code Cache", r"Code Cache"),
    NoiseRule("GPU Cache", r"GPUCache"),
    NoiseRule("Git Metadata", r".git"),
    NoiseRule("Node Modules", r"node_modules"),
    NoiseRule("Python Virtual Env", r".venv"),
    NoiseRule("Python Cache", r"__pycache__"),
    NoiseRule("Build Output", r"build"),
    NoiseRule("Dist Output", r"dist"),
    NoiseRule("Rust Target", r"target"),
    NoiseRule("Windows Update Download", r"{SYSTEMROOT}\SoftwareDistribution\Download"),
    NoiseRule("Package Cache", r"{PROGRAMDATA}\Package Cache"),
)


DEFAULT_EXCLUDED_PATHS: tuple[str, ...] = (
    r"{LOCALAPPDATA}\DiskHistory\logs",
    r"{LOCALAPPDATA}\DiskHistory\exports",
    r"{LOCALAPPDATA}\DiskHistory\focus_logs",
    r"{LOCALAPPDATA}\DiskHistory\disk_history.sqlite3",
    r"C:\System Volume Information",
    r"C:\$Extend",
    r"C:\$LogFile",
    r"C:\$MFT",
    r"C:\$Secure",
    r"C:\$Boot",
    r"C:\$BadClus",
    r"C:\$Bitmap",
    r"C:\$UpCase",
    r"C:\pagefile.sys",
    r"C:\hiberfil.sys",
    r"C:\swapfile.sys",
)


def app_data_dir() -> Path:
    configured = os.environ.get("DISK_HISTORY_HOME")
    if configured:
        return Path(configured).expanduser()

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / APP_NAME

    return Path.home() / f".{APP_NAME.lower()}"


def database_path() -> Path:
    return app_data_dir() / DB_NAME


def expand_path_template(path_template: str) -> Path:
    values = {
        "USERPROFILE": os.environ.get("USERPROFILE", str(Path.home())),
        "LOCALAPPDATA": os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")),
        "APPDATA": os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")),
        "PROGRAMDATA": os.environ.get("PROGRAMDATA", r"C:\ProgramData"),
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", r"C:\Windows"),
    }
    expanded = path_template
    for key, value in values.items():
        expanded = expanded.replace("{" + key + "}", value)
    return Path(os.path.expandvars(os.path.expanduser(expanded)))


def ensure_data_dir() -> Path:
    path = app_data_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def existing_fixed_drives(preferred: tuple[str, ...] = ("C:", "D:")) -> tuple[str, ...]:
    drives: list[str] = []
    candidates = list(preferred) + [f"{letter}:" for letter in ascii_uppercase]
    for drive in candidates:
        normalized = drive.upper().rstrip("\\/")
        if normalized in drives:
            continue
        if Path(normalized + "\\").exists():
            drives.append(normalized)
    return tuple(drives)
