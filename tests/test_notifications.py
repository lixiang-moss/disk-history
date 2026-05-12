import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from disk_history.notifications import TrayNotifier


def test_tray_notifier_quit_callback_is_invoked():
    called = []
    notifier = TrayNotifier(on_quit=lambda: called.append(True))

    notifier._handle_quit()

    assert called == [True]
    notifier.close()
