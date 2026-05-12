from __future__ import annotations

from collections.abc import Callable

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon


class TrayNotifier:
    def __init__(self, on_quit: Callable[[], None] | None = None) -> None:
        self.app = QApplication.instance() or QApplication([])
        self.tray: QSystemTrayIcon | None = None
        self.menu: QMenu | None = None
        self.quit_action: QAction | None = None
        self.on_quit = on_quit
        if QSystemTrayIcon.isSystemTrayAvailable():
            icon = self.app.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation)
            self.tray = QSystemTrayIcon(icon, self.app)
            self.tray.setToolTip("Disk History")
            self._build_menu()
            self.tray.show()

    def show_message(self, title: str, message: str) -> None:
        if self.tray is None:
            return
        self.tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 8000)
        self.process_events()

    def process_events(self) -> None:
        self.app.processEvents()

    def close(self) -> None:
        if self.tray is not None:
            self.tray.hide()
        self.process_events()

    def _build_menu(self) -> None:
        if self.tray is None:
            return
        self.menu = QMenu()
        self.quit_action = QAction("退出 Disk History", self.menu)
        self.quit_action.triggered.connect(self._handle_quit)
        self.menu.addAction(self.quit_action)
        self.tray.setContextMenu(self.menu)

    def _handle_quit(self) -> None:
        if self.on_quit is not None:
            self.on_quit()
