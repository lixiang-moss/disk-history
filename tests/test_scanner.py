from disk_history.scanner import child_size_rankings, directory_size, format_bytes


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
