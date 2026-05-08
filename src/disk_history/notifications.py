from __future__ import annotations

from PySide6.QtWidgets import QApplication, QStyle, QSystemTrayIcon


class TrayNotifier:
    def __init__(self) -> None:
        self.app = QApplication.instance() or QApplication([])
        self.tray: QSystemTrayIcon | None = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            icon = self.app.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation)
            self.tray = QSystemTrayIcon(icon, self.app)
            self.tray.setToolTip("Disk History")
            self.tray.show()

    def show_message(self, title: str, message: str) -> None:
        if self.tray is None:
            return
        self.tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 8000)
        self.app.processEvents()
