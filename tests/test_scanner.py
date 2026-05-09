from datetime import datetime, timedelta, timezone

from disk_history.config import MonitorRule, NoiseRule
from disk_history.scanner import (
    TreeRoot,
    capture_focus_snapshots,
    capture_noise_snapshots,
    capture_tree_snapshots,
    child_size_rankings,
    directory_size,
    format_bytes,
    tree_roots_from_monitor_rules,
)


def test_directory_size_counts_files(tmp_path):
    (tmp_path / "a.txt").write_bytes(b"abc")
    folder = tmp_path / "folder"
    folder.mkdir()
    (folder / "b.txt").write_bytes(b"de")

    result = directory_size(tmp_path)

    assert result.exists is True
    assert result.size_bytes == 5
    assert result.file_count == 2


def test_directory_size_skips_excluded_log_directory(tmp_path):
    (tmp_path / "data.bin").write_bytes(b"abc")
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "summary.md").write_bytes(b"ignored")

    result = directory_size(tmp_path, excluded_roots=(logs,))

    assert result.exists is True
    assert result.size_bytes == 3
    assert result.file_count == 1


def test_child_size_rankings_orders_immediate_children(tmp_path):
    small = tmp_path / "small"
    small.mkdir()
    (small / "a.bin").write_bytes(b"abc")
    large = tmp_path / "large"
    large.mkdir()
    (large / "b.bin").write_bytes(b"abcdef")
    (tmp_path / "file.txt").write_bytes(b"zz")

    rows = child_size_rankings(tmp_path)

    assert [row.name for row in rows] == ["large", "small", "file.txt"]
    assert rows[0].size_bytes == 6


def test_format_bytes():
    assert format_bytes(1024) == "1.0 KB"
    assert format_bytes(None) == "unknown"


def test_capture_tree_snapshots_respects_depth(tmp_path):
    level1 = tmp_path / "level1"
    level2 = level1 / "level2"
    level2.mkdir(parents=True)
    (level2 / "file.bin").write_bytes(b"abc")

    snapshots = capture_tree_snapshots(
        (TreeRoot("Root", tmp_path, "", "standard"),),
        max_depth=1,
    )

    assert {snapshot.relative_path for snapshot in snapshots} == {".", "level1"}


def test_tree_roots_skip_excluded_disk_history_data(tmp_path):
    logs = tmp_path / "logs"
    logs.mkdir()

    roots = tree_roots_from_monitor_rules(
        (MonitorRule("Logs", str(logs), "detailed"),),
        excluded_roots=(logs,),
    )

    assert roots == ()


def test_noise_snapshot_uses_snapshot_only_strategy(tmp_path):
    noise = tmp_path / "node_modules"
    noise.mkdir()
    (noise / "package.bin").write_bytes(b"abc")

    snapshots = capture_noise_snapshots((NoiseRule("Node Modules", str(noise)),))

    assert len(snapshots) == 1
    assert snapshots[0].strategy == "noise_snapshot_only"
    assert snapshots[0].size_bytes == 3


def test_focus_snapshots_use_deeper_depth(tmp_path):
    root = tmp_path / "focus"
    deep = root / "a" / "b"
    deep.mkdir(parents=True)
    (deep / "file.bin").write_bytes(b"abc")

    snapshots = capture_focus_snapshots(
        (
            {
                "id": "case-1",
                "name": "Case",
                "path_template": str(root),
                "enabled": True,
                "max_depth": 2,
            },
        ),
        max_depth=8,
    )

    assert {snapshot.relative_path for snapshot in snapshots} == {".", "a", r"a\b"}


def test_focus_snapshots_skip_expired_targets(tmp_path):
    root = tmp_path / "focus"
    root.mkdir()
    (root / "file.bin").write_bytes(b"abc")
    expired_at = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()

    snapshots = capture_focus_snapshots(
        (
            {
                "id": "case-1",
                "name": "Case",
                "path_template": str(root),
                "enabled": True,
                "max_depth": 2,
                "expires_at": expired_at,
            },
        ),
        max_depth=8,
    )

    assert snapshots == []
