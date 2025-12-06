# Windows Runbook: BUS Core Startup

Use these commands to bootstrap and launch the BUS Core application on Windows.

```powershell
# Ensure folders exist
New-Item -ItemType Directory -Force -Path data | Out-Null
New-Item -ItemType Directory -Force -Path data\journals | Out-Null

# Point DB to absolute path (avoids CWD surprises)
$env:BUS_DB = (Resolve-Path .\data\app.db).Path

# Apply migration
python core/appdb/migrations/2025_11_30_int_measurements.py

# Launch (adjust module/path if different in repo)
uvicorn core.api.http:create_app --factory --host 127.0.0.1 --port 8765
```
