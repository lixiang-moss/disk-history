from disk_history import startup
from disk_history.startup import startup_command, startup_shortcut_path


def test_startup_shortcut_path_uses_current_user_startup_folder(monkeypatch, tmp_path):
    monkeypatch.setenv("DISK_HISTORY_STARTUP_DIR", str(tmp_path))

    assert startup_shortcut_path() == tmp_path / "DiskHistoryBackground.lnk"


def test_startup_command_runs_background_module(tmp_path):
    target_path = tmp_path / "python.exe"
    target, arguments = startup_command(str(target_path))

    assert target == str(target_path)
    assert arguments == "-m disk_history background"


def test_startup_command_prefers_pythonw_on_windows(monkeypatch, tmp_path):
    monkeypatch.setattr(startup.os, "name", "nt")
    python = tmp_path / "python.exe"
    pythonw = tmp_path / "pythonw.exe"
    python.touch()
    pythonw.touch()

    target, arguments = startup_command(str(python))

    assert target == str(pythonw)
    assert arguments == "-m disk_history background"
