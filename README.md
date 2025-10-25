# 🤖 TGC Alpha Core

**Version: v.a0.01.3**

> A small, opinionated controller that boots, checks connections, shows status — and only digs deeper when you ask.

---

## What It Is

**TGC Alpha Core** is a lean automation hub. On start it loads plugins, performs base-layer probes via a scoped connection broker, and prints a clear status report. No crawling or writes by default.

---

## Pluggable Broker

Alpha Core now ships with a pluggable connection broker. The core stays integration-agnostic:

* Plugins live in `plugins/` and subclass `core.contracts.plugin_v2.PluginV2`.
* Each plugin calls `broker.register(...)` to provide services and probes.
* Core only knows about the services the plugins register and remains silent until they show up.

Google Drive, Sheets, Notion, and any other integrations live entirely in plugins under `plugins/`. Drop in a plugin package and restart the core to make the service available.

---

## Alpha Core (HTTP) — v.a0.01.3

Install deps:

```
python -m pip install -r requirements.txt
python -m pip install fastapi uvicorn[standard] pydantic
```

Start server:

```
python app.py serve
# or: python app.py alpha --serve
```

Auth:

```
$token = Get-Content .\data\session_token.txt
irm http://127.0.0.1:8765/health  -Headers @{ 'X-Session-Token'=$token }
irm http://127.0.0.1:8765/plugins -Headers @{ 'X-Session-Token'=$token }
irm http://127.0.0.1:8765/probe   -Method Post -Headers @{ 'X-Session-Token'=$token } -ContentType application/json -Body "{}"
```

## Packaged Dev App (TGC Controller)

Build the development-friendly ONEDIR bundle (PowerShell):

```
py -3.11 -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

pyinstaller launcher.py ^
  --name "TGC Controller" ^
  --noconsole ^
  --onedir ^
  --add-data "core/ui;core/ui" ^
  --add-data "docs/LICENSE;." ^
  --hidden-import uvicorn ^
  --hidden-import fastapi
```

Launch the packaged controller:

```
.\\dist\\TGC-Controller\\TGC Controller.exe
```

On startup it will:

* create (or reuse) `data\\` and `logs\\` beside the executable and save the current session token to `data\\session_token.txt`.
* print the token path and the resolved UI directory (`core\\ui`) so you can see where files are being served from.
* wait for the core to report healthy and open `http://127.0.0.1:8765/ui` (or the fallback port if 8765 is busy).

Live UI editing while the app runs:

* Edit the static assets under `.\\dist\\TGC-Controller\\core\\ui\\` (for example `index.html`, `app.js`, or `styles.css`).
* Refresh the browser tab — changes are served immediately because the ONEDIR layout keeps those files on disk.

To stop the app, close the window or press `Ctrl+C` in the console; the embedded uvicorn server will shut down cleanly.

Plugins:

* Put plugins under `plugins/<your_plugin>/plugin.py`
* Implement `Plugin(PluginV2)` with `describe()` and `register_broker()`
* Core remains silent until a plugin declares services.

## Capability Registry & System Manifest

- Core validates capabilities and writes a signed manifest:
  - Windows: `%LOCALAPPDATA%\TGC\state\system_manifest.json`
  - macOS/Linux: `~/.tgc/state/system_manifest.json`
- Endpoints:
  - `GET /capabilities`
  - `GET /capabilities/stream`  (SSE events: `CAPABILITY_UPDATE`)
- Plugins declare capabilities via `PluginV2.capabilities()`:
  - `provides`: `["namespace.capability"]`
  - `requires`: `["other.capability"]`
- Core is the only writer. No secrets in the manifest. HMAC-SHA256 signature prevents tampering.

---

## Safety & Transparency

* 🔒 **Scoped clients**: `read_base`, `read_crawl`, `write`
* 🚫 **No scope escalation**: a plugin can’t jump from read → write during a run
* 🧪 **Probe-only boot**: the default path is read-only
* 🧾 **Clear run logs**: every request logged under `logs/`

---

## Developing Plugins

```python
from core.contracts.plugin_v2 import PluginV2

class Plugin(PluginV2):
    id = "my_plugin"
    name = "My Provider"

    def register_broker(self, broker):
        broker.register("myservice", provider=my_provider_fn, probe=my_probe_fn)
```

* `describe()` advertises services/scopes.
* `register_broker()` wires providers and probes into the broker.
* Optional `run()` hooks remain available for long-running work.

Drop your plugin under `plugins/<name>/` and restart the core. Core discovers packages automatically and keeps Google/Notion details outside of the main runtime.

### Notion (read-only) v0.01.0
Set env:
- NOTION_TOKEN (required)
- NOTION_ROOT_PAGE_IDS (optional CSV)
- NOTION_API_VERSION (optional; default 2022-06-28)

Plugin is hidden until configured. Probe calls GET /v1/users/me (2s timeout).
Provides capability: notion.pages.read (read-only).

## Public API Contract (for plugins)

Plugins may only import:
- `core.contracts.plugin_v2`          (plugin base class & interface)
- `core.services.conn_broker`         (broker types & client handle; re-exported via `core.conn_broker`)
- `core.capabilities`                 (facade: publish/resolve/list_caps/emit_manifest/meta)

Plugins that import any other `core.*` modules are rejected at load time by the import guard.
Core internals live under `core/_internal/*` and are private.
HTTP endpoints are stable; do not rely on undocumented fields.

---

## Commands

* `python app.py alpha` → boot + probe + status
* `python app.py alpha --crawl` → perform full index/crawl (respects limits)
* `python app.py serve` → start the HTTP server on `127.0.0.1:8765`

---

### Continuous Integration (CI)
CI stamps and enforces SPDX headers and runs tests.

Local helpers:
```bash
python scripts/add_spdx_headers.py   # stamp headers
python scripts/check_spdx_headers.py # verify headers
python scripts/check_licenses.py     # verify plugin LICENSE files
```

---

## Licensing
- **Core**: PolyForm-Noncommercial-1.0.0 (source-available; commercial use requires permission).
- **Plugins**: Apache-2.0 by default. Third-party plugins may specify a different license in their own directory.
