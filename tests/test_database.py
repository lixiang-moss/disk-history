from datetime import UTC, datetime

from disk_history.database import DiskHistoryDatabase, FileEvent


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

