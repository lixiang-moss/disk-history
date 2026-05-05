from pathlib import Path

from disk_history.config import MonitorRule
from disk_history.privacy import DETAILED, IGNORE, SUMMARY, PrivacyPolicy


def test_privacy_policy_uses_longest_matching_rule(monkeypatch):
    monkeypatch.setenv("USERPROFILE", r"C:\Users\Example")
    rules = (
        MonitorRule("User", r"{USERPROFILE}", SUMMARY),
        MonitorRule("Downloads", r"{USERPROFILE}\Downloads", DETAILED),
    )
    policy = PrivacyPolicy(rules, ignore_patterns=())

    decision = policy.classify(Path(r"C:\Users\Example\Downloads\file.iso"))

    assert decision.mode == DETAILED
    assert decision.label == "Downloads"


def test_privacy_policy_hides_summary_paths(monkeypatch):
    monkeypatch.setenv("USERPROFILE", r"C:\Users\Example")
    rules = (MonitorRule("Documents", r"{USERPROFILE}\Documents", SUMMARY),)
    policy = PrivacyPolicy(rules, ignore_patterns=())

    stored = policy.storage_path_for(Path(r"C:\Users\Example\Documents\private.txt"))

    assert stored is None


def test_privacy_policy_ignores_matching_patterns(monkeypatch):
    monkeypatch.setenv("USERPROFILE", r"C:\Users\Example")
    rules = (MonitorRule("Downloads", r"{USERPROFILE}\Downloads", DETAILED),)
    policy = PrivacyPolicy(rules, ignore_patterns=("*.tmp",))

    decision = policy.classify(Path(r"C:\Users\Example\Downloads\scratch.tmp"))

    assert decision.mode == IGNORE

