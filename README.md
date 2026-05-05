# Disk History

Disk History 是一个本地优先的桌面工具，用来记录磁盘空间随时间发生的变化。它的目标是帮你回答这类问题：

- 今天系统盘为什么变大了？
- 最近几个小时哪些目录增长最多？
- 增长大概率来自下载、临时文件、开发依赖、软件安装，还是系统更新？

第一版以 Windows 为主要目标平台，使用 Python 开发。

## 当前状态

项目处于早期开发阶段。当前版本已经具备：

- PySide6 桌面界面骨架。
- SQLite 本地数据库，默认存放在当前用户的本地应用数据目录。
- 基于通用路径模板的默认监控规则，例如 `{USERPROFILE}` 和 `{LOCALAPPDATA}`，不会写死某一台电脑的个人路径。
- 单次目录快照扫描。
- 基于 `watchdog` 的基础文件变化记录。
- 详细记录、汇总记录、忽略三种隐私模式。
- 可编辑的本地配置文件。

## 隐私模型

Disk History 按本地工具设计。

- 不上传数据。
- 不记录文件内容。
- 不自动删除文件。
- 敏感目录可以配置为只记录汇总变化，不记录具体文件名。
- 本地数据库、日志和导出文件已经通过 `.gitignore` 排除，避免误提交到 Git。

请注意：如果你把某些目录设置成详细记录，本地数据库仍可能包含文件路径。不要上传生成的 `.db`、`.sqlite`、日志或导出文件。

## 快速开始

```powershell
cd D:\agenthome\disk-history
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m disk_history config-path
.\.venv\Scripts\python.exe -m disk_history scan
.\.venv\Scripts\python.exe -m disk_history gui
```

`config-path` 命令会创建并显示本地可编辑配置文件。监控规则使用 `{USERPROFILE}`、`{LOCALAPPDATA}` 这类路径模板，因此项目不会绑定到某个用户的电脑路径。

## 开发文档

- [开发记录](docs/DEVELOPMENT.md)
- [架构说明](docs/ARCHITECTURE.md)
- [安全与隐私](docs/SECURITY.md)
- [路线图](docs/ROADMAP.md)

## 许可证

本项目使用 MIT 许可证。`LICENSE` 文件保留 MIT 官方英文原文，便于 GitHub 和其他工具正确识别许可证。

