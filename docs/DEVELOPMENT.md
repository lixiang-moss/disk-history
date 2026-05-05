# 开发记录

这个文件用尽量直白的中文记录项目决策和开发过程，方便没有开发基础的用户事后复盘。

## 2026-05-06：环境准备

已安装或确认可用的工具：

- Git for Windows 2.54.0
- Python 3.12.10
- GitHub CLI 2.92.0
- `winget` 已存在，并用于安装官方软件包

选择理由：

- Git 用于版本控制和上传 GitHub。
- Python 3.12 稳定、较新，也适合新手学习。
- GitHub CLI 方便创建仓库、认证和推送代码，但 GitHub 同步不能阻塞本地开发。
- 第一版先用 Python，不直接上 C++，可以降低挫败感，也方便快速验证产品逻辑。

## 自动技术决策

项目默认采用稳健、适合新手理解的方案。除非未来需求明确要求改变，否则不为了炫技增加复杂度。

- 桌面界面：PySide6。它能做真正的 Windows 桌面应用，同时不需要先理解 Web 服务。
- 文件监听：`watchdog`。它比 NTFS USN Journal 更容易理解，足够支撑第一版。
- 数据库：Python 标准库里的 `sqlite3`。本地、简单、不需要额外数据库服务。
- 打包方向：后续使用 PyInstaller。等源码运行稳定后再做安装包。
- 隐私默认策略：监控和隐私规则可配置，敏感目录默认使用汇总记录。
- GitHub 安全策略：从第一次提交开始就忽略数据库、日志、导出文件和本地配置。

## 项目目录

```text
disk-history/
  docs/                 学习记录和项目设计文档
  scripts/              开发辅助脚本
  src/disk_history/     应用源码
  tests/                自动化测试
  .gitignore            防止本地隐私数据进入 Git
  pyproject.toml        Python 项目配置
  README.md             项目公开说明
```

## 第一版实现范围

第一版本地版本包含：

- 使用通用路径模板的默认监控规则，不写死个人绝对路径。
- 自动生成本地 `settings.json`，让监控规则和隐私规则可以配置。
- 本地应用数据目录解析。
- SQLite 表结构和读写方法。
- 目录快照扫描。
- 基础文件事件处理。
- 包含总览、时间线、监控规则、隐私、数据管理的桌面界面。
- 覆盖路径展开、隐私规则、数据库写入和目录扫描的测试。

## 暂不实现的内容

- 准确识别导致变化的进程。
- NTFS USN Journal 集成。
- 数据库加密。
- 完整安装包。
- 自动清理文件。

这些功能先延后处理。对新手友好的第一版应该先做到结构清楚、可以运行、可以测试，再逐步加入底层 Windows 能力。

## 2026-05-06：第一次验证

已经成功运行的检查：

- `python -m pytest`：9 个测试通过。
- `python -m ruff check .`：代码检查通过。
- `python -m disk_history init-db`：创建本地 SQLite 数据库。
- `python -m disk_history config-path`：创建本地配置文件。
- `python -m disk_history scan`：完成一次默认监控目录快照。
- `python -c "from disk_history.app import MainWindow"`：确认桌面模块可以正常导入。

说明：

- 本地数据库创建在 `%LOCALAPPDATA%\DiskHistory\`。
- 本地配置文件创建在 `%LOCALAPPDATA%\DiskHistory\settings.json`。
- 这些运行时文件不在项目仓库里。即使被误复制进仓库，也会被 `.gitignore` 的规则排除。
- Git 已安装，但旧终端可能不会立即刷新 PATH。重新打开终端后通常会正常识别。

## 2026-05-06：GitHub 同步状态

本地 Git 工作已完成：

- 初始化仓库，默认分支为 `main`。
- 配置本地 Git 作者为 `lixiang-moss`。
- 创建第一次提交：`Initial disk history project`。

第一次尝试 GitHub 同步时失败，原因是这台电脑上的 GitHub CLI 尚未登录：

```text
gh auth status
You are not logged into any GitHub hosts.
```

用户完成 GitHub CLI 授权后，已创建公开仓库：

```text
https://github.com/lixiang-moss/disk-history
```

仓库使用 `main` 作为默认分支，远程名为 `origin`。

## 2026-05-06：文档语言规范

用户要求项目文档统一使用中文。因此从这一版开始：

- `README.md` 使用中文。
- `docs/` 目录下的项目说明文档使用中文。
- 面向用户学习和维护的说明优先按中文母语者的表达方式编写。
- 标准 MIT `LICENSE` 保留英文原文，避免法律文本翻译造成歧义，也便于 GitHub 正确识别许可证。

