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
        "tab.cleanup": "清理建议",
        "tab.settings": "设置",
        "button.scan_once": "扫描一次",
        "button.refresh": "刷新",
        "button.start_monitoring": "开始实时监听",
        "button.stop_monitoring": "停止实时监听",
        "button.clear_history": "清空本地历史",
        "label.local_database": "本地数据库：{path}",
        "label.data_folder": "数据目录：{path}",
        "label.settings_file": "配置文件：{path}",
        "label.monitor_total": "当前监控规则：{count} 个",
        "label.monitor_status_stopped": "实时监听：未运行",
        "label.monitor_status_running": "实时监听：运行中，正在监听 {count} 个目录",
        "label.monitor_status_error": "实时监听启动失败：{message}",
        "label.snapshot_total": "最新快照总大小：{size}",
        "label.latest_scan": "最近快照时间：{time}",
        "label.no_scan": "还没有快照数据，请先点击“扫描一次”。",
        "label.language": "界面语言",
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
        "chart.size_mb": "大小（MB）",
        "chart.delta_mb": "变化量（MB）",
        "chart.hour_index": "最近 24 小时",
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
        "table.enabled": "启用",
        "table.recursive": "递归",
        "table.risk": "风险",
        "table.target": "对象",
        "table.suggestion": "建议",
        "yes": "是",
        "no": "否",
        "risk.safe": "可安全检查",
        "risk.caution": "谨慎处理",
        "risk.protected": "不建议手动清理",
        "cleanup.downloads": "检查是否有不再需要的安装包、压缩包或大文件。",
        "cleanup.temp": "通常可以通过系统清理工具处理，不建议在程序内自动删除。",
        "cleanup.package_cache": "可能是安装器缓存，清理前确认不会影响修复或卸载软件。",
        "cleanup.windows_update": "优先使用 Windows 自带磁盘清理，不建议手动删除。",
        "cleanup.dev_tools": "可能包含开发工具或扩展，确认不用后再删除。",
        "cleanup.local_programs": "这里通常是已安装软件，不建议直接手动删除。",
        "cleanup.personal": "这里可能包含个人文件，只做空间提醒，不给删除建议。",
        "dialog.clear_title": "清空本地历史",
        "dialog.clear_body": "确定要清空 SQLite 数据库里的历史记录吗？这个操作不会删除磁盘上的真实文件。",
    },
    "en": {
        "app.title": "Disk History",
        "tab.overview": "Overview",
        "tab.timeline": "Timeline",
        "tab.sources": "Sources",
        "tab.heatmap": "Activity Heatmap",
        "tab.cleanup": "Cleanup Advice",
        "tab.settings": "Settings",
        "button.scan_once": "Scan Once",
        "button.refresh": "Refresh",
        "button.start_monitoring": "Start Live Monitoring",
        "button.stop_monitoring": "Stop Live Monitoring",
        "button.clear_history": "Clear Local History",
        "label.local_database": "Local database: {path}",
        "label.data_folder": "Data folder: {path}",
        "label.settings_file": "Settings file: {path}",
        "label.monitor_total": "Monitor rules: {count}",
        "label.monitor_status_stopped": "Live monitoring: stopped",
        "label.monitor_status_running": "Live monitoring: running, watching {count} folders",
        "label.monitor_status_error": "Failed to start live monitoring: {message}",
        "label.snapshot_total": "Latest snapshot total: {size}",
        "label.latest_scan": "Latest snapshot time: {time}",
        "label.no_scan": "No snapshot data yet. Click Scan Once first.",
        "label.language": "Interface language",
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
        "chart.size_mb": "Size (MB)",
        "chart.delta_mb": "Delta (MB)",
        "chart.hour_index": "Last 24 Hours",
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
        "table.enabled": "Enabled",
        "table.recursive": "Recursive",
        "table.risk": "Risk",
        "table.target": "Target",
        "table.suggestion": "Suggestion",
        "yes": "Yes",
        "no": "No",
        "risk.safe": "Safe to review",
        "risk.caution": "Handle carefully",
        "risk.protected": "Do not manually clean",
        "cleanup.downloads": "Review installers, archives, or large files you no longer need.",
        "cleanup.temp": "Prefer system cleanup tools. The app should not delete these automatically.",
        "cleanup.package_cache": "Installer cache may help repair or uninstall apps. Verify before cleaning.",
        "cleanup.windows_update": "Use Windows Disk Cleanup first. Avoid manual deletion.",
        "cleanup.dev_tools": "May contain tools or extensions. Remove only after confirming they are unused.",
        "cleanup.local_programs": "Usually contains installed apps. Do not delete directly.",
        "cleanup.personal": "May contain personal files. This is only a space reminder.",
        "dialog.clear_title": "Clear Local History",
        "dialog.clear_body": (
            "Clear history from the SQLite database? This will not delete real files on disk."
        ),
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
