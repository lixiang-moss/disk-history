import json

from disk_history.settings import load_settings, settings_path


def test_load_settings_creates_default_config(monkeypatch, tmp_path):
    monkeypatch.setenv("DISK_HISTORY_HOME", str(tmp_path))

    settings = load_settings(create_if_missing=True)

    assert settings.monitor_rules
    assert settings.ignore_patterns
    assert settings.language == "zh-CN"
    assert settings.start_on_login is False
    assert settings.background_snapshot_interval_minutes == 10
    assert settings.log_directory == r"{LOCALAPPDATA}\DiskHistory\logs"
    assert settings.enable_growth_alerts is True
    assert settings.alert_window_minutes == 30
    assert settings.alert_growth_threshold_mb == 5120
    assert settings_path().exists()


def test_load_settings_reads_monitor_rules(monkeypatch, tmp_path):
    monkeypatch.setenv("DISK_HISTORY_HOME", str(tmp_path))
    settings_path().write_text(
        json.dumps(
            {
                "monitor_rules": [
                    {
                        "name": "Example",
                        "path_template": r"{USERPROFILE}\Example",
                        "privacy_mode": "summary",
                        "enabled": True,
                        "recursive": False,
                    }
                ],
                "ignore_patterns": ["*.tmp"],
                "language": "en",
                "start_on_login": True,
                "background_snapshot_interval_minutes": 15,
                "log_directory": r"C:\Logs",
                "enable_growth_alerts": False,
                "alert_window_minutes": 45,
                "alert_growth_threshold_mb": 2048,
            }
        ),
        encoding="utf-8",
    )

    settings = load_settings(create_if_missing=False)

    assert settings.monitor_rules[0].name == "Example"
    assert settings.monitor_rules[0].recursive is False
    assert settings.ignore_patterns == ("*.tmp",)
    assert settings.language == "en"
    assert settings.start_on_login is True
    assert settings.background_snapshot_interval_minutes == 15
    assert settings.log_directory == r"C:\Logs"
    assert settings.enable_growth_alerts is False
    assert settings.alert_window_minutes == 45
    assert settings.alert_growth_threshold_mb == 2048


def test_load_settings_migrates_missing_language(monkeypatch, tmp_path):
    monkeypatch.setenv("DISK_HISTORY_HOME", str(tmp_path))
    settings_path().write_text(
        json.dumps(
            {
                "monitor_rules": [],
                "ignore_patterns": [],
            }
        ),
        encoding="utf-8",
    )

    settings = load_settings(create_if_missing=True)
    raw = json.loads(settings_path().read_text(encoding="utf-8"))

    assert settings.language == "zh-CN"
    assert raw["language"] == "zh-CN"
    assert raw["start_on_login"] is False
    assert raw["background_snapshot_interval_minutes"] == 10
    assert raw["log_directory"] == r"{LOCALAPPDATA}\DiskHistory\logs"
    assert raw["enable_growth_alerts"] is True
    assert raw["alert_window_minutes"] == 30
    assert raw["alert_growth_threshold_mb"] == 5120
