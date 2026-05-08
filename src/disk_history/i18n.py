from __future__ import annotations


DEFAULT_LANGUAGE = "zh-CN"
SUPPORTED_LANGUAGES = {
    "zh-CN": "中文",
    "en": "English",
}


TRANSLATIONS: dict[str, dict[str, str]] = {
    "zh-CN": {
        "app.title": "Disk History",
        "tab.overview": "概览",
        "tab.timeline": "时间线",
        "tab.sources": "来源占比",
        "tab.heatmap": "活动热力图",
        "tab.investigation": "调查",
        "tab.settings": "设置",
        "button.scan_once": "扫描一次",
        "button.refresh": "刷新",
        "button.start_monitoring": "开始实时监听",
        "button.stop_monitoring": "停止实时监听",
        "button.enable_startup": "开启随开机启动",
        "button.disable_startup": "关闭随开机启动",
        "button.clear_history": "清空本地历史",
        "button.browse": "选择...",
        "button.save_settings": "保存设置",
        "button.add_rule": "添加监控规则",
        "button.remove_rule": "删除选中规则",
        "button.choose_rule_directory": "选择监控目录...",
        "label.product_focus": "定位：记录磁盘空间变化证据，帮助你自己分析原因。",
        "label.snapshot_evidence": "快照对比证据",
        "label.event_evidence": "文件事件辅助线索（最近 2 小时）",
        "label.local_database": "本地数据库：{path}",
        "label.data_folder": "数据目录：{path}",
        "label.settings_file": "配置文件：{path}",
        "label.startup_status_enabled": "随开机启动：已开启",
        "label.startup_status_disabled": "随开机启动：未开启",
        "label.startup_status_error": "随开机启动设置失败：{message}",
        "label.background_interval": "后台快照间隔：{minutes} 分钟",
        "label.background_interval_edit": "后台快照间隔（分钟）",
        "label.log_directory_edit": "日志目录",
        "label.log_directory_resolved": "当前实际日志目录：{path}",
        "label.enable_growth_alerts": "启用增长提醒",
        "label.alert_window_edit": "提醒窗口（分钟）",
        "label.alert_threshold_edit": "提醒阈值（MB）",
        "label.settings_saved": "设置已保存。",
        "label.settings_error_empty_log_directory": "日志目录不能为空。",
        "label.monitor_total": "当前监控规则：{count} 个",
        "label.monitor_status_stopped": "实时监听：未运行",
        "label.monitor_status_running": "实时监听：运行中，正在监听 {count} 个目录",
        "label.monitor_status_error": "实时监听启动失败：{message}",
        "label.snapshot_total": "最新快照总大小：{size}",
        "label.latest_scan": "最近快照时间：{time}",
        "label.no_scan": "还没有快照数据，请先点击“扫描一次”。",
        "label.language": "界面语言",
        "label.monitor_rules_editor": "监控规则",
        "label.rule_select_first": "请先选中一条监控规则。",
        "label.rule_error_empty_name": "第 {row} 条监控规则的名称不能为空。",
        "label.rule_error_empty_path": "第 {row} 条监控规则的路径不能为空。",
        "label.privacy_intro": (
            "Disk History 只记录元数据。\n\n"
            "详细记录：保存具体路径和大小变化。\n"
            "汇总记录：只保存规则名称和汇总信息。\n"
            "忽略：不记录该路径事件。\n\n"
            "第一版不会记录文件内容，不上传数据，也不会自动删除文件。"
        ),
        "chart.directory_rank": "目录占用排行",
        "chart.timeline": "最近 24 小时变化趋势",
        "chart.sources": "最近 24 小时增长来源",
        "chart.empty": "暂无可显示数据",
        "investigation.summary": "{window}：净变化 {delta}，对比区间 {start} 到 {end}",
        "investigation.not_enough_data": (
            "{window}：快照不足，暂时无法对比。请保持后台记录运行一段时间。"
        ),
        "window.30_minutes": "最近 30 分钟",
        "window.2_hours": "最近 2 小时",
        "window.today": "今天",
        "window.7_days": "最近 7 天",
        "chart.size_mb": "大小（MB）",
        "chart.delta_mb": "变化量（MB）",
        "chart.hour_index": "最近 24 小时",
        "notification.growth_alert.title": "Disk History 增长提醒",
        "notification.growth_alert.body": "最近 {minutes} 分钟监控目录净增长 {size}，已写入日志。",
        "table.rule": "规则",
        "table.size": "大小",
        "table.files": "文件数",
        "table.privacy": "隐私",
        "table.path_template": "路径模板",
        "table.time": "时间",
        "table.event": "事件",
        "table.delta": "变化",
        "table.category": "分类",
        "table.display_path": "显示路径",
        "table.start_size": "起始大小",
        "table.end_size": "结束大小",
        "table.window": "时间窗口",
        "table.enabled": "启用",
        "table.recursive": "递归",
        "yes": "是",
        "no": "否",
        "privacy.detailed": "详细记录",
        "privacy.summary": "汇总记录",
        "privacy.ignore": "忽略",
        "default.custom_rule_name": "自定义目录",
        "dialog.clear_title": "清空本地历史",
        "dialog.clear_body": (
            "确定要清空 SQLite 数据库里的历史记录吗？这个操作不会删除磁盘上的真实文件。"
        ),
        "dialog.choose_log_directory": "选择日志目录",
        "dialog.choose_monitor_directory": "选择监控目录",
    },
    "en": {
        "app.title": "Disk History",
        "tab.overview": "Overview",
        "tab.timeline": "Timeline",
        "tab.sources": "Sources",
        "tab.heatmap": "Activity Heatmap",
        "tab.investigation": "Investigation",
        "tab.settings": "Settings",
        "button.scan_once": "Scan Once",
        "button.refresh": "Refresh",
        "button.start_monitoring": "Start Live Monitoring",
        "button.stop_monitoring": "Stop Live Monitoring",
        "button.enable_startup": "Enable Start on Login",
        "button.disable_startup": "Disable Start on Login",
        "button.clear_history": "Clear Local History",
        "button.browse": "Browse...",
        "button.save_settings": "Save Settings",
        "button.add_rule": "Add Monitor Rule",
        "button.remove_rule": "Remove Selected Rule",
        "button.choose_rule_directory": "Choose Monitor Folder...",
        "label.product_focus": "Focus: record disk space evidence so you can analyze the cause.",
        "label.snapshot_evidence": "Snapshot Comparison Evidence",
        "label.event_evidence": "File Event Clues (Last 2 Hours)",
        "label.local_database": "Local database: {path}",
        "label.data_folder": "Data folder: {path}",
        "label.settings_file": "Settings file: {path}",
        "label.startup_status_enabled": "Start on login: enabled",
        "label.startup_status_disabled": "Start on login: disabled",
        "label.startup_status_error": "Failed to update start on login: {message}",
        "label.background_interval": "Background snapshot interval: {minutes} minutes",
        "label.background_interval_edit": "Background snapshot interval (minutes)",
        "label.log_directory_edit": "Log directory",
        "label.log_directory_resolved": "Current resolved log directory: {path}",
        "label.enable_growth_alerts": "Enable growth alerts",
        "label.alert_window_edit": "Alert window (minutes)",
        "label.alert_threshold_edit": "Alert threshold (MB)",
        "label.settings_saved": "Settings saved.",
        "label.settings_error_empty_log_directory": "Log directory cannot be empty.",
        "label.monitor_total": "Monitor rules: {count}",
        "label.monitor_status_stopped": "Live monitoring: stopped",
        "label.monitor_status_running": "Live monitoring: running, watching {count} folders",
        "label.monitor_status_error": "Failed to start live monitoring: {message}",
        "label.snapshot_total": "Latest snapshot total: {size}",
        "label.latest_scan": "Latest snapshot time: {time}",
        "label.no_scan": "No snapshot data yet. Click Scan Once first.",
        "label.language": "Interface language",
        "label.monitor_rules_editor": "Monitor Rules",
        "label.rule_select_first": "Select a monitor rule first.",
        "label.rule_error_empty_name": "Monitor rule {row} needs a name.",
        "label.rule_error_empty_path": "Monitor rule {row} needs a path.",
        "label.privacy_intro": (
            "Disk History records metadata only.\n\n"
            "Detailed mode stores concrete paths and size changes.\n"
            "Summary mode stores only rule labels and aggregate metadata.\n"
            "Ignored paths are not recorded.\n\n"
            "The first version does not record file contents, upload data, or delete files."
        ),
        "chart.directory_rank": "Directory Size Ranking",
        "chart.timeline": "Last 24 Hours Change Trend",
        "chart.sources": "Last 24 Hours Growth Sources",
        "chart.empty": "No data to display",
        "investigation.summary": "{window}: net change {delta}, comparing {start} to {end}",
        "investigation.not_enough_data": (
            "{window}: not enough snapshots to compare yet. Keep background recording running."
        ),
        "window.30_minutes": "Last 30 Minutes",
        "window.2_hours": "Last 2 Hours",
        "window.today": "Today",
        "window.7_days": "Last 7 Days",
        "chart.size_mb": "Size (MB)",
        "chart.delta_mb": "Delta (MB)",
        "chart.hour_index": "Last 24 Hours",
        "notification.growth_alert.title": "Disk History Growth Alert",
        "notification.growth_alert.body": (
            "Monitored folders grew by {size} in the last {minutes} minutes. Logs were updated."
        ),
        "table.rule": "Rule",
        "table.size": "Size",
        "table.files": "Files",
        "table.privacy": "Privacy",
        "table.path_template": "Path Template",
        "table.time": "Time",
        "table.event": "Event",
        "table.delta": "Delta",
        "table.category": "Category",
        "table.display_path": "Display Path",
        "table.start_size": "Start Size",
        "table.end_size": "End Size",
        "table.window": "Window",
        "table.enabled": "Enabled",
        "table.recursive": "Recursive",
        "yes": "Yes",
        "no": "No",
        "privacy.detailed": "Detailed",
        "privacy.summary": "Summary",
        "privacy.ignore": "Ignore",
        "default.custom_rule_name": "Custom Folder",
        "dialog.clear_title": "Clear Local History",
        "dialog.clear_body": (
            "Clear history from the SQLite database? This will not delete real files on disk."
        ),
        "dialog.choose_log_directory": "Choose Log Directory",
        "dialog.choose_monitor_directory": "Choose Monitor Folder",
    },
}


def normalize_language(language: str | None) -> str:
    if language in SUPPORTED_LANGUAGES:
        return str(language)
    return DEFAULT_LANGUAGE


def translate(language: str, key: str, **values: object) -> str:
    normalized = normalize_language(language)
    text = TRANSLATIONS[normalized].get(key, TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key))
    if values:
        return text.format(**values)
    return text


def missing_translation_keys() -> dict[str, set[str]]:
    all_keys = set().union(*(entries.keys() for entries in TRANSLATIONS.values()))
    return {
        language: all_keys - set(entries.keys())
        for language, entries in TRANSLATIONS.items()
        if all_keys - set(entries.keys())
    }
