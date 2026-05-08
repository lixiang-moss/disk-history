from __future__ import annotations

import time

from disk_history.database import DiskHistoryDatabase
from disk_history.scanner import capture_snapshots
from disk_history.settings import AppSettings, load_settings
from disk_history.watcher import DiskHistoryWatcher


class BackgroundRecorder:
    def __init__(
        self,
        database: DiskHistoryDatabase,
        settings: AppSettings,
    ) -> None:
        self.database = database
        self.settings = settings
        self.watcher = DiskHistoryWatcher(
            database,
            settings.monitor_rules,
            settings.ignore_patterns,
        )

    def capture_once(self) -> None:
        snapshots = capture_snapshots(self.settings.monitor_rules)
        self.database.insert_snapshots(snapshots)

    def start_live_monitoring(self) -> None:
        self.watcher.start()

    def stop(self) -> None:
        self.watcher.stop()

    def run_forever(self) -> None:
        self.start_live_monitoring()
        try:
            while True:
                self.capture_once()
                time.sleep(self.settings.background_snapshot_interval_minutes * 60)
        finally:
            self.stop()


def run_background() -> int:
    settings = load_settings()
    database = DiskHistoryDatabase()
    database.initialize()
    recorder = BackgroundRecorder(database, settings)
    try:
        recorder.run_forever()
    except KeyboardInterrupt:
        recorder.stop()
    finally:
        database.close()
    return 0

