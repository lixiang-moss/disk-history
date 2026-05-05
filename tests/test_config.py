from pathlib import Path

from disk_history.config import expand_path_template


def test_expand_path_template_uses_environment(monkeypatch):
    monkeypatch.setenv("USERPROFILE", r"C:\Users\Example")

    result = expand_path_template(r"{USERPROFILE}\Downloads")

    assert result == Path(r"C:\Users\Example\Downloads")

