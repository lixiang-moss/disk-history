from datetime import UTC, datetime

from disk_history.analytics import (
    category_growth,
    cleanup_recommendations,
    directory_rankings,
    heatmap_cells,
    snapshot_summary,
    timeline_by_hour,
)
from disk_history.database import format_time


def test_directory_rankings_and_summary():
    rows = [
        {
            "captured_at": format_time(datetime(2026, 5, 6, 8, tzinfo=UTC)),
            "rule_name": "Downloads",
            "size_bytes": 10,
            "file_count": 2,
            "privacy_mode": "detailed",
            "exists_on_disk": 1,
        },
        {
            "captured_at": format_time(datetime(2026, 5, 6, 9, tzinfo=UTC)),
            "rule_name": "Temp",
            "size_bytes": 20,
            "file_count": 3,
            "privacy_mode": "detailed",
            "exists_on_disk": 1,
        },
    ]

    summary = snapshot_summary(rows)
    rankings = directory_rankings(rows)

    assert summary.total_size_bytes == 30
    assert summary.total_file_count == 5
    assert summary.rule_count == 2
    assert rankings[0].name == "Temp"


def test_category_growth_and_timeline():
    now = datetime(2026, 5, 6, 12, tzinfo=UTC)
    rows = [
        {
            "happened_at": format_time(datetime(2026, 5, 6, 11, 15, tzinfo=UTC)),
            "category": "Downloads",
            "delta_bytes": 100,
        },
        {
            "happened_at": format_time(datetime(2026, 5, 6, 11, 30, tzinfo=UTC)),
            "category": "Downloads",
            "delta_bytes": -20,
        },
        {
            "happened_at": format_time(datetime(2026, 5, 6, 10, 30, tzinfo=UTC)),
            "category": "Temp",
            "delta_bytes": 50,
        },
    ]

    shares = category_growth(rows, now=now)
    points = timeline_by_hour(rows, hours=3, now=now)

    assert shares[0].category == "Downloads"
    assert shares[0].growth_bytes == 100
    assert [point.delta_bytes for point in points] == [50, 80, 0]


def test_heatmap_and_cleanup_recommendations():
    now = datetime(2026, 5, 6, 12, tzinfo=UTC)
    event_rows = [
        {
            "happened_at": format_time(datetime(2026, 5, 6, 11, tzinfo=UTC)),
            "delta_bytes": 100,
        }
    ]
    snapshot_rows = [
        {"rule_name": "Downloads", "size_bytes": 100, "file_count": 1},
        {"rule_name": "Local Programs", "size_bytes": 200, "file_count": 2},
    ]

    cells = heatmap_cells(event_rows, days=1, now=now)
    recommendations = cleanup_recommendations(snapshot_rows)

    assert len(cells) == 24
    assert cells[11].event_count == 1
    assert cells[11].intensity == 1.0
    assert recommendations[0].risk == "protected"
    assert recommendations[1].risk == "safe"
