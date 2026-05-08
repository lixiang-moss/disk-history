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
    )
    db = DiskHistoryDatabase(tmp_path / "background.sqlite3")
    db.initialize()
    recorder = BackgroundRecorder(db, settings)

    recorder.capture_once()

    snapshots = db.latest_snapshots()
    assert len(snapshots) == 1
    assert snapshots[0]["rule_name"] == "Watched"
    assert snapshots[0]["size_bytes"] == 3
    db.close()
