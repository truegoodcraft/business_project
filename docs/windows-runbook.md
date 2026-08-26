# Windows Runbook: Supported BUS Core Launch

This is a launch guide, not a diagnostic procedure. Read root `AGENTS.md` and use `OPERATIONS.md` for read-only inspection.

## Normal native launch

From a prepared source environment:

```powershell
python launcher.py
```

`launcher.py` is the canonical native entry. It owns AppData directory preparation, database/app locking, runtime initialization/migrations, verified-update handoff policy, Uvicorn startup, tray lifecycle, and browser opening. Do not create repo-local data folders, point `BUS_DB` at a repo database, or invoke migration files manually as part of normal startup.

The packaged Windows executable uses the same launcher authority.

## Explicit development launch

Use development mode only when that runtime mutation is approved:

```powershell
$env:BUS_DEV = "1"
python launcher.py --dev --port 8765
```

Development mode exposes dev-only diagnostics and detailed errors. It does not bypass authentication, suppress update requests, suppress/reroute native product telemetry, or make startup read-only.

## Operational warning

Launching can acquire locks, initialize or migrate databases, seed demo state, index files, write logs/config/state, emit startup events, and start a telemetry flush. Never launch BUS Core solely to inspect Lighthouse or telemetry evidence. If the instance is not already running and runtime access was not approved, report `ACCESS_BLOCKED` instead.
