from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


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


DEFAULT_MONITOR_RULES: tuple[MonitorRule, ...] = (
    MonitorRule("Downloads", r"{USERPROFILE}\Downloads", "detailed"),
    MonitorRule("Temp", r"{LOCALAPPDATA}\Temp", "detailed"),
    MonitorRule("Local Programs", r"{LOCALAPPDATA}\Programs", "detailed"),
    MonitorRule("VS Code Extensions", r"{USERPROFILE}\.vscode\extensions", "detailed"),
    MonitorRule("Package Cache", r"{PROGRAMDATA}\Package Cache", "detailed"),
    MonitorRule("Windows Update Download", r"{SYSTEMROOT}\SoftwareDistribution\Download", "summary"),
    MonitorRule("Documents", r"{USERPROFILE}\Documents", "summary"),
    MonitorRule("Desktop", r"{USERPROFILE}\Desktop", "summary"),
    MonitorRule("Pictures", r"{USERPROFILE}\Pictures", "summary"),
    MonitorRule("Videos", r"{USERPROFILE}\Videos", "summary"),
    MonitorRule("OneDrive", r"{USERPROFILE}\OneDrive", "summary"),
)


DEFAULT_IGNORE_PATTERNS: tuple[str, ...] = (
    "*.tmp",
    "*.lock",
    "*.log",
    "*/Cache/*",
    "*/Code Cache/*",
    "*/GPUCache/*",
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
