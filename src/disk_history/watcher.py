from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler, FileSystemMovedEvent
from watchdog.observers import Observer

from disk_history.config import DEFAULT_IGNORE_PATTERNS, DEFAULT_MONITOR_RULES, MonitorRule, NoiseRule
from disk_history.database import DiskHistoryDatabase, FileEvent, utc_now
from disk_history.paths import is_path_excluded
from disk_history.privacy import IGNORE, SUMMARY, PrivacyPolicy


@dataclass(frozen=True)
class WatchTarget:
    rule_name: str
    path: Path
    recursive: bool


class DiskHistoryEventHandler(FileSystemEventHandler):
    def __init__(
        self,
        database: DiskHistoryDatabase,
        privacy_policy: PrivacyPolicy,
        excluded_roots: tuple[Path, ...] = (),
        noise_roots: tuple[Path, ...] = (),
        noise_names: tuple[str, ...] = (),
        focus_roots: tuple[Path, ...] = (),
    ) -> None:
        super().__init__()
        self.database = database
        self.privacy_policy = privacy_policy
        self.size_cache: dict[str, int] = {}
        self.excluded_roots = excluded_roots
        self.noise_roots = noise_roots
        self.noise_names = noise_names
        self.focus_roots = focus_roots

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.event_type in {"opened", "closed"}:
            return
        if isinstance(event, FileSystemMovedEvent):
            self._record_moved(event)
            return
        self._record_path(event.event_type, Path(event.src_path), event.is_directory)

    def _record_moved(self, event: FileSystemMovedEvent) -> None:
        destination = Path(event.dest_path)
        if is_path_excluded(destination, self.excluded_roots):
            return
        if self._is_noise_event(destination):
            return
        decision = self.privacy_policy.classify(destination)
        if decision.mode == IGNORE:
            return

        display_path = decision.label if decision.mode == SUMMARY else str(destination)
        source_path = None if decision.mode == SUMMARY else event.src_path
        size_after = safe_size(destination)

        self.database.insert_event(
            FileEvent(
                happened_at=utc_now(),
                event_type="moved",
                privacy_mode=decision.mode,
                category=decision.label,
                display_path=display_path,
                path=self.privacy_policy.storage_path_for(destination),
                source_path=source_path,
                size_after=size_after,
                is_directory=event.is_directory,
                source_strategy=source_strategy_for(destination, self.focus_roots),
            )
        )

    def _record_path(self, event_type: str, path: Path, is_directory: bool) -> None:
        if is_path_excluded(path, self.excluded_roots):
            return
        if self._is_noise_event(path):
            return

        decision = self.privacy_policy.classify(path)
        if decision.mode == IGNORE:
            return

        cache_key = str(path)
        previous_size = self.size_cache.get(cache_key)
        current_size = None if event_type == "deleted" else safe_size(path)
        if current_size is not None:
            self.size_cache[cache_key] = current_size
        elif event_type == "deleted":
            self.size_cache.pop(cache_key, None)

        delta = None
        if previous_size is not None and current_size is not None:
            delta = current_size - previous_size
        elif event_type == "created" and current_size is not None:
            delta = current_size
        elif event_type == "deleted" and previous_size is not None:
            delta = -previous_size

        display_path = decision.label if decision.mode == SUMMARY else str(path)

        self.database.insert_event(
            FileEvent(
                happened_at=utc_now(),
                event_type=event_type,
                privacy_mode=decision.mode,
                category=decision.label,
                display_path=display_path,
                path=self.privacy_policy.storage_path_for(path),
                size_before=previous_size,
                size_after=current_size,
                delta_bytes=delta,
                is_directory=is_directory,
                source_strategy=source_strategy_for(path, self.focus_roots),
            )
        )

    def _is_noise_event(self, path: Path) -> bool:
        if is_path_excluded(path, self.focus_roots):
            return False
        if is_path_excluded(path, self.noise_roots):
            return True
        path_parts = {part.lower() for part in path.parts}
        return any(name in path_parts for name in self.noise_names)


class DiskHistoryWatcher:
    def __init__(
        self,
        database: DiskHistoryDatabase,
        monitor_rules: tuple[MonitorRule, ...] = DEFAULT_MONITOR_RULES,
        ignore_patterns: tuple[str, ...] = DEFAULT_IGNORE_PATTERNS,
        excluded_roots: tuple[Path, ...] = (),
        noise_rules: tuple[NoiseRule, ...] = (),
        focus_roots: tuple[Path, ...] = (),
    ) -> None:
        self.database = database
        self.monitor_rules = monitor_rules
        self.ignore_patterns = ignore_patterns
        self.excluded_roots = excluded_roots
        self.noise_roots = tuple(
            rule.resolved_path()
            for rule in noise_rules
            if rule.enabled and is_absolute_template(rule.path_template)
        )
        self.noise_names = tuple(
            rule.path_template.lower()
            for rule in noise_rules
            if rule.enabled and not is_absolute_template(rule.path_template)
        )
        self.focus_roots = focus_roots
        self.observer: Observer | None = None
        self.targets: list[WatchTarget] = []

    @property
    def is_running(self) -> bool:
        return self.observer is not None and self.observer.is_alive()

    def start(self) -> list[WatchTarget]:
        if self.is_running:
            return self.targets

        privacy_policy = PrivacyPolicy(self.monitor_rules, self.ignore_patterns)
        handler = DiskHistoryEventHandler(
            self.database,
            privacy_policy,
            self.excluded_roots,
            self.noise_roots,
            self.noise_names,
            self.focus_roots,
        )
        observer = Observer()
        targets = watch_targets(self.monitor_rules, self.excluded_roots, self.noise_roots)
        targets.extend(focus_watch_targets(self.focus_roots, self.excluded_roots))

        for target in targets:
            observer.schedule(handler, str(target.path), recursive=target.recursive)

        if not targets:
            raise RuntimeError("No configured monitor paths exist on this system.")

        observer.start()
        self.observer = observer
        self.targets = targets
        return targets

    def stop(self) -> None:
        if self.observer is None:
            return
        self.observer.stop()
        self.observer.join(timeout=5)
        self.observer = None
        self.targets = []


def safe_size(path: Path) -> int | None:
    try:
        if path.is_file():
            return path.stat().st_size
    except OSError:
        return None
    return None


def source_strategy_for(path: Path, focus_roots: tuple[Path, ...]) -> str:
    return "focus" if is_path_excluded(path, focus_roots) else "standard"


def is_absolute_template(path_template: str) -> bool:
    if path_template.startswith("{"):
        return True
    return Path(path_template).is_absolute()


def watch_targets(
    monitor_rules: tuple[MonitorRule, ...] = DEFAULT_MONITOR_RULES,
    excluded_roots: tuple[Path, ...] = (),
    noise_roots: tuple[Path, ...] = (),
) -> list[WatchTarget]:
    targets: list[WatchTarget] = []
    for rule in monitor_rules:
        if not rule.enabled:
            continue
        path = rule.resolved_path()
        if is_path_excluded(path, excluded_roots):
            continue
        if is_path_excluded(path, noise_roots):
            continue
        if path.exists():
            targets.append(WatchTarget(rule.name, path, rule.recursive))
    return targets


def focus_watch_targets(
    focus_roots: tuple[Path, ...],
    excluded_roots: tuple[Path, ...] = (),
) -> list[WatchTarget]:
    targets: list[WatchTarget] = []
    for path in focus_roots:
        if is_path_excluded(path, excluded_roots):
            continue
        if path.exists():
            targets.append(WatchTarget("Focus", path, True))
    return targets


def run_watcher(
    database: DiskHistoryDatabase,
    monitor_rules: tuple[MonitorRule, ...] = DEFAULT_MONITOR_RULES,
    ignore_patterns: tuple[str, ...] = DEFAULT_IGNORE_PATTERNS,
    excluded_roots: tuple[Path, ...] = (),
    noise_rules: tuple[NoiseRule, ...] = (),
    focus_roots: tuple[Path, ...] = (),
) -> None:
    watcher = DiskHistoryWatcher(
        database,
        monitor_rules,
        ignore_patterns,
        excluded_roots,
        noise_rules,
        focus_roots,
    )
    watcher.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        watcher.stop()
