# Development Notes

This file records the project decisions and implementation flow in plain language so a beginner can review how the project was built.

## 2026-05-06: Environment Setup

Installed or verified tools:

- Git for Windows 2.54.0
- Python 3.12.10
- GitHub CLI 2.92.0
- winget was already available and was used as the installer

Reasoning:

- Git is required for version control and GitHub publishing.
- Python 3.12 is stable, current, and beginner-friendly.
- GitHub CLI is useful for repository creation and authentication, but GitHub sync must not block local development.
- The first version uses Python instead of C++ to reduce learning pressure and speed up iteration.

## Automatic Technical Decisions

The project will use stable beginner-friendly defaults unless a future requirement forces a change.

- Desktop UI: PySide6. It gives a real Windows desktop app without requiring web server concepts.
- File watching: watchdog. It is easier to understand than NTFS USN Journal and is good enough for the first version.
- Database: SQLite through Python's standard `sqlite3` module. It is local, simple, and needs no server.
- Packaging direction: PyInstaller later, after the app can run reliably from source.
- Privacy default: configurable rules, with sensitive folders using summary-only mode by default.
- GitHub safety: generated databases, logs, exports, and local configs are ignored from the first commit.

## Project Layout

```text
disk-history/
  docs/                 Learning notes and project design
  scripts/              Helper scripts for development
  src/disk_history/     Application source code
  tests/                Automated tests
  .gitignore            Keeps private local data out of Git
  pyproject.toml        Python project configuration
  README.md             Public project overview
```

## First Implementation Scope

The first local version includes:

- Default monitor path templates instead of hardcoded personal paths.
- A generated local `settings.json` file so monitor and privacy rules are user-configurable.
- Local app data directory resolution.
- SQLite schema and repository methods.
- Directory snapshot scanning.
- Basic file event handling.
- Desktop UI with overview, timeline, rules, privacy, and data management tabs.
- Tests for path expansion, privacy behavior, database writes, and scanner behavior.

## What Is Not Implemented Yet

- Accurate process attribution.
- NTFS USN Journal integration.
- Database encryption.
- Polished installer.
- Automatic cleanup.

These are intentionally deferred. A beginner-friendly first version should be understandable and testable before adding lower-level Windows complexity.

## 2026-05-06: First Verification

Commands run successfully:

- `python -m pytest`: 9 tests passed.
- `python -m ruff check .`: all checks passed.
- `python -m disk_history init-db`: created the local SQLite database.
- `python -m disk_history config-path`: created the local settings file.
- `python -m disk_history scan`: captured a first snapshot of default monitored folders.
- `python -c "from disk_history.app import MainWindow"`: confirmed the desktop module imports correctly.

Notes:

- The local database was created under `%LOCALAPPDATA%\DiskHistory\`.
- The settings file was created under `%LOCALAPPDATA%\DiskHistory\settings.json`.
- These generated runtime files are outside the repository and are also covered by `.gitignore` patterns if copied into the repo by mistake.
- Git is installed, but the current terminal did not refresh PATH automatically. The project uses the installed Git executable directly until a new terminal session sees Git normally.
