from __future__ import annotations

import sys
import os
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

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
from PySide6.QtCore import QDateTime, QTimer, Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
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
    build_investigation_window,
    directory_rankings,
    heatmap_cells,
    investigation_windows,
    snapshot_summary,
    timeline_by_hour,
)
from disk_history.activity_log import activity_log_writer, detect_growth_alert
from disk_history.background import focus_roots_from_settings
from disk_history.config import MonitorRule, NoiseRule, app_data_dir, database_path
from disk_history.database import DiskHistoryDatabase, GrowthAlertRecord
from disk_history.focus_targets import (
    focus_target_remaining_text,
    focus_target_status,
    format_focus_time,
)
from disk_history.i18n import SUPPORTED_LANGUAGES, normalize_language, translate
from disk_history.notifications import TrayNotifier
from disk_history.privacy import DETAILED, IGNORE, SUMMARY
from disk_history.reports import build_investigation_report, default_report_path, write_report
from disk_history.scanner import (
    capture_drive_snapshots,
    capture_focus_snapshots,
    capture_noise_snapshots,
    capture_snapshots,
    capture_tree_snapshots,
    child_size_rankings,
    default_excluded_roots,
    format_bytes,
    tree_roots_from_monitor_rules,
)
from disk_history.settings import (
    load_settings,
    resolved_focus_log_directory,
    resolved_log_directory,
    save_settings,
    settings_path,
)
from disk_history.startup import (
    disable_start_on_login,
    enable_start_on_login,
    is_start_on_login_enabled,
)
from disk_history.trends import drive_subjects, drive_trend, latest_tree_growth, tree_subjects, tree_trend
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
        self.custom_investigation_range: tuple[datetime, datetime] | None = None
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
        self.tabs.addTab(self._drives_tab(), self.t("tab.drives"))
        self.tabs.addTab(self._tree_tab(), self.t("tab.tree"))
        self.tabs.addTab(self._timeline_tab(), self.t("tab.timeline"))
        self.tabs.addTab(self._investigation_tab(), self.t("tab.investigation"))
        self.tabs.addTab(self._noise_tab(), self.t("tab.noise"))
        self.tabs.addTab(self._focus_tab(), self.t("tab.focus"))
        self.tabs.addTab(self._growth_tab(), self.t("tab.growth"))
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

    def _drives_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        trend_row = QHBoxLayout()
        self.drive_trend_combo = QComboBox()
        self.drive_trend_combo.currentIndexChanged.connect(self.refresh_drive_trend)
        trend_row.addWidget(QLabel(self.t("label.drive_trend_subject")))
        trend_row.addWidget(self.drive_trend_combo)
        trend_row.addStretch(1)
        layout.addLayout(trend_row)

        self.drive_trend_chart = QChartView()
        self.drive_trend_chart.setMinimumHeight(260)
        layout.addWidget(self.drive_trend_chart)

        self.drive_table = QTableWidget(0, 5)
        self.drive_table.setHorizontalHeaderLabels(
            [
                self.t("table.drive"),
                self.t("table.total_size"),
                self.t("table.used_size"),
                self.t("table.free_size"),
                self.t("table.time"),
            ]
        )
        layout.addWidget(self.drive_table)
        return widget

    def _tree_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        trend_row = QHBoxLayout()
        self.tree_trend_combo = QComboBox()
        self.tree_trend_combo.currentIndexChanged.connect(self.refresh_tree_trend)
        trend_row.addWidget(QLabel(self.t("label.tree_trend_subject")))
        trend_row.addWidget(self.tree_trend_combo)
        trend_row.addStretch(1)
        layout.addLayout(trend_row)

        self.tree_trend_chart = QChartView()
        self.tree_trend_chart.setMinimumHeight(260)
        layout.addWidget(self.tree_trend_chart)

        self.tree_table = QTableWidget(0, 7)
        self.tree_table.setHorizontalHeaderLabels(
            [
                self.t("table.drive"),
                self.t("table.path"),
                self.t("table.depth"),
                self.t("table.size"),
                self.t("table.files"),
                self.t("table.strategy"),
                self.t("table.time"),
            ]
        )
        layout.addWidget(self.tree_table)
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

        custom_range_row = QHBoxLayout()
        self.custom_start_edit = QDateTimeEdit()
        self.custom_start_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.custom_start_edit.setCalendarPopup(True)
        self.custom_end_edit = QDateTimeEdit()
        self.custom_end_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.custom_end_edit.setCalendarPopup(True)
        now = QDateTime.currentDateTime()
        self.custom_start_edit.setDateTime(now.addSecs(-2 * 60 * 60))
        self.custom_end_edit.setDateTime(now)
        self.apply_custom_range_button = QPushButton(self.t("button.apply_time_range"))
        self.apply_custom_range_button.clicked.connect(self.apply_custom_investigation_range)
        self.custom_range_status_label = QLabel()
        custom_range_row.addWidget(QLabel(self.t("label.custom_start_time")))
        custom_range_row.addWidget(self.custom_start_edit)
        custom_range_row.addWidget(QLabel(self.t("label.custom_end_time")))
        custom_range_row.addWidget(self.custom_end_edit)
        custom_range_row.addWidget(self.apply_custom_range_button)
        custom_range_row.addWidget(self.custom_range_status_label)
        custom_range_row.addStretch(1)
        layout.addLayout(custom_range_row)

        report_row = QHBoxLayout()
        self.redact_report_paths_check = QCheckBox(self.t("label.redact_report_paths"))
        self.redact_report_paths_check.setChecked(True)
        self.export_report_button = QPushButton(self.t("button.export_report"))
        self.export_report_button.clicked.connect(self.export_investigation_report)
        self.report_status_label = QLabel()
        report_row.addWidget(self.redact_report_paths_check)
        report_row.addWidget(self.export_report_button)
        report_row.addWidget(self.report_status_label)
        report_row.addStretch(1)
        layout.addLayout(report_row)

        drilldown_row = QHBoxLayout()
        self.drilldown_rule_combo = QComboBox()
        self._populate_drilldown_rules()
        self.scan_drilldown_button = QPushButton(self.t("button.scan_drilldown"))
        self.scan_drilldown_button.clicked.connect(self.scan_drilldown)
        self.drilldown_status_label = QLabel()
        drilldown_row.addWidget(QLabel(self.t("label.drilldown_rule")))
        drilldown_row.addWidget(self.drilldown_rule_combo)
        drilldown_row.addWidget(self.scan_drilldown_button)
        drilldown_row.addWidget(self.drilldown_status_label)
        drilldown_row.addStretch(1)
        layout.addLayout(drilldown_row)

        self.drilldown_table = QTableWidget(0, 5)
        self.drilldown_table.setHorizontalHeaderLabels(
            [
                self.t("table.name"),
                self.t("table.size"),
                self.t("table.files"),
                self.t("table.type"),
                self.t("table.path"),
            ]
        )
        layout.addWidget(self.drilldown_table)

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

        self.event_evidence_label = QLabel(self.t("label.event_evidence"))
        layout.addWidget(self.event_evidence_label)
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

    def _noise_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel(self.t("label.noise_rules_intro")))
        self.noise_table = QTableWidget(0, 3)
        self.noise_table.setHorizontalHeaderLabels(
            [
                self.t("table.enabled"),
                self.t("table.name"),
                self.t("table.path_template"),
            ]
        )
        self._populate_noise_table(self.settings.noise_rules)
        layout.addWidget(self.noise_table)

        noise_actions = QHBoxLayout()
        self.add_noise_button = QPushButton(self.t("button.add_noise"))
        self.add_noise_button.clicked.connect(self.add_noise_rule)
        self.remove_noise_button = QPushButton(self.t("button.remove_noise"))
        self.remove_noise_button.clicked.connect(self.remove_selected_noise_rule)
        self.browse_noise_button = QPushButton(self.t("button.choose_noise_directory"))
        self.browse_noise_button.clicked.connect(self.choose_noise_directory)
        noise_actions.addWidget(self.add_noise_button)
        noise_actions.addWidget(self.remove_noise_button)
        noise_actions.addWidget(self.browse_noise_button)
        noise_actions.addStretch(1)
        layout.addLayout(noise_actions)
        return widget

    def _focus_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel(self.t("label.focus_targets_intro")))
        self.focus_table = QTableWidget(0, 7)
        self.focus_table.setHorizontalHeaderLabels(
            [
                self.t("table.enabled"),
                self.t("table.name"),
                self.t("table.path_template"),
                self.t("table.depth"),
                self.t("table.ttl_hours"),
                self.t("table.status"),
                self.t("table.remaining"),
            ]
        )
        self._populate_focus_table(self.settings.focus_targets)
        layout.addWidget(self.focus_table)

        focus_actions = QHBoxLayout()
        self.add_focus_button = QPushButton(self.t("button.add_focus"))
        self.add_focus_button.clicked.connect(self.add_focus_target)
        self.remove_focus_button = QPushButton(self.t("button.remove_focus"))
        self.remove_focus_button.clicked.connect(self.remove_selected_focus_target)
        self.pause_focus_button = QPushButton(self.t("button.pause_focus"))
        self.pause_focus_button.clicked.connect(self.pause_selected_focus_target)
        self.resume_focus_button = QPushButton(self.t("button.resume_focus"))
        self.resume_focus_button.clicked.connect(self.resume_selected_focus_target)
        self.browse_focus_button = QPushButton(self.t("button.choose_focus_directory"))
        self.browse_focus_button.clicked.connect(self.choose_focus_directory)
        self.open_focus_log_button = QPushButton(self.t("button.open_focus_logs"))
        self.open_focus_log_button.clicked.connect(self.open_focus_logs)
        focus_actions.addWidget(self.add_focus_button)
        focus_actions.addWidget(self.remove_focus_button)
        focus_actions.addWidget(self.pause_focus_button)
        focus_actions.addWidget(self.resume_focus_button)
        focus_actions.addWidget(self.browse_focus_button)
        focus_actions.addWidget(self.open_focus_log_button)
        focus_actions.addStretch(1)
        layout.addLayout(focus_actions)

        self.focus_log_label = QLabel(self.t("label.focus_log_directory", path=resolved_focus_log_directory()))
        layout.addWidget(self.focus_log_label)
        return widget

    def _growth_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel(self.t("label.growth_intro")))
        self.growth_table = QTableWidget(0, 7)
        self.growth_table.setHorizontalHeaderLabels(
            [
                self.t("table.time"),
                self.t("table.scope"),
                self.t("table.subject"),
                self.t("table.delta"),
                self.t("table.window"),
                self.t("table.threshold"),
                self.t("table.details"),
            ]
        )
        layout.addWidget(self.growth_table)
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

        layout.addWidget(QLabel(self.t("label.monitor_rules_editor")))
        self.rule_table = QTableWidget(0, 5)
        self.rule_table.setHorizontalHeaderLabels(
            [
                self.t("table.enabled"),
                self.t("table.rule"),
                self.t("table.privacy"),
                self.t("table.recursive"),
                self.t("table.path_template"),
            ]
        )
        self._populate_rule_table(self.settings.monitor_rules)
        layout.addWidget(self.rule_table)

        rule_actions = QHBoxLayout()
        self.add_rule_button = QPushButton(self.t("button.add_rule"))
        self.add_rule_button.clicked.connect(self.add_monitor_rule)
        self.remove_rule_button = QPushButton(self.t("button.remove_rule"))
        self.remove_rule_button.clicked.connect(self.remove_selected_monitor_rule)
        self.browse_rule_button = QPushButton(self.t("button.choose_rule_directory"))
        self.browse_rule_button.clicked.connect(self.choose_monitor_rule_directory)
        rule_actions.addWidget(self.add_rule_button)
        rule_actions.addWidget(self.remove_rule_button)
        rule_actions.addWidget(self.browse_rule_button)
        rule_actions.addStretch(1)
        layout.addLayout(rule_actions)

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
        if self.settings.drive_monitoring_enabled:
            self.database.insert_drive_snapshots(capture_drive_snapshots(self.settings.monitored_drives))
        tree_roots = tree_roots_from_monitor_rules(self.settings.monitor_rules, self._excluded_roots())
        self.database.insert_tree_snapshots(
            capture_tree_snapshots(
                tree_roots,
                max_depth=self.settings.standard_tree_depth,
                excluded_roots=self._excluded_roots(),
            )
        )
        self.database.insert_tree_snapshots(
            capture_noise_snapshots(self.settings.noise_rules, excluded_roots=self._excluded_roots())
        )
        self.database.insert_focus_snapshots(
            capture_focus_snapshots(
                self.settings.focus_targets,
                max_depth=self.settings.focus_tree_depth,
                excluded_roots=self._excluded_roots(),
            )
        )
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
            self.settings.noise_rules,
            focus_roots_from_settings(self.settings),
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
        drive_history = self.database.drive_snapshot_history()
        tree_history = self.database.tree_snapshot_history()
        self._refresh_drives(self.database.latest_drive_snapshots(), drive_history)
        self._refresh_tree(self.database.latest_tree_snapshots(), tree_history)
        self._refresh_events(events)
        self._refresh_investigation(snapshot_history)
        self._refresh_growth_alerts()
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

    def _refresh_drives(self, rows, history_rows=None) -> None:
        if not hasattr(self, "drive_table"):
            return
        if history_rows is not None:
            self._populate_combo_preserving(
                self.drive_trend_combo,
                drive_subjects(history_rows),
            )
            self.refresh_drive_trend()
        self.drive_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                row["drive"],
                format_bytes(row["total_bytes"]),
                format_bytes(row["used_bytes"]),
                format_bytes(row["free_bytes"]),
                row["captured_at"],
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column in {1, 2, 3}:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.drive_table.setItem(row_index, column, item)
        self.drive_table.resizeColumnsToContents()

    def _refresh_tree(self, rows, history_rows=None) -> None:
        if not hasattr(self, "tree_table"):
            return
        if history_rows is not None:
            self._populate_combo_preserving(
                self.tree_trend_combo,
                tree_subjects(history_rows),
            )
            self.refresh_tree_trend()
        self.tree_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                row["drive"],
                row["path"],
                str(row["depth"]),
                format_bytes(row["size_bytes"]),
                str(row["file_count"]),
                row["strategy"],
                row["captured_at"],
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column in {2, 3, 4}:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tree_table.setItem(row_index, column, item)
        self.tree_table.resizeColumnsToContents()

    def refresh_drive_trend(self, _index: int | None = None) -> None:
        if not hasattr(self, "drive_trend_chart"):
            return
        drive = self.drive_trend_combo.currentText()
        if not drive:
            self.drive_trend_chart.setChart(self._empty_chart(self.t("chart.drive_trend")))
            return
        points = drive_trend(self.database.drive_snapshot_history(), drive)
        self.drive_trend_chart.setChart(self._line_chart(self.t("chart.drive_trend"), points))

    def refresh_tree_trend(self, _index: int | None = None) -> None:
        if not hasattr(self, "tree_trend_chart"):
            return
        path = self.tree_trend_combo.currentText()
        if not path:
            self.tree_trend_chart.setChart(self._empty_chart(self.t("chart.tree_trend")))
            return
        points = tree_trend(self.database.tree_snapshot_history(), path)
        self.tree_trend_chart.setChart(self._line_chart(self.t("chart.tree_trend"), points))

    def _populate_combo_preserving(self, combo: QComboBox, values: list[str]) -> None:
        current = combo.currentText()
        combo.blockSignals(True)
        combo.clear()
        for value in values:
            combo.addItem(value)
        if current:
            index = combo.findText(current)
            if index >= 0:
                combo.setCurrentIndex(index)
        combo.blockSignals(False)

    def _refresh_growth_alerts(self) -> None:
        if not hasattr(self, "growth_table"):
            return
        alerts = list(self.database.recent_growth_alerts(limit=200))
        alerts.extend(_growth_rows_to_alert_like(latest_tree_growth(self.database.tree_snapshot_history())))
        self.growth_table.setRowCount(len(alerts))
        for row_index, row in enumerate(alerts):
            if isinstance(row, dict):
                values = [
                    str(row["end_time"]),
                    str(row["scope"]),
                    str(row["subject"]),
                    format_bytes(int(row["delta_bytes"])),
                    "",
                    "",
                    self.t("label.derived_growth_detail"),
                ]
            else:
                values = [
                    row["happened_at"],
                    row["scope"],
                    row["subject"],
                    format_bytes(row["net_growth_bytes"]),
                    str(row["window_minutes"]),
                    format_bytes(row["threshold_bytes"]),
                    row["details_json"],
                ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column in {3, 4, 5}:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.growth_table.setItem(row_index, column, item)
        self.growth_table.resizeColumnsToContents()

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

        if self.custom_investigation_range is not None:
            start_at, end_at = self.custom_investigation_range
            custom_window = build_investigation_window(
                snapshot_rows,
                label_key="window.custom",
                start_at=start_at,
                end_at=end_at,
            )
            custom_label = self.t("window.custom")
            if custom_window.has_enough_data:
                summary_lines.append(
                    self.t(
                        "investigation.summary",
                        window=custom_label,
                        delta=format_bytes(custom_window.net_delta_bytes),
                        start=custom_window.start_at.strftime("%Y-%m-%d %H:%M"),
                        end=custom_window.end_at.strftime("%Y-%m-%d %H:%M"),
                    )
                )
                for delta in custom_window.deltas:
                    table_rows.append((custom_label, delta))
            else:
                summary_lines.append(
                    self.t("investigation.not_enough_data", window=custom_label)
                )

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

        event_start, event_end = windows[1].start_at, windows[1].end_at
        if self.custom_investigation_range is not None:
            event_start, event_end = self.custom_investigation_range
            self.event_evidence_label.setText(self.t("label.event_evidence_custom"))
        else:
            self.event_evidence_label.setText(self.t("label.event_evidence"))
        recent_events = self.database.events_between(event_start, event_end, limit=200)
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

    def apply_custom_investigation_range(self) -> None:
        start_at = _qdatetime_to_utc(self.custom_start_edit.dateTime())
        end_at = _qdatetime_to_utc(self.custom_end_edit.dateTime())
        if start_at >= end_at:
            self.custom_range_status_label.setText(self.t("label.time_range_error"))
            return
        self.custom_investigation_range = (start_at, end_at)
        self.custom_range_status_label.setText(self.t("label.time_range_applied"))
        self.refresh_all()

    def _populate_drilldown_rules(self) -> None:
        self.drilldown_rule_combo.clear()
        for rule in self.settings.monitor_rules:
            if rule.enabled and rule.privacy_mode != IGNORE:
                self.drilldown_rule_combo.addItem(rule.name, rule.path_template)

    def scan_drilldown(self) -> None:
        path_template = self.drilldown_rule_combo.currentData()
        if path_template is None:
            self.drilldown_status_label.setText(self.t("label.drilldown_no_rule"))
            return
        rule_path = MonitorRule(
            self.drilldown_rule_combo.currentText(),
            str(path_template),
            SUMMARY,
        ).resolved_path()
        rows = child_size_rankings(rule_path, self._excluded_roots())
        self.drilldown_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                row.name,
                format_bytes(row.size_bytes),
                str(row.file_count),
                self.t("label.directory") if row.is_directory else self.t("label.file"),
                str(row.path),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in {1, 2}:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.drilldown_table.setItem(row_index, column, item)
        self.drilldown_table.resizeColumnsToContents()
        self.drilldown_status_label.setText(self.t("label.drilldown_done", count=len(rows)))

    def export_investigation_report(self) -> None:
        snapshot_rows = self.database.snapshot_history()
        if self.custom_investigation_range is not None:
            start_at, end_at = self.custom_investigation_range
        else:
            windows = investigation_windows(snapshot_rows)
            start_at, end_at = windows[1].start_at, windows[1].end_at

        event_rows = self.database.events_between(start_at, end_at, limit=1000)
        content = build_investigation_report(
            snapshot_rows,
            event_rows,
            start_at=start_at,
            end_at=end_at,
            redact_private_paths=self.redact_report_paths_check.isChecked(),
        )
        default_path = default_report_path(app_data_dir())
        selected, _filter = QFileDialog.getSaveFileName(
            self,
            self.t("dialog.export_report"),
            str(default_path),
            "Markdown (*.md)",
        )
        if not selected:
            return
        write_report(Path(selected), content)
        self.report_status_label.setText(self.t("label.report_exported", path=selected))

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
        return default_excluded_roots(
            (resolved_log_directory(self.settings), resolved_focus_log_directory())
        )

    def _populate_rule_table(self, rules: tuple[MonitorRule, ...]) -> None:
        self.rule_table.setRowCount(0)
        for rule in rules:
            self._append_rule_row(rule)
        self.rule_table.resizeColumnsToContents()

    def _populate_noise_table(self, rules: tuple[NoiseRule, ...]) -> None:
        self.noise_table.setRowCount(0)
        for rule in rules:
            row = self.noise_table.rowCount()
            self.noise_table.insertRow(row)
            self.noise_table.setItem(row, 0, _check_item(rule.enabled))
            self.noise_table.setItem(row, 1, QTableWidgetItem(rule.name))
            self.noise_table.setItem(row, 2, QTableWidgetItem(rule.path_template))
        self.noise_table.resizeColumnsToContents()

    def _populate_focus_table(self, targets: tuple[dict[str, object], ...]) -> None:
        self.focus_table.setRowCount(0)
        for target in targets:
            row = self.focus_table.rowCount()
            self.focus_table.insertRow(row)
            self.focus_table.setItem(row, 0, _check_item(bool(target.get("enabled", True))))
            self.focus_table.setItem(row, 1, QTableWidgetItem(str(target.get("name", ""))))
            self.focus_table.setItem(
                row,
                2,
                QTableWidgetItem(str(target.get("path_template", target.get("path", "")))),
            )
            self.focus_table.setItem(row, 3, QTableWidgetItem(str(target.get("max_depth", 8))))
            self.focus_table.setItem(row, 4, QTableWidgetItem(str(target.get("ttl_hours", 24))))
            self.focus_table.setItem(row, 5, QTableWidgetItem(self.t(f"focus_status.{focus_target_status(target)}")))
            self.focus_table.setItem(row, 6, QTableWidgetItem(focus_target_remaining_text(target)))
        self.focus_table.resizeColumnsToContents()

    def _append_rule_row(self, rule: MonitorRule) -> None:
        row = self.rule_table.rowCount()
        self.rule_table.insertRow(row)

        enabled_item = _check_item(rule.enabled)
        self.rule_table.setItem(row, 0, enabled_item)
        self.rule_table.setItem(row, 1, QTableWidgetItem(rule.name))

        privacy_combo = QComboBox()
        for mode in (DETAILED, SUMMARY, IGNORE):
            privacy_combo.addItem(self.t(f"privacy.{mode}"), mode)
        privacy_combo.setCurrentIndex(max(0, privacy_combo.findData(rule.privacy_mode)))
        self.rule_table.setCellWidget(row, 2, privacy_combo)

        recursive_item = _check_item(rule.recursive)
        self.rule_table.setItem(row, 3, recursive_item)
        self.rule_table.setItem(row, 4, QTableWidgetItem(rule.path_template))

    def add_monitor_rule(self) -> None:
        self._append_rule_row(
            MonitorRule(
                self.t("default.custom_rule_name"),
                "",
                SUMMARY,
                enabled=True,
                recursive=True,
            )
        )
        self.rule_table.setCurrentCell(self.rule_table.rowCount() - 1, 4)

    def remove_selected_monitor_rule(self) -> None:
        row = self.rule_table.currentRow()
        if row < 0:
            self.settings_status_label.setText(self.t("label.rule_select_first"))
            return
        self.rule_table.removeRow(row)

    def add_noise_rule(self) -> None:
        row = self.noise_table.rowCount()
        self.noise_table.insertRow(row)
        self.noise_table.setItem(row, 0, _check_item(True))
        self.noise_table.setItem(row, 1, QTableWidgetItem(self.t("default.noise_rule_name")))
        self.noise_table.setItem(row, 2, QTableWidgetItem(""))
        self.noise_table.setCurrentCell(row, 2)

    def remove_selected_noise_rule(self) -> None:
        row = self.noise_table.currentRow()
        if row < 0:
            self.settings_status_label.setText(self.t("label.noise_select_first"))
            return
        self.noise_table.removeRow(row)

    def add_focus_target(self) -> None:
        row = self.focus_table.rowCount()
        self.focus_table.insertRow(row)
        self.focus_table.setItem(row, 0, _check_item(True))
        self.focus_table.setItem(row, 1, QTableWidgetItem(self.t("default.focus_target_name")))
        self.focus_table.setItem(row, 2, QTableWidgetItem(""))
        self.focus_table.setItem(row, 3, QTableWidgetItem(str(self.settings.focus_tree_depth)))
        self.focus_table.setItem(row, 4, QTableWidgetItem(str(self.settings.focus_default_ttl_hours)))
        self.focus_table.setItem(row, 5, QTableWidgetItem(self.t("focus_status.active")))
        self.focus_table.setItem(row, 6, QTableWidgetItem(""))
        self.focus_table.setCurrentCell(row, 2)

    def remove_selected_focus_target(self) -> None:
        row = self.focus_table.currentRow()
        if row < 0:
            self.settings_status_label.setText(self.t("label.focus_select_first"))
            return
        self.focus_table.removeRow(row)

    def pause_selected_focus_target(self) -> None:
        self._set_selected_focus_enabled(False)

    def resume_selected_focus_target(self) -> None:
        self._set_selected_focus_enabled(True)

    def _set_selected_focus_enabled(self, enabled: bool) -> None:
        row = self.focus_table.currentRow()
        if row < 0:
            self.settings_status_label.setText(self.t("label.focus_select_first"))
            return
        self.focus_table.setItem(row, 0, _check_item(enabled))

    def choose_monitor_rule_directory(self) -> None:
        row = self.rule_table.currentRow()
        if row < 0:
            self.settings_status_label.setText(self.t("label.rule_select_first"))
            return
        path_item = self.rule_table.item(row, 4)
        current = path_item.text() if path_item else ""
        selected = QFileDialog.getExistingDirectory(
            self,
            self.t("dialog.choose_monitor_directory"),
            current,
        )
        if selected:
            self.rule_table.setItem(row, 4, QTableWidgetItem(selected))

    def choose_focus_directory(self) -> None:
        row = self.focus_table.currentRow()
        if row < 0:
            self.settings_status_label.setText(self.t("label.focus_select_first"))
            return
        path_item = self.focus_table.item(row, 2)
        current = path_item.text() if path_item else ""
        selected = QFileDialog.getExistingDirectory(
            self,
            self.t("dialog.choose_focus_directory"),
            current,
        )
        if selected:
            self.focus_table.setItem(row, 2, QTableWidgetItem(selected))

    def choose_noise_directory(self) -> None:
        row = self.noise_table.currentRow()
        if row < 0:
            self.settings_status_label.setText(self.t("label.noise_select_first"))
            return
        path_item = self.noise_table.item(row, 2)
        current = path_item.text() if path_item else ""
        selected = QFileDialog.getExistingDirectory(
            self,
            self.t("dialog.choose_noise_directory"),
            current,
        )
        if selected:
            self.noise_table.setItem(row, 2, QTableWidgetItem(selected))

    def open_focus_logs(self) -> None:
        resolved_focus_log_directory().mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(resolved_focus_log_directory())  # type: ignore[attr-defined]
        except OSError as exc:
            self.settings_status_label.setText(self.t("label.focus_log_open_error", message=str(exc)))

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
        monitor_rules = self._monitor_rules_from_table()
        if monitor_rules is None:
            return
        noise_rules = self._noise_rules_from_table()
        if noise_rules is None:
            return
        focus_targets = self._focus_targets_from_table()
        if focus_targets is None:
            return

        was_monitoring = self.watcher is not None and self.watcher.is_running
        if was_monitoring:
            self.stop_monitoring()

        self.settings = replace(
            self.settings,
            monitor_rules=monitor_rules,
            noise_rules=noise_rules,
            focus_targets=focus_targets,
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
        self._populate_drilldown_rules()
        self.focus_log_label.setText(self.t("label.focus_log_directory", path=resolved_focus_log_directory()))

        if was_monitoring:
            self.start_monitoring()

    def _monitor_rules_from_table(self) -> tuple[MonitorRule, ...] | None:
        rules: list[MonitorRule] = []
        for row in range(self.rule_table.rowCount()):
            name_item = self.rule_table.item(row, 1)
            path_item = self.rule_table.item(row, 4)
            name = name_item.text().strip() if name_item else ""
            path_template = path_item.text().strip() if path_item else ""
            if not name:
                self.settings_status_label.setText(self.t("label.rule_error_empty_name", row=row + 1))
                return None
            if not path_template:
                self.settings_status_label.setText(self.t("label.rule_error_empty_path", row=row + 1))
                return None

            privacy_widget = self.rule_table.cellWidget(row, 2)
            privacy_mode = SUMMARY
            if isinstance(privacy_widget, QComboBox):
                privacy_mode = str(privacy_widget.currentData())

            rules.append(
                MonitorRule(
                    name=name,
                    path_template=path_template,
                    privacy_mode=privacy_mode,
                    enabled=_item_checked(self.rule_table.item(row, 0)),
                    recursive=_item_checked(self.rule_table.item(row, 3)),
                )
            )
        return tuple(rules)

    def _noise_rules_from_table(self) -> tuple[NoiseRule, ...] | None:
        rules: list[NoiseRule] = []
        for row in range(self.noise_table.rowCount()):
            name_item = self.noise_table.item(row, 1)
            path_item = self.noise_table.item(row, 2)
            name = name_item.text().strip() if name_item else ""
            path_template = path_item.text().strip() if path_item else ""
            if not name or not path_template:
                self.settings_status_label.setText(self.t("label.noise_rule_error", row=row + 1))
                return None
            rules.append(
                NoiseRule(
                    name=name,
                    path_template=path_template,
                    enabled=_item_checked(self.noise_table.item(row, 0)),
                )
            )
        return tuple(rules)

    def _focus_targets_from_table(self) -> tuple[dict[str, object], ...] | None:
        targets: list[dict[str, object]] = []
        for row in range(self.focus_table.rowCount()):
            name_item = self.focus_table.item(row, 1)
            path_item = self.focus_table.item(row, 2)
            depth_item = self.focus_table.item(row, 3)
            ttl_item = self.focus_table.item(row, 4)
            name = name_item.text().strip() if name_item else ""
            path_template = path_item.text().strip() if path_item else ""
            if not name or not path_template:
                self.settings_status_label.setText(self.t("label.focus_rule_error", row=row + 1))
                return None
            existing = self.settings.focus_targets[row] if row < len(self.settings.focus_targets) else {}
            targets.append(
                {
                    "id": str(existing.get("id") or f"focus-{row + 1}"),
                    "name": name,
                    "path_template": path_template,
                    "enabled": _item_checked(self.focus_table.item(row, 0)),
                    "max_depth": _positive_int_item(depth_item, self.settings.focus_tree_depth),
                    "snapshot_interval_minutes": self.settings.focus_snapshot_interval_minutes,
                    "ttl_hours": _positive_int_item(ttl_item, self.settings.focus_default_ttl_hours),
                    "created_at": str(existing.get("created_at") or format_focus_time(datetime.now(UTC))),
                }
            )
        return tuple(targets)

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
        self.database.insert_growth_alert(
            GrowthAlertRecord(
                happened_at=alert.happened_at,
                scope="directory",
                subject="monitored_rules",
                window_minutes=alert.window_minutes,
                threshold_bytes=alert.threshold_bytes,
                net_growth_bytes=alert.net_growth_bytes,
                details_json=json.dumps(alert.top_growth, ensure_ascii=False),
            )
        )
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

    def _line_chart(self, title: str, points) -> QChart:
        if not points:
            return self._empty_chart(title)
        chart = QChart()
        chart.setTitle(title)
        series = QLineSeries()
        for index, point in enumerate(points):
            series.append(index, _to_mb(point.size_bytes))
        chart.addSeries(series)

        axis_x = QValueAxis()
        axis_x.setRange(0, max(len(points) - 1, 1))
        axis_x.setLabelFormat("%d")
        axis_x.setTitleText(self.t("chart.point_index"))
        axis_y = QValueAxis()
        values = [_to_mb(point.size_bytes) for point in points]
        low = min(values)
        high = max(values)
        if low == high:
            low -= 1
            high += 1
        axis_y.setRange(low, high)
        axis_y.setLabelFormat("%.1f")
        axis_y.setTitleText(self.t("chart.size_mb"))
        chart.addAxis(axis_x, Qt.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_x)
        series.attachAxis(axis_y)
        chart.legend().hide()
        return chart


def _to_mb(value: int) -> float:
    return value / 1024 / 1024


def _check_item(checked: bool) -> QTableWidgetItem:
    item = QTableWidgetItem("")
    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
    item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
    item.setTextAlignment(Qt.AlignCenter)
    return item


def _item_checked(item: QTableWidgetItem | None) -> bool:
    return item is not None and item.checkState() == Qt.Checked


def _positive_int_item(item: QTableWidgetItem | None, fallback: int) -> int:
    if item is None:
        return fallback
    try:
        return max(1, int(item.text().strip()))
    except ValueError:
        return fallback


def _qdatetime_to_utc(value: QDateTime) -> datetime:
    converted = value.toUTC().toPython()
    if converted.tzinfo is None:
        return converted.replace(tzinfo=UTC)
    return converted.astimezone(UTC)


def _heat_color(intensity: float) -> QColor:
    bounded = max(0.0, min(1.0, intensity))
    red = 255 - int(90 * bounded)
    green = 255 - int(160 * bounded)
    blue = 255 - int(210 * bounded)
    return QColor(red, green, blue)


def _growth_rows_to_alert_like(rows) -> list[dict[str, object]]:
    return list(rows)


def run_app() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
