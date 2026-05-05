import json

from disk_history.settings import load_settings, settings_path


def test_load_settings_creates_default_config(monkeypatch, tmp_path):
    monkeypatch.setenv("DISK_HISTORY_HOME", str(tmp_path))

    settings = load_settings(create_if_missing=True)

    assert settings.monitor_rules
    assert settings.ignore_patterns
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
            }
        ),
        encoding="utf-8",
    )

    settings = load_settings(create_if_missing=False)

    assert settings.monitor_rules[0].name == "Example"
    assert settings.monitor_rules[0].recursive is False
    assert settings.ignore_patterns == ("*.tmp",)
