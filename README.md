# Disk History

Disk History 是一个本地优先的 **磁盘空间变化调查工具**。它持续记录目录大小快照和文件变化元数据，帮助你在发现磁盘突然少了几个 GB 时，回看“哪些目录在什么时间段变大了”。

它不会替你自动下结论，也不会自动清理文件。它提供的是调查线索。

## 当前状态

项目处于早期开发阶段。当前版本已经具备：

- PySide6 桌面界面，默认中文，并支持切换 English。
- SQLite 本地数据库，默认存放在当前用户的本地应用数据目录。
- 基于通用路径模板的默认监控规则，例如 `{USERPROFILE}` 和 `{LOCALAPPDATA}`。
- 手动目录快照扫描。
- GUI 中启动和停止实时文件变化监听。
- 后台记录模式，可周期性记录目录快照。
- 当前用户登录后自动启动选项，默认关闭。
- 调查视图：最近 30 分钟、2 小时、今天、7 天的目录变化对比。
- 目录占用排行、变化时间线、来源占比、活动热力图等辅助视图。
- 详细记录、汇总记录、忽略三种隐私模式。

## 隐私模型

Disk History 按本地工具设计。

- 不上传数据。
- 不记录文件内容。
- 不自动删除文件。
- 不提供清理建议功能。
- 敏感目录可以配置为只记录汇总变化，不记录具体文件名。
- 本地数据库、日志和导出文件已经通过 `.gitignore` 排除，避免误提交到 Git。

请注意：如果你把某些目录设置成详细记录，本地数据库仍可能包含文件路径。不要上传生成的 `.db`、`.sqlite`、日志或导出文件。

## 快速开始

下面这些命令适合从源码运行当前开发版。它们不会上传数据，也不会自动删除磁盘上的文件。

进入项目目录：

```powershell
cd D:\agenthome\disk-history
```

创建本项目专用的 Python 虚拟环境。这样依赖会装在项目目录下的 `.venv`，不会混进系统 Python：

```powershell
python -m venv .venv
```

安装项目运行和开发所需依赖：

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

创建并显示本地配置文件路径。配置文件默认在 `%LOCALAPPDATA%\DiskHistory\settings.json`，用于保存监控规则、隐私模式、界面语言、后台快照间隔和开机启动偏好：

```powershell
.\.venv\Scripts\python.exe -m disk_history config-path
```

执行一次目录扫描，把默认监控目录的当前大小写入本地 SQLite 数据库：

```powershell
.\.venv\Scripts\python.exe -m disk_history scan
```

打开桌面图形界面，用调查视图查看最近 30 分钟、2 小时、今天、7 天的目录变化：

```powershell
.\.venv\Scripts\python.exe -m disk_history gui
```

运行后台记录模式。它会启动实时监听，并按配置间隔记录目录快照：

```powershell
.\.venv\Scripts\python.exe -m disk_history background
```

打开 GUI 后，可以点击“开始实时监听”。实时监听只记录文件变化元数据，不读取文件内容，也不会删除文件。需要暂停时点击“停止实时监听”。

如果希望登录 Windows 后自动记录，可以在“设置”页开启“随开机启动”。第一版只为当前用户创建启动项，不安装系统服务，也不要求管理员权限。

这些命令会生成本地运行数据，例如 SQLite 数据库和配置文件。它们位于 `%LOCALAPPDATA%\DiskHistory\`，不会被提交到 GitHub。

## 界面语言

桌面界面默认使用中文。可以在“设置”页切换为 English，选择后会保存到本地配置文件。

## 开发文档

- [产品需求说明](docs/PRODUCT_REQUIREMENTS.md)
- [开发记录](docs/DEVELOPMENT.md)
- [架构说明](docs/ARCHITECTURE.md)
- [安全与隐私](docs/SECURITY.md)
- [路线图](docs/ROADMAP.md)

## 许可证

本项目使用 MIT 许可证。`LICENSE` 文件保留 MIT 官方英文原文，便于 GitHub 和其他工具正确识别许可证。
