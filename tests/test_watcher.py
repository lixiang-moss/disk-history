from disk_history.config import MonitorRule
from disk_history.privacy import PrivacyPolicy
from disk_history.watcher import DiskHistoryEventHandler, DiskHistoryWatcher, watch_targets
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


def test_watch_targets_skip_excluded_log_directory(tmp_path):
    logs = tmp_path / "logs"
    logs.mkdir()
    rules = (MonitorRule("Logs", str(logs), "detailed", enabled=True),)

    targets = watch_targets(rules, excluded_roots=(logs,))

    assert targets == []


def test_watch_targets_skip_noise_directory(tmp_path):
    noise = tmp_path / "node_modules"
    noise.mkdir()
    rules = (MonitorRule("Noise", str(noise), "detailed", enabled=True),)

    targets = watch_targets(rules, noise_roots=(noise,))

    assert targets == []


def test_event_handler_ignores_relative_noise_directory(tmp_path):
    watched = tmp_path / "watched"
    noise = watched / ".git"
    noise.mkdir(parents=True)
    (noise / "index").write_bytes(b"abc")
    db = DiskHistoryDatabase(tmp_path / "events.sqlite3")
    db.initialize()
    rules = (MonitorRule("Watched", str(watched), "detailed"),)
    handler = DiskHistoryEventHandler(
        db,
        PrivacyPolicy(rules, ignore_patterns=()),
        noise_names=(".git",),
    )

    handler._record_path("modified", noise / "index", False)

    assert db.recent_events() == []
    db.close()


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
