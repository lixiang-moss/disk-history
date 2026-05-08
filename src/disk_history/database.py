from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Iterable

from disk_history.config import database_path, ensure_data_dir


SCHEMA_VERSION = 1


@dataclass(frozen=True)
class FileEvent:
    happened_at: datetime
    event_type: str
    privacy_mode: str
    category: str
    display_path: str
    path: str | None
    source_path: str | None = None
    size_before: int | None = None
    size_after: int | None = None
    delta_bytes: int | None = None
    is_directory: bool = False


@dataclass(frozen=True)
class DirectorySnapshot:
    captured_at: datetime
    rule_name: str
    path_template: str
    privacy_mode: str
    exists: bool
    size_bytes: int
    file_count: int
    error_count: int = 0


class DiskHistoryDatabase:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or database_path()
        ensure_data_dir()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self.connection = sqlite3.connect(self.path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row

    def close(self) -> None:
        with self._lock:
            self.connection.close()

    def initialize(self) -> None:
        with self._lock:
            self.connection.executescript(
                """
                PRAGMA journal_mode=WAL;

                CREATE TABLE IF NOT EXISTS schema_info (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS file_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    happened_at TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    privacy_mode TEXT NOT NULL,
                    category TEXT NOT NULL,
                    display_path TEXT NOT NULL,
                    path TEXT,
                    source_path TEXT,
                    size_before INTEGER,
                    size_after INTEGER,
                    delta_bytes INTEGER,
                    is_directory INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS directory_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    captured_at TEXT NOT NULL,
                    rule_name TEXT NOT NULL,
                    path_template TEXT NOT NULL,
                    privacy_mode TEXT NOT NULL,
                    exists_on_disk INTEGER NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    file_count INTEGER NOT NULL,
                    error_count INTEGER NOT NULL DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_file_events_happened_at
                    ON file_events(happened_at);

                CREATE INDEX IF NOT EXISTS idx_directory_snapshots_captured_at
                    ON directory_snapshots(captured_at);
                """
            )
            self.connection.execute(
                "INSERT OR REPLACE INTO schema_info(key, value) VALUES (?, ?)",
                ("schema_version", str(SCHEMA_VERSION)),
            )
            self.connection.commit()

    def insert_event(self, event: FileEvent) -> None:
        with self._lock:
            self.connection.execute(
                """
                INSERT INTO file_events (
                    happened_at, event_type, privacy_mode, category, display_path,
                    path, source_path, size_before, size_after, delta_bytes, is_directory
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    format_time(event.happened_at),
                    event.event_type,
                    event.privacy_mode,
                    event.category,
                    event.display_path,
                    event.path,
                    event.source_path,
                    event.size_before,
                    event.size_after,
                    event.delta_bytes,
                    int(event.is_directory),
                ),
            )
            self.connection.commit()

    def insert_snapshots(self, snapshots: Iterable[DirectorySnapshot]) -> None:
        with self._lock:
            self.connection.executemany(
                """
                INSERT INTO directory_snapshots (
                    captured_at, rule_name, path_template, privacy_mode,
                    exists_on_disk, size_bytes, file_count, error_count
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        format_time(snapshot.captured_at),
                        snapshot.rule_name,
                        snapshot.path_template,
                        snapshot.privacy_mode,
                        int(snapshot.exists),
                        snapshot.size_bytes,
                        snapshot.file_count,
                        snapshot.error_count,
                    )
                    for snapshot in snapshots
                ],
            )
            self.connection.commit()

    def recent_events(self, limit: int = 100) -> list[sqlite3.Row]:
        with self._lock:
            cursor = self.connection.execute(
                """
                SELECT *
                FROM file_events
                ORDER BY happened_at DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            )
            return list(cursor.fetchall())

    def latest_snapshots(self) -> list[sqlite3.Row]:
        with self._lock:
            cursor = self.connection.execute(
                """
                SELECT ds.*
                FROM directory_snapshots ds
                JOIN (
                    SELECT rule_name, MAX(captured_at) AS captured_at
                    FROM directory_snapshots
                    GROUP BY rule_name
                ) latest
                ON ds.rule_name = latest.rule_name
                AND ds.captured_at = latest.captured_at
                ORDER BY ds.size_bytes DESC
                """
            )
            return list(cursor.fetchall())

    def snapshot_history(self, limit: int = 10000) -> list[sqlite3.Row]:
        with self._lock:
            cursor = self.connection.execute(
                """
                SELECT *
                FROM directory_snapshots
                ORDER BY captured_at DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            )
            return list(cursor.fetchall())

    def events_between(self, start_at: datetime, end_at: datetime, limit: int = 500) -> list[sqlite3.Row]:
        with self._lock:
            cursor = self.connection.execute(
                """
                SELECT *
                FROM file_events
                WHERE happened_at >= ?
                  AND happened_at <= ?
                ORDER BY happened_at DESC, id DESC
                LIMIT ?
                """,
                (format_time(start_at), format_time(end_at), limit),
            )
            return list(cursor.fetchall())

    def clear_history(self) -> None:
        with self._lock:
            self.connection.execute("DELETE FROM file_events")
            self.connection.execute("DELETE FROM directory_snapshots")
            self.connection.commit()


def utc_now() -> datetime:
    return datetime.now(UTC)


def format_time(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()
