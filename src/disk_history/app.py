from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from disk_history.config import app_data_dir, database_path
from disk_history.database import DiskHistoryDatabase
from disk_history.scanner import capture_snapshots, format_bytes
from disk_history.settings import load_settings, settings_path


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Disk History")
        self.resize(1100, 720)

        self.database = DiskHistoryDatabase()
        self.database.initialize()
        self.settings = load_settings()

        tabs = QTabWidget()
        tabs.addTab(self._overview_tab(), "Overview")
        tabs.addTab(self._timeline_tab(), "Timeline")
        tabs.addTab(self._rules_tab(), "Monitor Rules")
        tabs.addTab(self._privacy_tab(), "Privacy")
        tabs.addTab(self._data_tab(), "Data")
        self.setCentralWidget(tabs)

        self.refresh_all()

    def _overview_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.status_label = QLabel()
        layout.addWidget(self.status_label)

        actions = QHBoxLayout()
        scan_button = QPushButton("Scan Once")
        scan_button.clicked.connect(self.scan_once)
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_all)
        actions.addWidget(scan_button)
        actions.addWidget(refresh_button)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.snapshot_table = QTableWidget(0, 5)
        self.snapshot_table.setHorizontalHeaderLabels(
            ["Rule", "Size", "Files", "Privacy", "Path Template"]
        )
        layout.addWidget(self.snapshot_table)
        return widget

    def _timeline_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.event_table = QTableWidget(0, 6)
        self.event_table.setHorizontalHeaderLabels(
            ["Time", "Event", "Delta", "Category", "Privacy", "Display Path"]
        )
        layout.addWidget(self.event_table)
        return widget

    def _rules_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        table = QTableWidget(len(self.settings.monitor_rules), 5)
        table.setHorizontalHeaderLabels(["Enabled", "Name", "Privacy", "Recursive", "Path Template"])
        for index, rule in enumerate(self.settings.monitor_rules):
            values = [
                "Yes" if rule.enabled else "No",
                rule.name,
                rule.privacy_mode,
                "Yes" if rule.recursive else "No",
                rule.path_template,
            ]
            for column, value in enumerate(values):
                table.setItem(index, column, QTableWidgetItem(value))
        table.resizeColumnsToContents()
        layout.addWidget(table)
        return widget

    def _privacy_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(
            "Disk History records metadata only.\n\n"
            "Detailed mode stores concrete file paths and size metadata.\n"
            "Summary mode stores only the configured rule label and aggregate metadata.\n"
            "Ignored paths are not recorded.\n\n"
            "The first version does not record file contents and does not upload data.\n\n"
            f"Settings file:\n{settings_path()}"
        )
        layout.addWidget(text)
        return widget

    def _data_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel(f"Data folder: {app_data_dir()}"))
        layout.addWidget(QLabel(f"Database: {database_path()}"))
        clear_button = QPushButton("Clear Local History")
        clear_button.clicked.connect(self.clear_history)
        layout.addWidget(clear_button)
        layout.addStretch(1)
        return widget

    def scan_once(self) -> None:
        self.settings = load_settings()
        snapshots = capture_snapshots(self.settings.monitor_rules)
        self.database.insert_snapshots(snapshots)
        self.refresh_all()

    def refresh_all(self) -> None:
        self.status_label.setText(f"Local database: {database_path()}")
        self._refresh_snapshots()
        self._refresh_events()

    def _refresh_snapshots(self) -> None:
        rows = self.database.latest_snapshots()
        self.snapshot_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                row["rule_name"],
                format_bytes(row["size_bytes"]),
                str(row["file_count"]),
                row["privacy_mode"],
                row["path_template"],
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in {1, 2}:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.snapshot_table.setItem(row_index, column, item)
        self.snapshot_table.resizeColumnsToContents()

    def _refresh_events(self) -> None:
        rows = self.database.recent_events()
        self.event_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                row["happened_at"],
                row["event_type"],
                format_bytes(row["delta_bytes"]),
                row["category"],
                row["privacy_mode"],
                row["display_path"],
            ]
            for column, value in enumerate(values):
                self.event_table.setItem(row_index, column, QTableWidgetItem(value))
        self.event_table.resizeColumnsToContents()

    def clear_history(self) -> None:
        result = QMessageBox.question(
            self,
            "Clear Local History",
            "Clear all recorded local history from the SQLite database?",
        )
        if result == QMessageBox.Yes:
            self.database.clear_history()
            self.refresh_all()


def run_app() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
