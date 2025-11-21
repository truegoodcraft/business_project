# TGC BUS Core (Business Utility System Core)

- Local-first FastAPI + SQLite app (single-machine), no telemetry.
- UI served from `/ui/shell.html` (hash routing).
- Modular `/app/**` domain APIs (vendors, items, contacts, etc.).

**Status:** Not specified in the SoT you’ve given me.  
**Requirements:** Windows path rules are canonical; Python version not specified in the SoT you’ve given me.

## Quickstart (dev, Windows PowerShell)

```powershell
git clone https://github.com/truegoodcraft/TGC-BUS-Core.git
cd TGC-BUS-Core
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev_bootstrap.ps1
# then open http://127.0.0.1:8765/ui/shell.html (script auto-opens)
```

The bootstrap script also guarantees a default community license at `%LOCALAPPDATA%\BUSCore\license.json` if one is missing.

**Tip:** Mint a session token with **GET** (not POST):

```powershell
$BASE = "http://127.0.0.1:8765"
$tok = (Invoke-RestMethod -Uri "$BASE/session/token").token
```


**SoT (developer workflow & licensing) last synced:** 2025-11-18.

**Owner:** True Good Craft
**License:** GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later)

## What is this?

TGC BUS Core (“BUS” = **Business Utility System**) is a local-first operations core for tiny shops, makers, and small businesses.

- Single-machine, offline-capable
- No telemetry
- SQLite + journals, not a cloud SaaS
- Designed to be extended with plugins (including future PRO plugins)

Right now this is an **alpha** aimed at developers and power users, not yet a polished end-user product.

## Status

- **Backend:** Working alpha
  - Items, vendors, tasks
  - Transactions (money in/out)
  - RFQ generator
  - Inventory runs with journaling
  - Encrypted export/import
- **UI:** Rough / work-in-progress
  - Home dashboard  (donuts + last 10)
  - Inventory & vendors screens
  - Settings (writes toggle, business profile)
- **Not ready** for general non-technical users yet.

## Core principles

- Local-first, offline-capable
- No telemetry, no phone-home
- No forced cloud service
- Data is exportable and migratable (no lock-in)
- Clear separation between:
  - **Free core** (AGPL)
  - **Optional PRO plugins** (separate commercial license)

## Two-window dev flow

> **⚠️ Development & smoke testing use the uvicorn commands shown below.** `launcher.py` is not used for the dev flow.

Run two PowerShell windows exactly as shown.

**Window A (server):**

```powershell
# 1) Go to the project folder
cd "C:\path\to\TGC-BUS-Core"

# 2) Install deps (uses your global Python)
python -m pip install -r requirements.txt

# 3) Make sure the app can import the repo modules
$env:PYTHONPATH = (Get-Location).Path

# 4) Guarantee a default license for dev
$lic = Join-Path $env:LOCALAPPDATA 'BUSCore\license.json'
if (!(Test-Path $lic)) {
  New-Item -ItemType Directory -Force -Path (Split-Path $lic) | Out-Null
  '{"tier":"community","features":{},"plugins":{}}' | Set-Content -Path $lic
}

# 5) (Optional) Point UI path if your app expects it
$env:BUS_UI_DIR = (Join-Path (Get-Location) 'core\ui')

# 6) Run the server
python -m uvicorn core.api.http:create_app --host 127.0.0.1 --port 8765 --reload
```

**Window B (smoke):**

```powershell
# 1) Go to the project folder
cd "C:\path\to\TGC-BUS-Core"

# 2) Wait for the server to be up
$u = 'http://127.0.0.1:8765/session/token'
$max = 30
for ($i=0; $i -lt $max; $i++) {
  try { Invoke-WebRequest -UseBasicParsing $u -TimeoutSec 2 | Out-Null; break } catch { Start-Sleep -Seconds 1 }
}

# 3) Run smoke
powershell -NoProfile -ExecutionPolicy Bypass -File ".\buscore-smoke.ps1"
```

### Run smoke

`buscore-smoke.ps1` is the canonical SoT harness. Smoke must be **100% green** for a change to be accepted. The Window A script above creates the required `%LOCALAPPDATA%\BUSCore\license.json` if it is missing.

### Health & UI

- Public `GET /health` returns `{"ok": true}` (200).
- Protected `GET /health` (with `X-Session-Token`) returns 200 with `version`, `policy`, `license`, and `run-id`.
- `GET /ui/shell.html` must return HTTP 200 with content.

## Project structure (high level)

* `core/` – backend application (FastAPI, domain logic, RFQ, inventory, export/import, etc.)
* `core/ui/` – front-end (HTML/JS/CSS, cards, dashboard)
* `launcher/` – helper scripts / launchers
* `docs/`

  * `SOT.md` – Source of Truth (design, rules, constraints)
  * `ARCHITECTURE.md` – architecture overview
  * `ROADMAP.md` – versioned roadmap and scope

## Contributing

Right now, help is especially welcome on:

* UI cleanup and consistency (Home, Inventory, Vendors, RFQ, Settings)
* User flows and error handling
* Tests for key backend flows

Basic expectations:

* Respect the local-first, no-telemetry constraints.
* Don’t introduce background schedulers / hidden network calls.
* Keep changes small and focused; open issues/PRs for discussion.

## License

The core of this project is licensed under the **GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later)**.

See the `LICENSE` file for full details.

Optional PRO plugins and commercial add-ons may be offered under a separate license by True Good Craft.
