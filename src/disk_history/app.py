from __future__ import annotations

import sys
from dataclasses import replace

from PySide6.QtCharts import (
    QBarCategoryAxis,
    QBarSet,
    QChart,
    QChartView,
    QHorizontalBarSeries,
    QLineSeries,
    QPieSeries,
    QValueAxis,
)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
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

from disk_history.analytics import (
    category_growth,
    cleanup_recommendations,
    directory_rankings,
    heatmap_cells,
    snapshot_summary,
    timeline_by_hour,
)
from disk_history.config import app_data_dir, database_path
from disk_history.database import DiskHistoryDatabase
from disk_history.i18n import SUPPORTED_LANGUAGES, normalize_language, translate
from disk_history.scanner import capture_snapshots, format_bytes
from disk_history.settings import load_settings, save_settings, settings_path
from disk_history.watcher import DiskHistoryWatcher


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.resize(1200, 780)

        self.database = DiskHistoryDatabase()
        self.database.initialize()
        self.settings = load_settings()
        self.language = normalize_language(self.settings.language)
        self.watcher: DiskHistoryWatcher | None = None
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(3000)
        self.refresh_timer.timeout.connect(self.refresh_all)

        self._build_ui()
        self.refresh_all()

    def t(self, key: str, **values: object) -> str:
        return translate(self.language, key, **values)

    def _build_ui(self) -> None:
        self.setWindowTitle(self.t("app.title"))
        self.tabs = QTabWidget()
        self.tabs.addTab(self._overview_tab(), self.t("tab.overview"))
        self.tabs.addTab(self._timeline_tab(), self.t("tab.timeline"))
        self.tabs.addTab(self._sources_tab(), self.t("tab.sources"))
        self.tabs.addTab(self._heatmap_tab(), self.t("tab.heatmap"))
        self.tabs.addTab(self._cleanup_tab(), self.t("tab.cleanup"))
        self.tabs.addTab(self._settings_tab(), self.t("tab.settings"))
        self.setCentralWidget(self.tabs)

    def _overview_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.status_label = QLabel()
        self.summary_label = QLabel()
        self.monitor_status_label = QLabel()
        layout.addWidget(self.status_label)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.monitor_status_label)

        actions = QHBoxLayout()
        self.scan_button = QPushButton(self.t("button.scan_once"))
        self.scan_button.clicked.connect(self.scan_once)
        self.refresh_button = QPushButton(self.t("button.refresh"))
        self.refresh_button.clicked.connect(self.refresh_all)
        self.start_monitor_button = QPushButton(self.t("button.start_monitoring"))
        self.start_monitor_button.clicked.connect(self.start_monitoring)
        self.stop_monitor_button = QPushButton(self.t("button.stop_monitoring"))
        self.stop_monitor_button.clicked.connect(self.stop_monitoring)
        actions.addWidget(self.scan_button)
        actions.addWidget(self.refresh_button)
        actions.addWidget(self.start_monitor_button)
        actions.addWidget(self.stop_monitor_button)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.directory_chart = QChartView()
        self.directory_chart.setMinimumHeight(280)
        layout.addWidget(self.directory_chart)

        self.snapshot_table = QTableWidget(0, 5)
        self.snapshot_table.setHorizontalHeaderLabels(
            [
                self.t("table.rule"),
                self.t("table.size"),
                self.t("table.files"),
                self.t("table.privacy"),
                self.t("table.path_template"),
            ]
        )
        layout.addWidget(self.snapshot_table)
        return widget

    def _timeline_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.timeline_chart = QChartView()
        self.timeline_chart.setMinimumHeight(300)
        layout.addWidget(self.timeline_chart)

        self.event_table = QTableWidget(0, 6)
        self.event_table.setHorizontalHeaderLabels(
            [
                self.t("table.time"),
                self.t("table.event"),
                self.t("table.delta"),
                self.t("table.category"),
                self.t("table.privacy"),
                self.t("table.display_path"),
            ]
        )
        layout.addWidget(self.event_table)
        return widget

    def _sources_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.sources_chart = QChartView()
        self.sources_chart.setMinimumHeight(520)
        layout.addWidget(self.sources_chart)
        return widget

    def _heatmap_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.heatmap_table = QTableWidget(7, 24)
        self.heatmap_table.setHorizontalHeaderLabels([f"{hour:02d}" for hour in range(24)])
        self.heatmap_table.verticalHeader().setDefaultSectionSize(32)
        layout.addWidget(self.heatmap_table)
        return widget

    def _cleanup_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.cleanup_table = QTableWidget(0, 4)
        self.cleanup_table.setHorizontalHeaderLabels(
            [
                self.t("table.risk"),
                self.t("table.target"),
                self.t("table.size"),
                self.t("table.suggestion"),
            ]
        )
        layout.addWidget(self.cleanup_table)
        return widget

    def _settings_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        language_row = QHBoxLayout()
        language_row.addWidget(QLabel(self.t("label.language")))
        self.language_combo = QComboBox()
        for code, label in SUPPORTED_LANGUAGES.items():
            self.language_combo.addItem(label, code)
        self.language_combo.setCurrentIndex(self.language_combo.findData(self.language))
        self.language_combo.currentIndexChanged.connect(self.change_language)
        language_row.addWidget(self.language_combo)
        language_row.addStretch(1)
        layout.addLayout(language_row)

        self.rule_table = QTableWidget(len(self.settings.monitor_rules), 5)
        self.rule_table.setHorizontalHeaderLabels(
            [
                self.t("table.enabled"),
                self.t("table.rule"),
                self.t("table.privacy"),
                self.t("table.recursive"),
                self.t("table.path_template"),
            ]
        )
        for index, rule in enumerate(self.settings.monitor_rules):
            values = [
                self.t("yes") if rule.enabled else self.t("no"),
                rule.name,
                rule.privacy_mode,
                self.t("yes") if rule.recursive else self.t("no"),
                rule.path_template,
            ]
            for column, value in enumerate(values):
                self.rule_table.setItem(index, column, QTableWidgetItem(value))
        self.rule_table.resizeColumnsToContents()
        layout.addWidget(self.rule_table)

        self.privacy_text = QTextEdit()
        self.privacy_text.setReadOnly(True)
        self.privacy_text.setPlainText(
            self.t("label.privacy_intro") + f"\n\n{self.t('label.settings_file', path=settings_path())}"
        )
        layout.addWidget(self.privacy_text)

        layout.addWidget(QLabel(self.t("label.data_folder", path=app_data_dir())))
        layout.addWidget(QLabel(self.t("label.local_database", path=database_path())))
        clear_button = QPushButton(self.t("button.clear_history"))
        clear_button.clicked.connect(self.clear_history)
        layout.addWidget(clear_button)
        return widget

    def scan_once(self) -> None:
        self.settings = load_settings()
        snapshots = capture_snapshots(self.settings.monitor_rules)
        self.database.insert_snapshots(snapshots)
        self.refresh_all()

    def start_monitoring(self) -> None:
        if self.watcher and self.watcher.is_running:
            self.refresh_all()
            return

        self.settings = load_settings()
        self.watcher = DiskHistoryWatcher(
            self.database,
            self.settings.monitor_rules,
            self.settings.ignore_patterns,
        )
        try:
            self.watcher.start()
        except RuntimeError as exc:
            self.monitor_status_label.setText(
                self.t("label.monitor_status_error", message=str(exc))
            )
            self.watcher = None
            return

        self.refresh_timer.start()
        self.refresh_all()

    def stop_monitoring(self) -> None:
        if self.watcher:
            self.watcher.stop()
        self.refresh_timer.stop()
        self.refresh_all()

    def refresh_all(self) -> None:
        snapshots = self.database.latest_snapshots()
        events = self.database.recent_events(limit=2000)
        summary = snapshot_summary(snapshots)

        self.status_label.setText(self.t("label.local_database", path=database_path()))
        if summary.latest_time is None:
            self.summary_label.setText(self.t("label.no_scan"))
        else:
            self.summary_label.setText(
                "  |  ".join(
                    [
                        self.t("label.monitor_total", count=summary.rule_count),
                        self.t("label.snapshot_total", size=format_bytes(summary.total_size_bytes)),
                        self.t("label.latest_scan", time=summary.latest_time.strftime("%Y-%m-%d %H:%M")),
                    ]
                )
            )

        if self.watcher and self.watcher.is_running:
            self.monitor_status_label.setText(
                self.t("label.monitor_status_running", count=len(self.watcher.targets))
            )
            self.start_monitor_button.setEnabled(False)
            self.stop_monitor_button.setEnabled(True)
        else:
            self.monitor_status_label.setText(self.t("label.monitor_status_stopped"))
            self.start_monitor_button.setEnabled(True)
            self.stop_monitor_button.setEnabled(False)

        self._refresh_snapshots(snapshots)
        self._refresh_events(events)
        self._refresh_directory_chart(snapshots)
        self._refresh_timeline_chart(events)
        self._refresh_sources_chart(events)
        self._refresh_heatmap(events)
        self._refresh_cleanup(snapshots)

    def _refresh_snapshots(self, rows) -> None:
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

    def _refresh_events(self, rows) -> None:
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

    def _refresh_directory_chart(self, rows) -> None:
        rankings = directory_rankings(rows)
        if not rankings:
            self.directory_chart.setChart(self._empty_chart(self.t("chart.directory_rank")))
            return

        chart = QChart()
        chart.setTitle(self.t("chart.directory_rank"))
        values = QBarSet(self.t("chart.size_mb"))
        categories = []
        for item in reversed(rankings):
            values.append(_to_mb(item.size_bytes))
            categories.append(item.name)
        series = QHorizontalBarSeries()
        series.append(values)
        chart.addSeries(series)

        axis_y = QBarCategoryAxis()
        axis_y.append(categories)
        axis_x = QValueAxis()
        axis_x.setTitleText(self.t("chart.size_mb"))
        axis_x.setLabelFormat("%.1f")
        chart.addAxis(axis_y, Qt.AlignLeft)
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_y)
        series.attachAxis(axis_x)
        chart.legend().hide()
        self.directory_chart.setChart(chart)

    def _refresh_timeline_chart(self, rows) -> None:
        points = timeline_by_hour(rows, hours=24)
        if not points or all(point.delta_bytes == 0 for point in points):
            self.timeline_chart.setChart(self._empty_chart(self.t("chart.timeline")))
            return

        chart = QChart()
        chart.setTitle(self.t("chart.timeline"))
        series = QLineSeries()
        for index, point in enumerate(points):
            series.append(index, _to_mb(point.delta_bytes))
        chart.addSeries(series)

        axis_x = QValueAxis()
        axis_x.setRange(0, max(len(points) - 1, 1))
        axis_x.setTitleText(self.t("chart.hour_index"))
        axis_x.setLabelFormat("%d")
        values = [_to_mb(point.delta_bytes) for point in points]
        axis_y = QValueAxis()
        low = min(values)
        high = max(values)
        if low == high:
            low -= 1
            high += 1
        axis_y.setRange(low, high)
        axis_y.setTitleText(self.t("chart.delta_mb"))
        axis_y.setLabelFormat("%.1f")

        chart.addAxis(axis_x, Qt.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_x)
        series.attachAxis(axis_y)
        chart.legend().hide()
        self.timeline_chart.setChart(chart)

    def _refresh_sources_chart(self, rows) -> None:
        shares = category_growth(rows, hours=24)
        if not shares:
            self.sources_chart.setChart(self._empty_chart(self.t("chart.sources")))
            return

        chart = QChart()
        chart.setTitle(self.t("chart.sources"))
        series = QPieSeries()
        for share in shares:
            series.append(f"{share.category} ({format_bytes(share.growth_bytes)})", share.growth_bytes)
        for slice_item in series.slices():
            slice_item.setLabelVisible(True)
        chart.addSeries(series)
        chart.legend().setVisible(True)
        self.sources_chart.setChart(chart)

    def _refresh_heatmap(self, rows) -> None:
        cells = heatmap_cells(rows, days=7)
        day_labels = []
        by_key = {}
        for cell in cells:
            if cell.day_label not in day_labels:
                day_labels.append(cell.day_label)
            by_key[(cell.day_label, cell.hour)] = cell

        self.heatmap_table.setVerticalHeaderLabels(day_labels)
        for row_index, day_label in enumerate(day_labels):
            for hour in range(24):
                cell = by_key[(day_label, hour)]
                text = "" if cell.event_count == 0 else str(cell.event_count)
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                item.setBackground(QBrush(_heat_color(cell.intensity)))
                self.heatmap_table.setItem(row_index, hour, item)
        self.heatmap_table.resizeColumnsToContents()

    def _refresh_cleanup(self, rows) -> None:
        recommendations = cleanup_recommendations(rows)
        self.cleanup_table.setRowCount(len(recommendations))
        for row_index, item in enumerate(recommendations):
            values = [
                self.t(f"risk.{item.risk}"),
                item.rule_name,
                format_bytes(item.size_bytes),
                self.t(f"cleanup.{item.suggestion_key}"),
            ]
            for column, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                if column == 0:
                    table_item.setBackground(QBrush(_risk_color(item.risk)))
                if column == 2:
                    table_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.cleanup_table.setItem(row_index, column, table_item)
        self.cleanup_table.resizeColumnsToContents()

    def change_language(self, _index: int | None = None) -> None:
        language = self.language_combo.currentData()
        normalized = normalize_language(str(language))
        if normalized == self.language:
            return
        self.settings = replace(self.settings, language=normalized)
        save_settings(self.settings)
        self.language = normalized
        self._build_ui()
        self.refresh_all()

    def clear_history(self) -> None:
        result = QMessageBox.question(
            self,
            self.t("dialog.clear_title"),
            self.t("dialog.clear_body"),
        )
        if result == QMessageBox.Yes:
            self.database.clear_history()
            self.refresh_all()

    def closeEvent(self, event) -> None:
        self.stop_monitoring()
        self.database.close()
        event.accept()

    def _empty_chart(self, title: str) -> QChart:
        chart = QChart()
        chart.setTitle(f"{title} - {self.t('chart.empty')}")
        chart.legend().hide()
        return chart


def _to_mb(value: int) -> float:
    return value / 1024 / 1024


def _heat_color(intensity: float) -> QColor:
    bounded = max(0.0, min(1.0, intensity))
    red = 255 - int(90 * bounded)
    green = 255 - int(160 * bounded)
    blue = 255 - int(210 * bounded)
    return QColor(red, green, blue)


def _risk_color(risk: str) -> QColor:
    if risk == "safe":
        return QColor(218, 245, 226)
    if risk == "caution":
        return QColor(255, 240, 204)
    return QColor(238, 238, 238)


def run_app() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
