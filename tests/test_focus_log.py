from datetime import UTC, datetime

from disk_history.database import FocusSnapshot
from disk_history.focus_log import FocusLogWriter


def test_focus_log_writer_creates_independent_logs(tmp_path):
    writer = FocusLogWriter(tmp_path)
    captured_at = datetime(2026, 5, 9, 12, tzinfo=UTC)

    writer.append_snapshots(
        (
            FocusSnapshot(
                captured_at=captured_at,
                target_id="case-1",
                target_name="可疑目录",
                path=r"C:\Project",
                relative_path=".",
                depth=0,
                size_bytes=10,
                file_count=1,
                error_count=0,
            ),
        )
    )

    target_dirs = list((tmp_path / "2026-05-09").iterdir())

    assert len(target_dirs) == 1
    assert (target_dirs[0] / "summary.md").exists()
    assert (target_dirs[0] / "snapshots.jsonl").read_text(encoding="utf-8")
