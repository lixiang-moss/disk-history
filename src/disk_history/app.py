from __future__ import annotations

import sys
from dataclasses import replace
from datetime import timedelta

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
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from disk_history.analytics import (
    category_growth,
    directory_rankings,
    heatmap_cells,
    investigation_windows,
    snapshot_summary,
    timeline_by_hour,
)
from disk_history.activity_log import activity_log_writer, detect_growth_alert
from disk_history.config import app_data_dir, database_path
from disk_history.database import DiskHistoryDatabase
from disk_history.i18n import SUPPORTED_LANGUAGES, normalize_language, translate
from disk_history.notifications import TrayNotifier
from disk_history.scanner import capture_snapshots, format_bytes
from disk_history.settings import load_settings, resolved_log_directory, save_settings, settings_path
from disk_history.startup import (
    disable_start_on_login,
    enable_start_on_login,
    is_start_on_login_enabled,
)
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
        self.notifier = TrayNotifier()
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
        self.tabs.addTab(self._investigation_tab(), self.t("tab.investigation"))
        self.tabs.addTab(self._sources_tab(), self.t("tab.sources"))
        self.tabs.addTab(self._heatmap_tab(), self.t("tab.heatmap"))
        self.tabs.addTab(self._settings_tab(), self.t("tab.settings"))
        self.setCentralWidget(self.tabs)

    def _overview_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.status_label = QLabel()
        self.summary_label = QLabel()
        self.monitor_status_label = QLabel()
        self.focus_label = QLabel(self.t("label.product_focus"))
        layout.addWidget(self.focus_label)
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

    def _investigation_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel(self.t("label.snapshot_evidence")))

        self.investigation_summary = QTextEdit()
        self.investigation_summary.setReadOnly(True)
        self.investigation_summary.setMaximumHeight(120)
        layout.addWidget(self.investigation_summary)

        self.investigation_table = QTableWidget(0, 6)
        self.investigation_table.setHorizontalHeaderLabels(
            [
                self.t("table.window"),
                self.t("table.rule"),
                self.t("table.delta"),
                self.t("table.start_size"),
                self.t("table.end_size"),
                self.t("table.privacy"),
            ]
        )
        layout.addWidget(self.investigation_table)

        layout.addWidget(QLabel(self.t("label.event_evidence")))
        self.investigation_event_table = QTableWidget(0, 5)
        self.investigation_event_table.setHorizontalHeaderLabels(
            [
                self.t("table.time"),
                self.t("table.event"),
                self.t("table.delta"),
                self.t("table.category"),
                self.t("table.display_path"),
            ]
        )
        layout.addWidget(self.investigation_event_table)
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

        self.startup_status_label = QLabel()
        layout.addWidget(self.startup_status_label)

        settings_form = QFormLayout()
        self.background_interval_spin = QSpinBox()
        self.background_interval_spin.setRange(1, 1440)
        self.background_interval_spin.setValue(self.settings.background_snapshot_interval_minutes)
        settings_form.addRow(self.t("label.background_interval_edit"), self.background_interval_spin)

        self.log_directory_edit = QLineEdit(self.settings.log_directory)
        log_directory_widget = QWidget()
        log_directory_row = QHBoxLayout(log_directory_widget)
        log_directory_row.setContentsMargins(0, 0, 0, 0)
        log_directory_row.addWidget(self.log_directory_edit)
        self.browse_log_button = QPushButton(self.t("button.browse"))
        self.browse_log_button.clicked.connect(self.choose_log_directory)
        log_directory_row.addWidget(self.browse_log_button)
        settings_form.addRow(self.t("label.log_directory_edit"), log_directory_widget)

        self.enable_growth_alerts_check = QCheckBox(self.t("label.enable_growth_alerts"))
        self.enable_growth_alerts_check.setChecked(self.settings.enable_growth_alerts)
        settings_form.addRow("", self.enable_growth_alerts_check)

        self.alert_window_spin = QSpinBox()
        self.alert_window_spin.setRange(1, 10080)
        self.alert_window_spin.setValue(self.settings.alert_window_minutes)
        settings_form.addRow(self.t("label.alert_window_edit"), self.alert_window_spin)

        self.alert_threshold_spin = QSpinBox()
        self.alert_threshold_spin.setRange(1, 10_000_000)
        self.alert_threshold_spin.setValue(self.settings.alert_growth_threshold_mb)
        settings_form.addRow(self.t("label.alert_threshold_edit"), self.alert_threshold_spin)
        layout.addLayout(settings_form)

        settings_row = QHBoxLayout()
        self.save_settings_button = QPushButton(self.t("button.save_settings"))
        self.save_settings_button.clicked.connect(self.save_runtime_settings)
        self.settings_status_label = QLabel()
        settings_row.addWidget(self.save_settings_button)
        settings_row.addWidget(self.settings_status_label)
        settings_row.addStretch(1)
        layout.addLayout(settings_row)

        self.log_directory_resolved_label = QLabel(
            self.t("label.log_directory_resolved", path=resolved_log_directory(self.settings))
        )
        layout.addWidget(self.log_directory_resolved_label)
        startup_row = QHBoxLayout()
        self.enable_startup_button = QPushButton(self.t("button.enable_startup"))
        self.enable_startup_button.clicked.connect(self.enable_startup)
        self.disable_startup_button = QPushButton(self.t("button.disable_startup"))
        self.disable_startup_button.clicked.connect(self.disable_startup)
        startup_row.addWidget(self.enable_startup_button)
        startup_row.addWidget(self.disable_startup_button)
        startup_row.addStretch(1)
        layout.addLayout(startup_row)

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
        snapshots = capture_snapshots(self.settings.monitor_rules, self._excluded_roots())
        self.database.insert_snapshots(snapshots)
        self._write_activity_logs_and_alert(snapshots)
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
            self._excluded_roots(),
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
        snapshot_history = self.database.snapshot_history()
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
        self._refresh_investigation(snapshot_history)
        self._refresh_directory_chart(snapshots)
        self._refresh_timeline_chart(events)
        self._refresh_sources_chart(events)
        self._refresh_heatmap(events)
        self._refresh_startup_status()

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

    def _refresh_investigation(self, snapshot_rows) -> None:
        windows = investigation_windows(snapshot_rows)
        summary_lines = []
        table_rows = []
        for window in windows:
            window_label = self.t(window.label_key)
            if not window.has_enough_data:
                summary_lines.append(self.t("investigation.not_enough_data", window=window_label))
                continue

            summary_lines.append(
                self.t(
                    "investigation.summary",
                    window=window_label,
                    delta=format_bytes(window.net_delta_bytes),
                    start=window.start_at.strftime("%Y-%m-%d %H:%M"),
                    end=window.end_at.strftime("%Y-%m-%d %H:%M"),
                )
            )
            for delta in window.deltas:
                table_rows.append((window_label, delta))

        self.investigation_summary.setPlainText("\n".join(summary_lines))
        self.investigation_table.setRowCount(len(table_rows))
        for row_index, (window_label, delta) in enumerate(table_rows):
            values = [
                window_label,
                delta.rule_name,
                format_bytes(delta.delta_bytes),
                format_bytes(delta.start_size_bytes),
                format_bytes(delta.end_size_bytes),
                delta.privacy_mode,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in {2, 3, 4}:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.investigation_table.setItem(row_index, column, item)
        self.investigation_table.resizeColumnsToContents()

        recent_events = self.database.events_between(windows[1].start_at, windows[1].end_at, limit=200)
        self.investigation_event_table.setRowCount(len(recent_events))
        for row_index, row in enumerate(recent_events):
            values = [
                row["happened_at"],
                row["event_type"],
                format_bytes(row["delta_bytes"]),
                row["category"],
                row["display_path"],
            ]
            for column, value in enumerate(values):
                self.investigation_event_table.setItem(row_index, column, QTableWidgetItem(value))
        self.investigation_event_table.resizeColumnsToContents()

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

    def enable_startup(self) -> None:
        try:
            enable_start_on_login()
        except (OSError, RuntimeError) as exc:
            self.startup_status_label.setText(
                self.t("label.startup_status_error", message=str(exc))
            )
            return
        self.settings = replace(self.settings, start_on_login=True)
        save_settings(self.settings)
        self._refresh_startup_status()

    def disable_startup(self) -> None:
        try:
            disable_start_on_login()
        except OSError as exc:
            self.startup_status_label.setText(
                self.t("label.startup_status_error", message=str(exc))
            )
            return
        self.settings = replace(self.settings, start_on_login=False)
        save_settings(self.settings)
        self._refresh_startup_status()

    def _refresh_startup_status(self) -> None:
        if not hasattr(self, "startup_status_label"):
            return
        enabled = is_start_on_login_enabled()
        self.startup_status_label.setText(
            self.t("label.startup_status_enabled")
            if enabled
            else self.t("label.startup_status_disabled")
        )
        self.enable_startup_button.setEnabled(not enabled)
        self.disable_startup_button.setEnabled(enabled)

    def _excluded_roots(self):
        return (resolved_log_directory(self.settings),)

    def choose_log_directory(self) -> None:
        current = str(resolved_log_directory(self.settings))
        selected = QFileDialog.getExistingDirectory(
            self,
            self.t("dialog.choose_log_directory"),
            current,
        )
        if selected:
            self.log_directory_edit.setText(selected)

    def save_runtime_settings(self) -> None:
        log_directory = self.log_directory_edit.text().strip()
        if not log_directory:
            self.settings_status_label.setText(self.t("label.settings_error_empty_log_directory"))
            return

        was_monitoring = self.watcher is not None and self.watcher.is_running
        if was_monitoring:
            self.stop_monitoring()

        self.settings = replace(
            self.settings,
            background_snapshot_interval_minutes=self.background_interval_spin.value(),
            log_directory=log_directory,
            enable_growth_alerts=self.enable_growth_alerts_check.isChecked(),
            alert_window_minutes=self.alert_window_spin.value(),
            alert_growth_threshold_mb=self.alert_threshold_spin.value(),
        )
        save_settings(self.settings)
        self.settings_status_label.setText(self.t("label.settings_saved"))
        self.log_directory_resolved_label.setText(
            self.t("label.log_directory_resolved", path=resolved_log_directory(self.settings))
        )

        if was_monitoring:
            self.start_monitoring()

    def _write_activity_logs_and_alert(self, snapshots) -> None:
        writer = activity_log_writer(self.settings)
        writer.append_snapshots(snapshots)
        if not snapshots:
            return

        now = snapshots[0].captured_at
        event_rows = self.database.events_between(
            now - timedelta(minutes=self.settings.alert_window_minutes),
            now,
            limit=1000,
        )
        writer.append_event_rows(event_rows, now)
        alert = detect_growth_alert(
            self.database.snapshot_history(),
            settings=self.settings,
            now=now,
        )
        if alert is None:
            return
        writer.append_alert(alert)
        self.notifier.show_message(
            self.t("notification.growth_alert.title"),
            self.t(
                "notification.growth_alert.body",
                minutes=alert.window_minutes,
                size=format_bytes(alert.net_growth_bytes),
            ),
        )

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


def run_app() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
