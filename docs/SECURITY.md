# Security and Privacy

Disk History should be safe by default for a personal local tool and for future open-source use.

## What The Tool Records

Depending on privacy settings, it may record:

- File or directory path metadata.
- File sizes.
- Time of change.
- Event type such as created, modified, deleted, or moved.
- Directory snapshot size.
- A human-readable category such as Downloads or Temp.

## What The Tool Does Not Record

The first version does not record:

- File contents.
- Document text.
- Image contents.
- Browser history.
- Chat contents.
- Passwords, tokens, or secrets.

## Privacy Modes

- Detailed: record the concrete path and size metadata.
- Summary: record only the configured rule label and aggregate size metadata.
- Ignore: do not record the event.

Sensitive user folders should default to summary mode.

## User Configuration

The app creates a local editable settings file:

```text
%LOCALAPPDATA%\DiskHistory\settings.json
```

Rules use path templates such as `{USERPROFILE}` instead of personal absolute paths. Users can change privacy modes without editing source code.

## GitHub Safety Rules

Never commit generated local data:

- `*.db`
- `*.sqlite`
- `*.sqlite3`
- `*.db-wal`
- `*.db-shm`
- `logs/`
- `exports/`
- local config files

These patterns are included in `.gitignore`.

## Cleanup Safety

The first version does not delete files. Future cleanup features must require explicit user confirmation.
