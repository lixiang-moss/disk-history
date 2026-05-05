# Roadmap

## Version 0.1

- Project skeleton.
- Desktop UI.
- SQLite database.
- Default monitor rules.
- Directory snapshot scanning.
- Basic watchdog event recording.
- Privacy modes.
- Tests.

## Version 0.2

- Better dashboard summaries.
- Time range filters.
- Rule editing in the UI.
- Exportable reports with private paths redacted.
- Clearer cleanup suggestions without deleting files.

## Version 0.3

- Windows startup option.
- Background tray mode.
- More reliable event batching.
- Optional database encryption.

## Future C++ / Windows Module

Consider a C++ or Rust native module only after the Python version proves the product behavior.

Possible goals:

- NTFS USN Journal support.
- Better performance on large directory trees.
- More accurate low-level filesystem change tracking.

