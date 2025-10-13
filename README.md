# Alpha Core

The Alpha Core provides a slim controller that boots the system, discovers v2 plugins, probes configured services, and reports status. A deep crawl is only started when explicitly requested.

## Quickstart

```bash
python app.py alpha               # boot, discover v2 plugins, probe base services
python app.py alpha --crawl       # boot + start full index/crawl
python app.py alpha --fast --max-files 500 --timeout 60 --crawl
```

`--fast`, `--timeout`, `--max-files`, `--max-pages`, and `--page-size` constrain crawl workloads only. The boot/probe flow always runs with the same semantics. `--dry-run` is reserved for future write actions during crawl execution.

## First Run (Alpha)

1. Run: `python app.py` → creates `credentials/`, `data/`, `logs/`, and `.env` with helpful defaults.
2. Drop your Google **service-account.json** into `credentials/` (or set an absolute path in `.env`).
3. Set `DRIVE_ROOT_IDS` and `SHEET_INVENTORY_ID` in `.env` (optional for boot; required for crawl).
4. Re-run: `python app.py` → status shows OK/PENDING along with hints.
5. Start crawl on demand: `python app.py alpha --crawl --fast --max-files 500 --timeout 60`.

### Troubleshooting

- Shared Drives: invite the service account email as a member of each shared drive you want indexed.

## Plugin API (v2)

Alpha plugins must implement the `PluginV2` interface defined in `core/contracts/plugin_v2.py`:

```python
class PluginV2:
    id: str = "plugin"
    name: str = "Alpha Plugin"

    def probe(self, broker) -> Dict[str, Any]:
        raise NotImplementedError

    def describe(self) -> Dict[str, Any]:
        return {"services": [], "scopes": ["read_base"]}

    def run(self, broker, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"ok": True}
```

An example plugin lives in `plugins_alpha/example_plugin.py`:

```python
from core.contracts.plugin_v2 import PluginV2

class Plugin(PluginV2):
    id = "example"
    name = "Example Alpha Plugin"

    def describe(self):
        base = super().describe()
        base["services"] = ["drive"]
        return base

    def probe(self, broker):
        return broker.probe("drive")
```

Plugins should list the services they depend on via `describe().services`. The core will call `ConnectionBroker.probe(service)` for each service before invoking `plugin.probe(broker)` to allow additional validation.

Place plugins in `plugins_alpha/` and export them via a `Plugin` subclass of `PluginV2` to have them auto-discovered during boot.

## Connection Broker

The connection broker issues scoped client handles for services. Supported scopes:

- `read_base`
- `read_crawl`
- `write`

Once a service has been granted a scope, the broker will not escalate that service to `write` during the same run. Attempts to escalate are denied and logged via `broker.escalation.denied`. Repeated requests for the same scope or lower scopes are permitted.

## What’s removed

- Developer/`--dev` CLI flows
- Legacy plugin adapters and compatibility layers
- Safe-mode first boot paths (`OFFLINE_SAFE_MODE` no longer blocks startup)
- Default deep crawls (now opt-in via `--crawl`)

## Alpha expectations

The Alpha Core is intentionally breaking and may change quickly before beta. Boot/probe is read-only. Write paths (when introduced) must honor `--dry-run` during the crawl phase. The status output lists reachable services, enabled plugins, and the effective crawl configuration.

## Design Rationale

Alpha isolates the boot/probe phase from the expensive crawl. Booting always initializes the controller, discovers v2 plugins, and probes base connections. Crawls are executed only when the operator passes `--crawl`, reusing the existing master index pipeline while respecting the provided limits.
