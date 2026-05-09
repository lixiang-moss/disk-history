from datetime import UTC, datetime
from threading import Thread

from disk_history.database import DiskHistoryDatabase, DriveSnapshot, FileEvent, FocusSnapshot, TreeSnapshot


def test_database_inserts_and_reads_event(tmp_path):
    db = DiskHistoryDatabase(tmp_path / "test.sqlite3")
    db.initialize()

    db.insert_event(
        FileEvent(
            happened_at=datetime(2026, 5, 6, tzinfo=UTC),
            event_type="created",
            privacy_mode="detailed",
            category="Downloads",
            display_path=r"C:\Users\Example\Downloads\a.bin",
            path=r"C:\Users\Example\Downloads\a.bin",
            size_after=10,
            delta_bytes=10,
        )
    )

    rows = db.recent_events()

    assert len(rows) == 1
    assert rows[0]["event_type"] == "created"
    assert rows[0]["delta_bytes"] == 10
    db.close()


def test_database_accepts_background_thread_writes(tmp_path):
    db = DiskHistoryDatabase(tmp_path / "threaded.sqlite3")
    db.initialize()

    def write_event() -> None:
        db.insert_event(
            FileEvent(
                happened_at=datetime(2026, 5, 6, tzinfo=UTC),
                event_type="created",
                privacy_mode="detailed",
                category="Thread",
                display_path="threaded.bin",
                path="threaded.bin",
                size_after=1,
                delta_bytes=1,
            )
        )

    thread = Thread(target=write_event)
    thread.start()
    thread.join()

    assert db.recent_events()[0]["category"] == "Thread"
    db.close()


def test_database_filters_events_between_times(tmp_path):
    db = DiskHistoryDatabase(tmp_path / "events.sqlite3")
    db.initialize()
    early = datetime(2026, 5, 6, 8, tzinfo=UTC)
    late = datetime(2026, 5, 6, 10, tzinfo=UTC)
    for happened_at, category in ((early, "Early"), (late, "Late")):
        db.insert_event(
            FileEvent(
                happened_at=happened_at,
                event_type="created",
                privacy_mode="detailed",
                category=category,
                display_path=category,
                path=category,
                delta_bytes=1,
            )
        )

    rows = db.events_between(
        datetime(2026, 5, 6, 9, tzinfo=UTC),
        datetime(2026, 5, 6, 11, tzinfo=UTC),
    )

    assert len(rows) == 1
    assert rows[0]["category"] == "Late"
    db.close()


def test_database_stores_drive_tree_and_focus_snapshots(tmp_path):
    db = DiskHistoryDatabase(tmp_path / "snapshots.sqlite3")
    db.initialize()
    captured_at = datetime(2026, 5, 6, tzinfo=UTC)

    db.insert_drive_snapshots((DriveSnapshot(captured_at, "C:", 100, 40, 60),))
    db.insert_tree_snapshots(
        (
            TreeSnapshot(
                captured_at=captured_at,
                drive="C:",
                path=r"C:\Project",
                relative_path="Project",
                depth=1,
                size_bytes=10,
                file_count=1,
                error_count=0,
                strategy="standard",
            ),
        )
    )
    db.insert_focus_snapshots(
        (
            FocusSnapshot(
                captured_at=captured_at,
                target_id="focus-1",
                target_name="Focus",
                path=r"C:\Project",
                relative_path=".",
                depth=0,
                size_bytes=10,
                file_count=1,
                error_count=0,
            ),
        )
    )

    assert db.latest_drive_snapshots()[0]["used_bytes"] == 40
    assert db.latest_tree_snapshots()[0]["strategy"] == "standard"
    db.close()


def test_database_filters_events_by_source_strategy(tmp_path):
    db = DiskHistoryDatabase(tmp_path / "strategy.sqlite3")
    db.initialize()
    happened_at = datetime(2026, 5, 6, tzinfo=UTC)
    db.insert_event(
        FileEvent(
            happened_at=happened_at,
            event_type="created",
            privacy_mode="detailed",
            category="standard",
            display_path="standard",
            path="standard",
            source_strategy="standard",
        )
    )
    db.insert_event(
        FileEvent(
            happened_at=happened_at,
            event_type="created",
            privacy_mode="detailed",
            category="focus",
            display_path="focus",
            path="focus",
            source_strategy="focus",
        )
    )

    rows = db.events_between(happened_at, happened_at, source_strategy="focus")

    assert len(rows) == 1
    assert rows[0]["category"] == "focus"
    db.close()
