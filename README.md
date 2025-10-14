# 🤖 TGC Alpha Core

**Version: v.a0.01.3**

> A small, opinionated controller that boots, checks connections, shows status — and only digs deeper when you ask.

---

## What It Is

**TGC Alpha Core** is a lean automation hub. On start it loads plugins, performs base-layer probes via a scoped connection broker, and prints a clear status report. No crawling or writes by default.

---

## Pluggable Broker

Alpha Core now ships with a pluggable connection broker. The core stays integration-agnostic:

* Plugins live in `plugins_alpha/` and subclass `core.contracts.plugin_v2.PluginV2`.
* Each plugin calls `broker.register(...)` to provide services and probes.
* Core only knows about the services the plugins register and remains silent until they show up.

Google Drive, Sheets, Notion, and any other integrations live entirely in plugins under `plugins_alpha/`. Drop in a plugin package and restart the core to make the service available.

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

Plugins:

* Put plugins under `plugins_alpha/<your_plugin>/plugin.py`
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

Drop your plugin under `plugins_alpha/<name>/` and restart the core. Core discovers packages automatically and keeps Google/Notion details outside of the main runtime.

## Public API Contract (for plugins)

Plugins may only import:
- `core.contracts.plugin_v2`          (plugin base class & interface)
- `core.conn_broker`                  (broker types & client handle)
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

## License & Ownership

* 🧿 **Core Ownership**: The core is proprietary to True Good Craft (TGC). All rights reserved.
* 🔌 **Plugins**: You may create and add plugins for use within this software’s access scope. Your plugins remain yours; the core remains mine.
* ✅ **Permitted**: Build plugins, use the broker, run crawls.
* ❌ **Not Permitted**: Extracting or relicensing the core, or bypassing the broker/safety model.

If this helps you, buy your software a coffee. ☕️
