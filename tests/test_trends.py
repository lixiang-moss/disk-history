from disk_history.trends import drive_subjects, drive_trend, latest_tree_growth, tree_subjects, tree_trend


def test_drive_and_tree_trends():
    drive_rows = [
        {"drive": "C:", "captured_at": "2026-05-09T10:00:00+00:00", "used_bytes": 10},
        {"drive": "C:", "captured_at": "2026-05-09T11:00:00+00:00", "used_bytes": 20},
        {"drive": "D:", "captured_at": "2026-05-09T11:00:00+00:00", "used_bytes": 5},
    ]
    tree_rows = [
        {"path": "C:\\A", "captured_at": "2026-05-09T10:00:00+00:00", "size_bytes": 10},
        {"path": "C:\\A", "captured_at": "2026-05-09T11:00:00+00:00", "size_bytes": 30},
        {"path": "C:\\B", "captured_at": "2026-05-09T11:00:00+00:00", "size_bytes": 5},
    ]

    assert drive_subjects(drive_rows) == ["C:", "D:"]
    assert [point.size_bytes for point in drive_trend(drive_rows, "C:")] == [10, 20]
    assert tree_subjects(tree_rows) == ["C:\\A", "C:\\B"]
    assert [point.size_bytes for point in tree_trend(tree_rows, "C:\\A")] == [10, 30]
    assert latest_tree_growth(tree_rows)[0]["delta_bytes"] == 20
