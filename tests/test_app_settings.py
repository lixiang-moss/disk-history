import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QDateTime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

import disk_history.app as app_module
from disk_history.app import MainWindow
from disk_history.settings import load_settings
from disk_history.startup import startup_shortcut_path


def test_gui_saves_runtime_settings(monkeypatch, tmp_path):
    monkeypatch.setenv("DISK_HISTORY_HOME", str(tmp_path))
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    window = MainWindow()

    window.background_interval_spin.setValue(7)
    window.log_directory_edit.setText(str(tmp_path / "custom-logs"))
    window.enable_growth_alerts_check.setChecked(False)
    window.alert_window_spin.setValue(45)
    window.alert_threshold_spin.setValue(2048)
    window.save_runtime_settings()

    settings = load_settings(create_if_missing=False)

    assert settings.background_snapshot_interval_minutes == 7
    assert settings.log_directory == str(tmp_path / "custom-logs")
    assert settings.enable_growth_alerts is False
    assert settings.alert_window_minutes == 45
    assert settings.alert_growth_threshold_mb == 2048
    assert window.settings_status_label.text()

    window.close()
    app.processEvents()


def test_gui_saves_startup_mode_choice(monkeypatch, tmp_path):
    monkeypatch.setenv("DISK_HISTORY_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("DISK_HISTORY_STARTUP_DIR", str(tmp_path / "startup"))
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    def fake_enable_start_on_login():
        shortcut = startup_shortcut_path()
        shortcut.parent.mkdir(parents=True, exist_ok=True)
        shortcut.write_text("shortcut", encoding="utf-8")
        return shortcut

    monkeypatch.setattr(app_module, "enable_start_on_login", fake_enable_start_on_login)

    app = QApplication.instance() or QApplication([])
    window = MainWindow()

    window.startup_mode_combo.setCurrentIndex(window.startup_mode_combo.findData("auto"))
    window.save_runtime_settings()

    settings = load_settings(create_if_missing=False)
    assert settings.start_on_login is True
    assert startup_shortcut_path().exists()

    window.startup_mode_combo.setCurrentIndex(window.startup_mode_combo.findData("manual"))
    window.save_runtime_settings()

    settings = load_settings(create_if_missing=False)
    assert settings.start_on_login is False
    assert not startup_shortcut_path().exists()

    window.close()
    app.processEvents()


def test_gui_saves_monitor_rule_edits(monkeypatch, tmp_path):
    monkeypatch.setenv("DISK_HISTORY_HOME", str(tmp_path))
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    window = MainWindow()

    window.rule_table.setRowCount(0)
    window.add_monitor_rule()
    window.rule_table.item(0, 1).setText("Project Cache")
    window.rule_table.item(0, 4).setText(str(tmp_path / "cache"))
    privacy_combo = window.rule_table.cellWidget(0, 2)
    privacy_combo.setCurrentIndex(privacy_combo.findData("detailed"))
    window.save_runtime_settings()

    settings = load_settings(create_if_missing=False)

    assert len(settings.monitor_rules) == 1
    assert settings.monitor_rules[0].name == "Project Cache"
    assert settings.monitor_rules[0].path_template == str(tmp_path / "cache")
    assert settings.monitor_rules[0].privacy_mode == "detailed"
    assert settings.monitor_rules[0].enabled is True
    assert settings.monitor_rules[0].recursive is True

    window.close()
    app.processEvents()


def test_gui_saves_noise_and_focus_rules(monkeypatch, tmp_path):
    monkeypatch.setenv("DISK_HISTORY_HOME", str(tmp_path))
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    window = MainWindow()

    window.noise_table.setRowCount(0)
    window.noise_table.insertRow(0)
    window.noise_table.setItem(0, 0, window.rule_table.item(0, 0).clone())
    window.noise_table.setItem(0, 1, window.rule_table.item(0, 1).clone())
    window.noise_table.item(0, 1).setText("Build")
    window.noise_table.setItem(0, 2, window.rule_table.item(0, 4).clone())
    window.noise_table.item(0, 2).setText("build")

    focus = tmp_path / "focus"
    focus.mkdir()
    window.focus_table.setRowCount(0)
    window.add_focus_target()
    window.focus_table.item(0, 1).setText("Focus")
    window.focus_table.item(0, 2).setText(str(focus))
    window.save_runtime_settings()

    settings = load_settings(create_if_missing=False)

    assert settings.noise_rules[0].name == "Build"
    assert settings.noise_rules[0].path_template == "build"
    assert settings.focus_targets[0]["name"] == "Focus"
    assert settings.focus_targets[0]["path_template"] == str(focus)
    assert "created_at" in settings.focus_targets[0]

    window.close()
    app.processEvents()


def test_gui_noise_and_focus_controls(monkeypatch, tmp_path):
    monkeypatch.setenv("DISK_HISTORY_HOME", str(tmp_path))
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    window = MainWindow()

    original_noise_count = window.noise_table.rowCount()
    window.add_noise_rule()
    assert window.noise_table.rowCount() == original_noise_count + 1
    window.noise_table.setCurrentCell(window.noise_table.rowCount() - 1, 1)
    window.remove_selected_noise_rule()
    assert window.noise_table.rowCount() == original_noise_count

    window.focus_table.setRowCount(0)
    window.add_focus_target()
    window.focus_table.setCurrentCell(0, 1)
    window.pause_selected_focus_target()
    assert window.focus_table.item(0, 0).checkState() == Qt.Unchecked
    window.resume_selected_focus_target()
    assert window.focus_table.item(0, 0).checkState() == Qt.Checked

    window.close()
    app.processEvents()


def test_gui_rejects_monitor_rule_without_path(monkeypatch, tmp_path):
    monkeypatch.setenv("DISK_HISTORY_HOME", str(tmp_path))
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    window = MainWindow()

    window.rule_table.setRowCount(0)
    window.add_monitor_rule()
    window.save_runtime_settings()

    assert "路径不能为空" in window.settings_status_label.text()

    window.close()
    app.processEvents()


def test_gui_applies_custom_investigation_range(monkeypatch, tmp_path):
    monkeypatch.setenv("DISK_HISTORY_HOME", str(tmp_path))
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    window = MainWindow()

    end = QDateTime.currentDateTime()
    start = end.addSecs(-3600)
    window.custom_start_edit.setDateTime(start)
    window.custom_end_edit.setDateTime(end)
    window.apply_custom_investigation_range()

    assert window.custom_investigation_range is not None
    assert window.custom_range_status_label.text()

    window.custom_start_edit.setDateTime(end)
    window.custom_end_edit.setDateTime(start)
    window.apply_custom_investigation_range()

    assert "早于" in window.custom_range_status_label.text()

    window.close()
    app.processEvents()


def test_gui_drilldown_scans_selected_monitor_rule(monkeypatch, tmp_path):
    monkeypatch.setenv("DISK_HISTORY_HOME", str(tmp_path))
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    watched = tmp_path / "watched"
    child = watched / "child"
    child.mkdir(parents=True)
    (child / "file.bin").write_bytes(b"abc")
    app = QApplication.instance() or QApplication([])
    window = MainWindow()

    window.rule_table.setRowCount(0)
    window.add_monitor_rule()
    window.rule_table.item(0, 1).setText("Watched")
    window.rule_table.item(0, 4).setText(str(watched))
    window.save_runtime_settings()
    window.scan_drilldown()

    assert window.drilldown_table.rowCount() == 1
    assert window.drilldown_table.item(0, 0).text() == "child"
    assert window.drilldown_table.item(0, 1).text() == "3 B"

    window.close()
    app.processEvents()
