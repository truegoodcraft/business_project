# 🤖 TGC Alpha Core

**Version: v.a0.01.2**

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

## Quickstart (HTTP)

```bash
python -m pip install -r requirements.txt
python app.py serve
# Copy the session token from console or data\session_token.txt
```

```powershell
$token = type .\data\session_token.txt
irm http://127.0.0.1:8765/health -Headers @{ 'X-Session-Token' = $token }
irm http://127.0.0.1:8765/plugins -Headers @{ 'X-Session-Token' = $token }
irm http://127.0.0.1:8765/probe -Method Post -Headers @{ 'X-Session-Token' = $token } -ContentType "application/json" -Body "{}"
```

* `/health` reports the running version and session.
* `/plugins` lists the plugins that registered providers.
* `/probe` asks the broker to check each requested service.

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
