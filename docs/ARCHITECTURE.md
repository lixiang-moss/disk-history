# 架构说明

## 2026-05-09 架构补充：三层监控模型

当前架构把监控分成三层：

- 普通实时监控：`watcher.py` 使用 `watchdog` 记录普通目录的文件事件；`scanner.py` 同时定期生成盘容量快照和最多 4 层目录树快照。
- 噪音目录间隔监控：噪音规则由 `settings.py` 保存，`watcher.py` 在实时事件阶段过滤这些目录，`scanner.py` 使用 `noise_snapshot_only` 策略记录短间隔大小快照。
- 重点监控名单：用户手动添加目标后，`watcher.py` 继续实时记录该目录事件并标记为 `focus`，`scanner.py` 生成更深层快照，`focus_log.py` 写入独立日志。

新增数据表职责：

- `drive_snapshots`：记录盘符、总容量、已用空间和可用空间。
- `tree_snapshots`：记录普通目录树和噪音目录的大小快照，包含深度和策略。
- `focus_snapshots`：记录重点监控目标的深层快照。
- `file_events.source_strategy`：区分普通实时事件和重点监控事件。
- `growth_alerts`：预留快速增长提醒的结构化入库空间，当前主要提醒仍写入按日日志。

新的数据流：

```text
普通目录
  -> watcher.py 实时事件
  -> file_events(source_strategy=standard)
  -> scanner.py 4 层目录树快照
  -> tree_snapshots(strategy=standard)

噪音目录
  -> watcher.py 过滤实时事件
  -> scanner.py 3 分钟间隔快照
  -> tree_snapshots(strategy=noise_snapshot_only)

重点监控目录
  -> watcher.py 实时事件
  -> file_events(source_strategy=focus)
  -> scanner.py 8 层快照
  -> focus_snapshots
  -> focus_log.py 独立日志
```

## 后期架构备忘：自适应策略引擎

后期如果实现自适应噪音目录识别，可以新增一个独立模块，例如 `adaptive_policy.py`。它不应直接写文件事件，也不应直接修改监听器状态，而是读取 `file_events`、`tree_snapshots` 和 `growth_alerts`，生成“策略建议”。

建议的数据流：

```text
file_events + tree_snapshots + growth_alerts
  -> adaptive_policy.py 计算目录稳定性指标
  -> adaptive_policy_suggestions 表
  -> GUI 展示建议和解释
  -> 用户确认后写入 noise_rules 或动态扫描配置
```

建议指标：

- `event_count`：观察窗口内事件数量。
- `snapshot_count`：观察窗口内快照数量。
- `net_growth_bytes`：窗口起点到终点的净增长。
- `absolute_churn_bytes`：所有相邻快照变化量的绝对值之和。
- `peak_to_peak_bytes`：窗口内最大占用和最小占用的差。
- `max_single_growth_bytes`：相邻两次快照之间的最大正增长。
- `stability_ratio`：`abs(net_growth_bytes) / max(absolute_churn_bytes, 1)`。

基本判定可以是：事件数量超过阈值，但净增长、峰谷差、最大单次增长都低于阈值，并且最近没有增长提醒，则认为它是“高频低增长候选”。候选目录需要经过冷却期，避免一次短期平稳就被降级。

Disk History 被拆分成多个小模块，方便新手理解每一部分的职责。

## 主流程

```text
监控规则
  -> 路径模板展开
  -> 隐私规则判断
  -> 目录快照和文件事件
  -> SQLite 本地数据库
  -> 快照对比和辅助事件聚合
  -> 桌面界面和命令行查询
```

## 模块职责

- `config.py`：默认监控规则、默认忽略规则、应用数据目录和路径模板展开。
- `privacy.py`：判断某个路径应该详细记录、汇总记录，还是完全忽略。
- `database.py`：创建 SQLite 表结构，并负责写入和读取历史数据。
- `scanner.py`：计算目录大小，用于生成目录快照。
- `analytics.py`：把目录快照对比成调查窗口，并聚合辅助图表数据。
- `activity_log.py`：把快照、文件事件和提醒写成按日分类的 Markdown 与 JSONL 日志。
- `i18n.py`：集中管理界面中英文文本，避免文字散落在界面代码里。
- `paths.py`：提供路径包含关系判断，用于实现日志目录排除。
- `settings.py`：创建和读取本地可编辑配置文件。
- `watcher.py`：通过 `watchdog` 监听实时文件变化。
- `background.py`：后台周期性记录目录快照，并启动实时监听。
- `notifications.py`：用 PySide6 的系统托盘能力发出增长提醒；如果系统不支持通知，日志写入仍然继续。
- `reports.py`：生成 Markdown 调查报告，并负责常见私人路径隐藏。
- `startup.py`：管理当前用户登录后自动启动的快捷方式。
- `app.py`：PySide6 桌面界面。
- `cli.py`：命令行入口，用于扫描、监听、后台记录、打开界面等操作。

## 数据存放位置

运行时数据不放在项目源码目录，而是放在当前用户的本地应用数据目录：

```text
%LOCALAPPDATA%\DiskHistory\
```

默认数据库路径：

```text
%LOCALAPPDATA%\DiskHistory\disk_history.sqlite3
```

这个数据库属于本地隐私数据，不能提交到 Git。

默认配置文件路径：

```text
%LOCALAPPDATA%\DiskHistory\settings.json
```

这个文件保存监控路径模板、隐私模式、界面语言、后台快照间隔和开机启动偏好。

```json
{
  "language": "zh-CN",
  "start_on_login": false,
  "background_snapshot_interval_minutes": 10,
  "log_directory": "{LOCALAPPDATA}\\DiskHistory\\logs",
  "enable_growth_alerts": true,
  "alert_window_minutes": 30,
  "alert_growth_threshold_mb": 5120
}
```

默认日志目录：

```text
%LOCALAPPDATA%\DiskHistory\logs\
```

日志按日期分目录保存：

```text
logs\2026-05-08\summary.md
logs\2026-05-08\snapshots.jsonl
logs\2026-05-08\events.jsonl
logs\2026-05-08\alerts.jsonl
```

## 核心证据模型

Disk History 以目录快照作为主要证据，以文件事件作为辅助线索。

- 目录快照回答“哪个目录在某个时间范围内变大或变小了”。
- 文件事件回答“同一时间范围内有哪些文件发生过变化”。
- 工具不承诺自动判断根因，用户根据这些记录自行分析。

## 日志与提醒数据流

```text
后台或手动扫描
  -> capture_snapshots()
  -> SQLite directory_snapshots
  -> activity_log.py 写入 snapshots.jsonl 和 summary.md
  -> analytics.py 对比提醒窗口内的快照
  -> 超过阈值时写入 alerts.jsonl
  -> notifications.py 尝试显示系统托盘提醒
```

日志目录会被传入 `scanner.py` 和 `watcher.py` 的排除列表：

- 扫描父目录时，日志目录及其子目录不参与大小统计。
- 监听父目录时，日志目录内的文件事件会被忽略。
- 如果用户把日志目录本身加入监控规则，监听目标会被跳过，不会报错退出。

这样可以避免“工具写日志 -> 监听到日志变化 -> 再写日志”的循环。

GUI 设置页会直接修改 `settings.json` 中的监控规则、日志与提醒配置。保存时只更新配置文件，不修改历史数据库。若保存设置时实时监听正在运行，界面会先停止监听，再用新配置重新启动监听，使新的监控规则和日志目录排除规则立即生效。

## 可视化层

界面使用 PySide6 自带的 QtCharts 展示图表，不额外引入复杂绘图库。

当前可视化包括：

- 调查视图：对比最近 30 分钟、2 小时、今天、7 天和用户自定义时间范围的目录净变化。
- 目录占用排行：从最新目录快照计算。
- 变化时间线：从最近文件事件按小时聚合。
- 来源占比：按分类汇总最近 24 小时的增长量，作为辅助线索。
- 活动热力图：按日期和小时展示变化活跃度。
- 目录钻取：对选中的监控目录做一次即时子项扫描，展示下一层子目录和文件的当前大小排行。
- 调查报告导出：把当前调查时间范围、目录变化和文件事件线索写成 Markdown。

## 实时监听

GUI 里的实时监听使用 `watcher.py` 中的 `DiskHistoryWatcher` 控制。

- 启动监听时，根据当前监控规则找出真实存在且启用的目录。
- `watchdog` 在后台线程里接收文件事件。
- GUI 主线程不直接处理文件事件，只通过定时器刷新数据库中的结果。
- SQLite 连接使用线程锁保护，避免后台写入和界面读取同时发生时互相干扰。

这种设计把“文件监听”“数据库写入”“界面刷新”分开，后续更容易调试。

## 后台记录和开机启动

后台记录模式通过 `python -m disk_history background` 启动。

- 启动后先开启实时监听。
- 按配置间隔记录目录快照，默认 10 分钟。
- 开机启动通过当前用户启动文件夹中的快捷方式实现。
- 第一版不安装 Windows 服务，不写系统级注册表，不要求管理员权限。
- GUI 中的“记录程序启动方式”只是对同一机制的明确表达：选择自动模式会创建该快捷方式，选择手动模式会删除该快捷方式。
- 在 Windows 上，如果同目录存在 `pythonw.exe`，启动项会优先使用它运行后台记录，以避免登录时出现额外控制台窗口。
- 后台模式会创建系统托盘图标。托盘右键菜单提供“退出 Disk History”，点击后向 `BackgroundRecorder` 发出停止请求。
- 后台循环在两次采样之间会短间隔处理 Qt 事件，避免托盘菜单因为没有事件循环而无法响应。

## 第一版技术取舍

- 使用 Python 是为了降低入门难度，并让功能更快跑通。
- 使用 `watchdog` 是为了先实现可理解、可测试的文件变化监听。
- 使用 SQLite 是因为它不需要单独安装数据库服务，适合本地桌面工具。
- 使用 QtCharts 是因为它随 PySide6 一起工作，第一版不用额外学习前端图表生态。
- 暂不使用 C++ 或 NTFS USN Journal，避免第一版过早进入复杂的 Windows 底层开发。
## 0.3 可用性补强数据流

0.3 阶段把“盘符 + 目录树 + 实时事件 + 重点监控”的模型进一步拆清楚：

```text
settings.json
  -> 普通监控规则 monitor_rules
  -> 噪音目录规则 noise_rules
  -> 重点监控名单 focus_targets

scanner.py
  -> drive_snapshots：记录 C:、D: 等盘符整体容量
  -> tree_snapshots：记录普通目录最多 4 层目录树
  -> focus_snapshots：记录重点监控目录更深层快照

watcher.py / background.py
  -> file_events：普通实时事件
  -> focus_events：重点监控事件
  -> growth_alerts：快速增长提醒

trends.py
  -> 盘符趋势
  -> 目录趋势
  -> 最近目录增长线索

app.py
  -> 磁盘页、目录树页、实时事件页、噪音目录页、重点监控页、快速增长页
```

新增模块职责：

- `focus_targets.py`：负责重点监控目标的默认值补齐、启用/暂停/过期判断、剩余时间显示和后台监听根目录过滤。
- `trends.py`：负责把 SQLite 中的盘符快照和目录树快照整理成 GUI 图表可直接使用的数据点。
- `growth_alerts` 数据表：保存短时间增长超过阈值的记录，供 GUI 和后续报告功能读取。

设计取舍：

- 重点监控目标默认 24 小时后过期，是为了避免用户临时调查目录后忘记关闭，导致长期高负载。
- 噪音目录仍然不写实时事件，因为这类目录的单个事件通常没有分析价值，真正重要的是一段时间内净增长是否异常。
- 趋势图第一版用快照序号作为横轴，不直接使用时间轴。这样实现简单、稳定，后续可以再升级成真正的时间坐标和缩放交互。
