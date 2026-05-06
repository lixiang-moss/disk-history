# Disk History

Disk History 是一个本地优先的桌面工具，用来记录磁盘空间随时间发生的变化。它的目标是帮你回答这类问题：

- 今天系统盘为什么变大了？
- 最近几个小时哪些目录增长最多？
- 增长大概率来自下载、临时文件、开发依赖、软件安装，还是系统更新？

第一版以 Windows 为主要目标平台，使用 Python 开发。

## 当前状态

项目处于早期开发阶段。当前版本已经具备：

- PySide6 桌面界面，默认中文，并支持切换 English。
- SQLite 本地数据库，默认存放在当前用户的本地应用数据目录。
- 基于通用路径模板的默认监控规则，例如 `{USERPROFILE}` 和 `{LOCALAPPDATA}`，不会写死某一台电脑的个人路径。
- 单次目录快照扫描。
- 基于 `watchdog` 的基础文件变化记录。
- 详细记录、汇总记录、忽略三种隐私模式。
- 可编辑的本地配置文件。
- 目录占用排行、变化时间线、来源占比、活动热力图、清理建议等可视化视图。

## 隐私模型

Disk History 按本地工具设计。

- 不上传数据。
- 不记录文件内容。
- 不自动删除文件。
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

创建并显示本地配置文件路径。配置文件默认在 `%LOCALAPPDATA%\DiskHistory\settings.json`，用于保存监控规则、隐私模式和界面语言：

```powershell
.\.venv\Scripts\python.exe -m disk_history config-path
```

执行一次目录扫描，把默认监控目录的当前大小写入本地 SQLite 数据库：

```powershell
.\.venv\Scripts\python.exe -m disk_history scan
```

打开桌面图形界面，用图表和表格查看扫描结果、时间线、来源占比、活动热力图和清理建议：

```powershell
.\.venv\Scripts\python.exe -m disk_history gui
```

这些命令会生成本地运行数据，例如 SQLite 数据库和配置文件。它们位于 `%LOCALAPPDATA%\DiskHistory\`，不会被提交到 GitHub。

## 界面语言

桌面界面默认使用中文。可以在“设置”页切换为 English，选择后会保存到本地配置文件。

## 开发文档

- [开发记录](docs/DEVELOPMENT.md)
- [架构说明](docs/ARCHITECTURE.md)
- [安全与隐私](docs/SECURITY.md)
- [路线图](docs/ROADMAP.md)

## 许可证

本项目使用 MIT 许可证。`LICENSE` 文件保留 MIT 官方英文原文，便于 GitHub 和其他工具正确识别许可证。
