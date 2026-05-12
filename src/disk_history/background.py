from __future__ import annotations

import time
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from disk_history.activity_log import activity_log_writer, detect_growth_alert
from disk_history.database import DiskHistoryDatabase, GrowthAlertRecord
from disk_history.focus_targets import active_focus_roots
from disk_history.focus_log import FocusLogWriter
from disk_history.notifications import TrayNotifier
from disk_history.scanner import (
    capture_drive_snapshots,
    capture_focus_snapshots,
    capture_noise_snapshots,
    capture_snapshots,
    capture_tree_snapshots,
    default_excluded_roots,
    tree_roots_from_monitor_rules,
)
from disk_history.settings import (
    AppSettings,
    load_settings,
    resolved_focus_log_directory,
    resolved_log_directory,
)
from disk_history.watcher import DiskHistoryWatcher


class BackgroundRecorder:
    def __init__(
        self,
        database: DiskHistoryDatabase,
        settings: AppSettings,
    ) -> None:
        self.database = database
        self.settings = settings
        self.excluded_roots = default_excluded_roots(
            (resolved_log_directory(settings), resolved_focus_log_directory())
        )
        self.log_writer = activity_log_writer(settings)
        self.focus_log_writer = FocusLogWriter(resolved_focus_log_directory())
        self.last_event_log_at: datetime | None = None
        self.last_standard_snapshot_at: datetime | None = None
        self.last_noise_snapshot_at: datetime | None = None
        self.last_focus_snapshot_at: datetime | None = None
        self.stop_requested = False
        self.watcher = DiskHistoryWatcher(
            database,
            settings.monitor_rules,
            settings.ignore_patterns,
            self.excluded_roots,
            settings.noise_rules,
            focus_roots_from_settings(settings),
        )

    def capture_once(self, notifier: TrayNotifier | None = None) -> None:
        now = datetime.now(UTC)
        directory_snapshots = []

        if self._should_capture(
            self.last_standard_snapshot_at,
            self.settings.standard_snapshot_interval_minutes,
        ):
            directory_snapshots = capture_snapshots(self.settings.monitor_rules, self.excluded_roots)
            self.database.insert_snapshots(directory_snapshots)
            self.log_writer.append_snapshots(directory_snapshots)

            if self.settings.drive_monitoring_enabled:
                self.database.insert_drive_snapshots(
                    capture_drive_snapshots(self.settings.monitored_drives)
                )

            self.database.insert_tree_snapshots(
                capture_tree_snapshots(
                    tree_roots_from_monitor_rules(self.settings.monitor_rules, self.excluded_roots),
                    max_depth=self.settings.standard_tree_depth,
                    excluded_roots=self.excluded_roots,
                )
            )
            self.last_standard_snapshot_at = now

        if self._should_capture(
            self.last_noise_snapshot_at,
            self.settings.noise_snapshot_interval_minutes,
        ):
            self.database.insert_tree_snapshots(
                capture_noise_snapshots(
                    self.settings.noise_rules,
                    excluded_roots=self.excluded_roots,
                )
            )
            self.last_noise_snapshot_at = now

        if self.settings.focus_monitoring_enabled and self._should_capture(
            self.last_focus_snapshot_at,
            self.settings.focus_snapshot_interval_minutes,
        ):
            focus_snapshots = capture_focus_snapshots(
                self.settings.focus_targets,
                max_depth=self.settings.focus_tree_depth,
                excluded_roots=self.excluded_roots,
            )
            self.database.insert_focus_snapshots(focus_snapshots)
            self.focus_log_writer.append_snapshots(focus_snapshots)
            self.last_focus_snapshot_at = now

        capture_time = directory_snapshots[0].captured_at if directory_snapshots else now
        event_start = self.last_event_log_at or capture_time - timedelta(
            minutes=self.settings.background_snapshot_interval_minutes
        )
        event_rows = self.database.events_between(event_start, capture_time, limit=1000)
        self.log_writer.append_event_rows(event_rows, capture_time)
        focus_event_rows = self.database.events_between(
            event_start,
            capture_time,
            limit=1000,
            source_strategy="focus",
        )
        self.focus_log_writer.append_event_rows(focus_event_rows, moment=capture_time)
        self.last_event_log_at = capture_time

        alert = detect_growth_alert(
            self.database.snapshot_history(),
            settings=self.settings,
            now=capture_time,
        )
        if alert is None:
            return

        self.log_writer.append_alert(alert)
        self.database.insert_growth_alert(
            GrowthAlertRecord(
                happened_at=alert.happened_at,
                scope="directory",
                subject="monitored_rules",
                window_minutes=alert.window_minutes,
                threshold_bytes=alert.threshold_bytes,
                net_growth_bytes=alert.net_growth_bytes,
                details_json=json.dumps(alert.top_growth, ensure_ascii=False),
            )
        )
        if notifier is not None:
            notifier.show_message(
                "Disk History",
                (
                    f"最近 {alert.window_minutes} 分钟监控目录净增长 "
                    f"{alert.net_growth_bytes / 1024 / 1024:.1f} MB，已写入日志。"
                ),
            )

    def _should_capture(self, previous: datetime | None, interval_minutes: int) -> bool:
        if previous is None:
            return True
        return datetime.now(UTC) - previous >= timedelta(minutes=interval_minutes)

    def start_live_monitoring(self) -> None:
        if self.settings.standard_realtime_enabled:
            self.watcher.start()

    def stop(self) -> None:
        self.watcher.stop()

    def request_stop(self) -> None:
        self.stop_requested = True

    def run_forever(
        self,
        notifier: TrayNotifier | None = None,
        *,
        capture_interval_seconds: float = 60,
        event_poll_seconds: float = 0.5,
    ) -> None:
        self.start_live_monitoring()
        try:
            while not self.stop_requested:
                self.capture_once(notifier)
                self._wait_between_captures(
                    notifier,
                    capture_interval_seconds=capture_interval_seconds,
                    event_poll_seconds=event_poll_seconds,
                )
        finally:
            self.stop()

    def _wait_between_captures(
        self,
        notifier: TrayNotifier | None,
        *,
        capture_interval_seconds: float,
        event_poll_seconds: float,
    ) -> None:
        deadline = time.monotonic() + capture_interval_seconds
        while not self.stop_requested:
            if notifier is not None:
                notifier.process_events()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            time.sleep(min(event_poll_seconds, remaining))


def focus_roots_from_settings(settings: AppSettings) -> tuple[Path, ...]:
    return active_focus_roots(settings.focus_targets)


def run_background() -> int:
    settings = load_settings()
    database = DiskHistoryDatabase()
    database.initialize()
    recorder = BackgroundRecorder(database, settings)
    notifier = TrayNotifier(on_quit=recorder.request_stop)
    try:
        recorder.run_forever(notifier)
    except KeyboardInterrupt:
        recorder.request_stop()
    finally:
        notifier.close()
        recorder.stop()
        database.close()
    return 0
