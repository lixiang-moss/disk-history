from __future__ import annotations

import argparse
from datetime import timedelta

from disk_history.activity_log import activity_log_writer, detect_growth_alert
from disk_history.config import database_path
from disk_history.background import focus_roots_from_settings
from disk_history.database import DiskHistoryDatabase
from disk_history.scanner import (
    capture_drive_snapshots,
    capture_focus_snapshots,
    capture_noise_snapshots,
    capture_snapshots,
    capture_tree_snapshots,
    default_excluded_roots,
    format_bytes,
    tree_roots_from_monitor_rules,
)
from disk_history.settings import (
    load_settings,
    resolved_focus_log_directory,
    resolved_log_directory,
    settings_path,
)
from disk_history.watcher import run_watcher


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="disk-history")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("init-db", help="Create or upgrade the local database.")
    subparsers.add_parser("config-path", help="Show the local settings file path.")
    subparsers.add_parser("scan", help="Capture one directory size snapshot.")
    subparsers.add_parser("recent", help="Show recent recorded filesystem events.")
    subparsers.add_parser("watch", help="Run the filesystem watcher in the foreground.")
    subparsers.add_parser("background", help="Run background snapshots and live monitoring.")
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
        excluded_roots = default_excluded_roots(
            (resolved_log_directory(settings), resolved_focus_log_directory())
        )
        snapshots = capture_snapshots(settings.monitor_rules, excluded_roots)
        db.insert_snapshots(snapshots)
        if settings.drive_monitoring_enabled:
            db.insert_drive_snapshots(capture_drive_snapshots(settings.monitored_drives))
        db.insert_tree_snapshots(
            capture_tree_snapshots(
                tree_roots_from_monitor_rules(settings.monitor_rules, excluded_roots),
                max_depth=settings.standard_tree_depth,
                excluded_roots=excluded_roots,
            )
        )
        db.insert_tree_snapshots(capture_noise_snapshots(settings.noise_rules, excluded_roots=excluded_roots))
        db.insert_focus_snapshots(
            capture_focus_snapshots(
                settings.focus_targets,
                max_depth=settings.focus_tree_depth,
                excluded_roots=excluded_roots,
            )
        )
        writer = activity_log_writer(settings)
        writer.append_snapshots(snapshots)
        if snapshots:
            now = snapshots[0].captured_at
            writer.append_event_rows(
                db.events_between(
                    now - timedelta(minutes=settings.alert_window_minutes),
                    now,
                    limit=1000,
                ),
                now,
            )
            alert = detect_growth_alert(db.snapshot_history(), settings=settings, now=now)
            if alert is not None:
                writer.append_alert(alert)
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
        excluded_roots = default_excluded_roots(
            (resolved_log_directory(settings), resolved_focus_log_directory())
        )
        run_watcher(
            db,
            settings.monitor_rules,
            settings.ignore_patterns,
            excluded_roots,
            settings.noise_rules,
            focus_roots_from_settings(settings),
        )
        return 0

    if command == "background":
        from disk_history.background import run_background

        db.close()
        return run_background()

    parser.print_help()
    return 2
