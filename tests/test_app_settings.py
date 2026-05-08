import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from disk_history.app import MainWindow
from disk_history.settings import load_settings


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
