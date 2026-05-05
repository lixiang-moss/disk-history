# Architecture

Disk History is split into small modules so each part is easy to understand.

## Main Flow

```text
Monitor rules
  -> path template expansion
  -> privacy classification
  -> file watcher events and directory snapshots
  -> SQLite database
  -> desktop UI and CLI queries
```

## Modules

- `config.py`: default monitor rules, privacy rules, and app data paths.
- `privacy.py`: decides whether a path is detailed, summary-only, or ignored.
- `database.py`: creates and writes the SQLite database.
- `scanner.py`: calculates directory sizes for snapshot history.
- `settings.py`: creates and reads the local editable settings file.
- `watcher.py`: records live filesystem events through watchdog.
- `app.py`: PySide6 desktop interface.
- `cli.py`: command-line entry points for scanning, watching, and opening the UI.

## Data Storage

Runtime data is stored outside the repository:

```text
%LOCALAPPDATA%\DiskHistory\
```

The default database path is:

```text
%LOCALAPPDATA%\DiskHistory\disk_history.sqlite3
```

This database is local user data and must not be committed to Git.

The default settings path is:

```text
%LOCALAPPDATA%\DiskHistory\settings.json
```

This file stores path templates and privacy modes. It should remain local because users may customize it.
