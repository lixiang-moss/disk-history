from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


STARTUP_NAME = "DiskHistoryBackground.lnk"


def startup_folder() -> Path:
    configured = os.environ.get("DISK_HISTORY_STARTUP_DIR")
    if configured:
        return Path(configured)

    appdata = os.environ.get("APPDATA")
    if not appdata:
        return Path.home()
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def startup_shortcut_path() -> Path:
    return startup_folder() / STARTUP_NAME


def is_start_on_login_enabled() -> bool:
    return startup_shortcut_path().exists()


def startup_command(python_executable: str | None = None) -> tuple[str, str]:
    executable = python_executable or sys.executable
    return executable, "-m disk_history background"


def enable_start_on_login(
    *,
    python_executable: str | None = None,
    working_directory: Path | None = None,
) -> Path:
    folder = startup_folder()
    folder.mkdir(parents=True, exist_ok=True)
    shortcut = startup_shortcut_path()
    target, arguments = startup_command(python_executable)
    working_dir = str(working_directory or Path.cwd())

    script = f"""
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut('{_ps_escape(str(shortcut))}')
$shortcut.TargetPath = '{_ps_escape(target)}'
$shortcut.Arguments = '{_ps_escape(arguments)}'
$shortcut.WorkingDirectory = '{_ps_escape(working_dir)}'
$shortcut.Description = 'Disk History background recorder'
$shortcut.Save()
"""
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        check=True,
        capture_output=True,
        text=True,
    )
    return shortcut


def disable_start_on_login() -> None:
    shortcut = startup_shortcut_path()
    if shortcut.exists():
        shortcut.unlink()


def _ps_escape(value: str) -> str:
    return value.replace("'", "''")

