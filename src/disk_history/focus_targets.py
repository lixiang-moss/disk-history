from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Mapping

from disk_history.config import expand_path_template


def normalized_focus_target(
    target: Mapping[str, Any],
    *,
    index: int = 0,
    default_depth: int = 8,
    default_interval_minutes: int = 1,
    default_ttl_hours: int = 24,
    now: datetime | None = None,
) -> dict[str, object]:
    created_at = str(target.get("created_at") or format_focus_time(now or datetime.now(UTC)))
    target_id = str(target.get("id") or f"focus-{index + 1}")
    ttl_hours = max(1, int(target.get("ttl_hours", default_ttl_hours)))
    return {
        "id": target_id,
        "name": str(target.get("name") or target_id),
        "path_template": str(target.get("path_template") or target.get("path") or ""),
        "enabled": bool(target.get("enabled", True)),
        "max_depth": max(1, int(target.get("max_depth", default_depth))),
        "snapshot_interval_minutes": max(
            1,
            int(target.get("snapshot_interval_minutes", default_interval_minutes)),
        ),
        "ttl_hours": ttl_hours,
        "created_at": created_at,
        "expires_at": str(
            target.get("expires_at")
            or format_focus_time(parse_focus_time(created_at) + timedelta(hours=ttl_hours))
        ),
    }


def is_focus_target_expired(target: Mapping[str, Any], now: datetime | None = None) -> bool:
    expires_at = target.get("expires_at")
    if not expires_at:
        return False
    moment = now or datetime.now(UTC)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return parse_focus_time(str(expires_at)) <= moment.astimezone(UTC)


def focus_target_status(target: Mapping[str, Any], now: datetime | None = None) -> str:
    if is_focus_target_expired(target, now):
        return "expired"
    if not bool(target.get("enabled", True)):
        return "paused"
    return "active"


def focus_target_remaining_text(target: Mapping[str, Any], now: datetime | None = None) -> str:
    if is_focus_target_expired(target, now):
        return "0h"
    expires_at = target.get("expires_at")
    if not expires_at:
        return ""
    moment = now or datetime.now(UTC)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    remaining = parse_focus_time(str(expires_at)) - moment.astimezone(UTC)
    total_minutes = max(0, int(remaining.total_seconds() // 60))
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours}h {minutes}m"


def active_focus_roots(targets: tuple[Mapping[str, Any], ...]) -> tuple[Path, ...]:
    roots: list[Path] = []
    for target in targets:
        normalized = normalized_focus_target(target)
        if bool(normalized["enabled"]) and not is_focus_target_expired(normalized):
            path_template = str(normalized["path_template"])
            if path_template:
                roots.append(expand_path_template(path_template))
    return tuple(roots)


def parse_focus_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def format_focus_time(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()
