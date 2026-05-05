# Disk History

Disk History is a local-first desktop tool for tracking disk size changes over time. It is designed to help answer questions like:

- Why did my system drive grow today?
- Which folders changed the most in the last few hours?
- Which changes are likely downloads, temporary files, development dependencies, or software updates?

The first version targets Windows and uses Python.

## Current Status

This project is in early development. The current implementation provides:

- A PySide6 desktop shell.
- SQLite storage under the current user's local app data folder.
- Default monitor rules based on portable path templates such as `{USERPROFILE}` and `{LOCALAPPDATA}`.
- One-time directory snapshot scanning.
- Basic file event recording through `watchdog`.
- Privacy modes for detailed, summary-only, and ignored paths.

## Privacy Model

Disk History is designed to run locally.

- It does not upload data.
- It does not record file contents.
- It does not automatically delete files.
- Sensitive paths can be configured to record only summary-level size changes.
- Local databases and logs are ignored by Git through `.gitignore`.

The local database may still contain file paths depending on your privacy settings. Do not upload generated `.db`, `.sqlite`, log, or export files.

## Quick Start

```powershell
cd D:\agenthome\disk-history
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m disk_history config-path
.\.venv\Scripts\python.exe -m disk_history scan
.\.venv\Scripts\python.exe -m disk_history gui
```

The `config-path` command creates and prints the local editable settings file. Monitor rules use templates like `{USERPROFILE}` and `{LOCALAPPDATA}` so the project is not tied to one person's computer.

## Development Documents

- [Development Notes](docs/DEVELOPMENT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Security](docs/SECURITY.md)
- [Roadmap](docs/ROADMAP.md)

## License

MIT
