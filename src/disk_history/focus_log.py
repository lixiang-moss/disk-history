from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from disk_history.database import FocusSnapshot, format_time
from disk_history.settings import resolved_focus_log_directory


class FocusLogWriter:
    def __init__(self, log_root: Path | None = None) -> None:
        self.log_root = log_root or resolved_focus_log_directory()

    def target_dir(self, moment: datetime, target_id: str, target_name: str) -> Path:
        local_moment = moment.astimezone() if moment.tzinfo else moment
        safe_name = safe_path_part(target_name)
        safe_id = safe_path_part(target_id)
        return self.log_root / local_moment.strftime("%Y-%m-%d") / f"focus-{safe_id}-{safe_name}"

    def ensure_target_files(self, moment: datetime, target_id: str, target_name: str) -> Path:
        target_dir = self.target_dir(moment, target_id, target_name)
        target_dir.mkdir(parents=True, exist_ok=True)
        for name in ("snapshots.jsonl", "events.jsonl", "alerts.jsonl"):
            (target_dir / name).touch(exist_ok=True)
        summary = target_dir / "summary.md"
        if not summary.exists():
            summary.write_text(
                "# 重点监控日志摘要\n\n"
                "本目录用于单独导出某个重点监控目标的记录，便于交给 AI 或人工分析。"
                "它只记录路径、大小、时间、事件类型等元数据，不读取文件内容。\n\n",
                encoding="utf-8",
            )
        return target_dir

    def append_snapshots(self, snapshots: Iterable[FocusSnapshot]) -> None:
        grouped: dict[tuple[str, str, datetime], list[FocusSnapshot]] = {}
        for snapshot in snapshots:
            key = (snapshot.target_id, snapshot.target_name, snapshot.captured_at)
            grouped.setdefault(key, []).append(snapshot)

        for (target_id, target_name, moment), rows in grouped.items():
            target_dir = self.ensure_target_files(moment, target_id, target_name)
            with (target_dir / "snapshots.jsonl").open("a", encoding="utf-8") as handle:
                for row in rows:
                    handle.write(json.dumps(focus_snapshot_record(row), ensure_ascii=False) + "\n")
            self._append_summary(
                moment,
                target_id,
                target_name,
                f"- {moment.isoformat()} 记录 {len(rows)} 条重点目录快照。\n",
            )

    def append_event_rows(
        self,
        rows: Iterable[Mapping[str, Any]],
        *,
        moment: datetime,
        target_id: str = "focus",
        target_name: str = "focus",
    ) -> None:
        rows = list(rows)
        if not rows:
            return
        target_dir = self.ensure_target_files(moment, target_id, target_name)
        with (target_dir / "events.jsonl").open("a", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(dict(row), ensure_ascii=False) + "\n")
        self._append_summary(
            moment,
            target_id,
            target_name,
            f"- {moment.isoformat()} 记录 {len(rows)} 条重点实时事件。\n",
        )

    def _append_summary(
        self,
        moment: datetime,
        target_id: str,
        target_name: str,
        text: str,
    ) -> None:
        target_dir = self.ensure_target_files(moment, target_id, target_name)
        with (target_dir / "summary.md").open("a", encoding="utf-8") as handle:
            handle.write(text)
            if not text.endswith("\n"):
                handle.write("\n")


def focus_snapshot_record(snapshot: FocusSnapshot) -> dict[str, Any]:
    return {
        "captured_at": format_time(snapshot.captured_at),
        "target_id": snapshot.target_id,
        "target_name": snapshot.target_name,
        "path": snapshot.path,
        "relative_path": snapshot.relative_path,
        "depth": snapshot.depth,
        "size_bytes": snapshot.size_bytes,
        "file_count": snapshot.file_count,
        "error_count": snapshot.error_count,
    }


def safe_path_part(value: str) -> str:
    cleaned = "".join(character if character.isalnum() or character in ("-", "_") else "-" for character in value)
    return cleaned.strip("-") or "target"
