from __future__ import annotations

import argparse

from disk_history.config import database_path
from disk_history.database import DiskHistoryDatabase
from disk_history.scanner import capture_snapshots, format_bytes
from disk_history.settings import load_settings, settings_path
from disk_history.watcher import run_watcher


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="disk-history")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("init-db", help="Create or upgrade the local database.")
    subparsers.add_parser("config-path", help="Show the local settings file path.")
    subparsers.add_parser("scan", help="Capture one directory size snapshot.")
    subparsers.add_parser("recent", help="Show recent recorded filesystem events.")
    subparsers.add_parser("watch", help="Run the filesystem watcher in the foreground.")
    subparsers.add_parser("gui", help="Open the desktop interface.")

    args = parser.parse_args(argv)
    command = args.command or "gui"

    if command == "gui":
        from disk_history.app import run_app

        return run_app()

    db = DiskHistoryDatabase()
    db.initialize()

    if command == "init-db":
        print(f"Database ready: {database_path()}")
        return 0

    if command == "config-path":
        load_settings(create_if_missing=True)
        print(f"Settings file: {settings_path()}")
        return 0

    if command == "scan":
        settings = load_settings()
        snapshots = capture_snapshots(settings.monitor_rules)
        db.insert_snapshots(snapshots)
        for snapshot in snapshots:
            exists = "exists" if snapshot.exists else "missing"
            print(
                f"{snapshot.rule_name}: {format_bytes(snapshot.size_bytes)} "
                f"({snapshot.file_count} files, {exists})"
            )
        return 0

    if command == "recent":
        rows = db.recent_events()
        for row in rows:
            delta = format_bytes(row["delta_bytes"])
            print(f"{row['happened_at']} {row['event_type']} {delta} {row['display_path']}")
        return 0

    if command == "watch":
        settings = load_settings()
        run_watcher(db, settings.monitor_rules, settings.ignore_patterns)
        return 0

    parser.print_help()
    return 2
