from datetime import UTC, datetime, timedelta

from disk_history.focus_targets import (
    focus_target_remaining_text,
    focus_target_status,
    is_focus_target_expired,
    normalized_focus_target,
)


def test_focus_target_expiration_and_status():
    now = datetime(2026, 5, 9, 12, tzinfo=UTC)
    target = normalized_focus_target(
        {"id": "focus-1", "name": "Focus", "path_template": "C:\\Focus", "ttl_hours": 1},
        now=now - timedelta(hours=2),
    )

    assert is_focus_target_expired(target, now=now) is True
    assert focus_target_status(target, now=now) == "expired"
    assert focus_target_remaining_text(target, now=now) == "0h"


def test_focus_target_paused_status():
    now = datetime(2026, 5, 9, 12, tzinfo=UTC)
    target = normalized_focus_target(
        {"id": "focus-1", "name": "Focus", "path_template": "C:\\Focus", "enabled": False},
        now=now,
    )

    assert focus_target_status(target, now=now) == "paused"
