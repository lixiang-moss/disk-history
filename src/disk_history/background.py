from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

from disk_history.activity_log import activity_log_writer, detect_growth_alert
from disk_history.database import DiskHistoryDatabase
from disk_history.notifications import TrayNotifier
from disk_history.scanner import capture_snapshots
from disk_history.settings import AppSettings, load_settings, resolved_log_directory
from disk_history.watcher import DiskHistoryWatcher


class BackgroundRecorder:
    def __init__(
        self,
        database: DiskHistoryDatabase,
        settings: AppSettings,
    ) -> None:
        self.database = database
        self.settings = settings
        self.excluded_roots = (resolved_log_directory(settings),)
        self.log_writer = activity_log_writer(settings)
        self.last_event_log_at: datetime | None = None
        self.watcher = DiskHistoryWatcher(
            database,
            settings.monitor_rules,
            settings.ignore_patterns,
            self.excluded_roots,
        )

    def capture_once(self, notifier: TrayNotifier | None = None) -> None:
        snapshots = capture_snapshots(self.settings.monitor_rules, self.excluded_roots)
        self.database.insert_snapshots(snapshots)
        self.log_writer.append_snapshots(snapshots)

        now = snapshots[0].captured_at if snapshots else datetime.now(UTC)
        event_start = self.last_event_log_at or now - timedelta(
            minutes=self.settings.background_snapshot_interval_minutes
        )
        event_rows = self.database.events_between(event_start, now, limit=1000)
        self.log_writer.append_event_rows(event_rows, now)
        self.last_event_log_at = now

        alert = detect_growth_alert(
            self.database.snapshot_history(),
            settings=self.settings,
            now=now,
        )
        if alert is None:
            return
        self.log_writer.append_alert(alert)
        if notifier is not None:
            notifier.show_message(
                "Disk History",
                (
                    f"最近 {alert.window_minutes} 分钟监控目录净增长 "
                    f"{alert.net_growth_bytes / 1024 / 1024:.1f} MB，已写入日志。"
                ),
            )

    def start_live_monitoring(self) -> None:
        self.watcher.start()

    def stop(self) -> None:
        self.watcher.stop()

    def run_forever(self, notifier: TrayNotifier | None = None) -> None:
        self.start_live_monitoring()
        try:
            while True:
                self.capture_once(notifier)
                time.sleep(self.settings.background_snapshot_interval_minutes * 60)
        finally:
            self.stop()


def run_background() -> int:
    settings = load_settings()
    database = DiskHistoryDatabase()
    database.initialize()
    recorder = BackgroundRecorder(database, settings)
    notifier = TrayNotifier()
    try:
        recorder.run_forever(notifier)
    except KeyboardInterrupt:
        recorder.stop()
    finally:
        database.close()
    return 0
