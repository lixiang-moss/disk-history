from disk_history.config import MonitorRule
from disk_history.watcher import DiskHistoryWatcher, watch_targets
from disk_history.database import DiskHistoryDatabase


def test_watch_targets_only_include_existing_enabled_paths(tmp_path):
    existing = tmp_path / "existing"
    existing.mkdir()
    missing = tmp_path / "missing"
    rules = (
        MonitorRule("Existing", str(existing), "detailed", enabled=True),
        MonitorRule("Missing", str(missing), "detailed", enabled=True),
        MonitorRule("Disabled", str(existing), "detailed", enabled=False),
    )

    targets = watch_targets(rules)

    assert len(targets) == 1
    assert targets[0].rule_name == "Existing"
    assert targets[0].path == existing


def test_disk_history_watcher_start_stop(tmp_path):
    watched = tmp_path / "watched"
    watched.mkdir()
    rules = (MonitorRule("Watched", str(watched), "detailed", enabled=True),)
    db = DiskHistoryDatabase(tmp_path / "watcher.sqlite3")
    db.initialize()
    watcher = DiskHistoryWatcher(db, rules, ignore_patterns=())

    targets = watcher.start()

    assert watcher.is_running is True
    assert len(targets) == 1

    watcher.stop()

    assert watcher.is_running is False
    assert watcher.targets == []
    db.close()
