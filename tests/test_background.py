from disk_history.background import BackgroundRecorder
from disk_history.config import MonitorRule
from disk_history.database import DiskHistoryDatabase
from disk_history.settings import AppSettings


def test_background_recorder_capture_once(tmp_path):
    watched = tmp_path / "watched"
    watched.mkdir()
    (watched / "file.bin").write_bytes(b"abc")
    settings = AppSettings(
        monitor_rules=(MonitorRule("Watched", str(watched), "detailed"),),
        ignore_patterns=(),
        log_directory=str(tmp_path / "logs"),
    )
    db = DiskHistoryDatabase(tmp_path / "background.sqlite3")
    db.initialize()
    recorder = BackgroundRecorder(db, settings)

    recorder.capture_once()

    snapshots = db.latest_snapshots()
    assert len(snapshots) == 1
    assert snapshots[0]["rule_name"] == "Watched"
    assert snapshots[0]["size_bytes"] == 3
    assert (tmp_path / "logs").exists()
    db.close()


def test_background_recorder_can_stop_run_loop(tmp_path):
    settings = AppSettings(
        monitor_rules=(),
        ignore_patterns=(),
        log_directory=str(tmp_path / "logs"),
    )
    db = DiskHistoryDatabase(tmp_path / "background.sqlite3")
    db.initialize()

    class StopAfterFirstCapture(BackgroundRecorder):
        def __init__(self, database, app_settings):
            super().__init__(database, app_settings)
            self.capture_count = 0
            self.stopped = False

        def start_live_monitoring(self):
            return None

        def capture_once(self, notifier=None):
            self.capture_count += 1
            self.request_stop()

        def stop(self):
            self.stopped = True

    recorder = StopAfterFirstCapture(db, settings)

    recorder.run_forever(capture_interval_seconds=0.01, event_poll_seconds=0.01)

    assert recorder.capture_count == 1
    assert recorder.stop_requested is True
    assert recorder.stopped is True
    db.close()
