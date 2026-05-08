import sys

from disk_history.startup import startup_command, startup_shortcut_path


def test_startup_shortcut_path_uses_current_user_startup_folder(monkeypatch, tmp_path):
    monkeypatch.setenv("DISK_HISTORY_STARTUP_DIR", str(tmp_path))

    assert startup_shortcut_path() == tmp_path / "DiskHistoryBackground.lnk"


def test_startup_command_runs_background_module():
    target, arguments = startup_command()

    assert target == sys.executable
    assert arguments == "-m disk_history background"
