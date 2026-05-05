from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import Path

from disk_history.config import DEFAULT_IGNORE_PATTERNS, MonitorRule


DETAILED = "detailed"
SUMMARY = "summary"
IGNORE = "ignore"


@dataclass(frozen=True)
class PrivacyDecision:
    mode: str
    label: str
    path_template: str | None = None


class PrivacyPolicy:
    def __init__(
        self,
        monitor_rules: tuple[MonitorRule, ...],
        ignore_patterns: tuple[str, ...] = DEFAULT_IGNORE_PATTERNS,
    ) -> None:
        self.monitor_rules = tuple(rule for rule in monitor_rules if rule.enabled)
        self.ignore_patterns = ignore_patterns

    def classify(self, path: Path) -> PrivacyDecision:
        normalized = normalize_path(path)
        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(normalized, normalize_pattern(pattern)):
                return PrivacyDecision(IGNORE, "Ignored")

        best_rule: MonitorRule | None = None
        best_length = -1
        for rule in self.monitor_rules:
            root = normalize_path(rule.resolved_path())
            if normalized == root or normalized.startswith(root + "/"):
                if len(root) > best_length:
                    best_rule = rule
                    best_length = len(root)

        if best_rule is None:
            return PrivacyDecision(SUMMARY, "Unmatched")

        return PrivacyDecision(best_rule.privacy_mode, best_rule.name, best_rule.path_template)

    def storage_path_for(self, path: Path) -> str | None:
        decision = self.classify(path)
        if decision.mode == IGNORE:
            return None
        if decision.mode == SUMMARY:
            return None
        return str(path)


def normalize_path(path: Path) -> str:
    return str(path).replace("\\", "/").rstrip("/").lower()


def normalize_pattern(pattern: str) -> str:
    return pattern.replace("\\", "/").lower()

