# 🤖 TGC Alpha Core

> A small, opinionated controller that boots, checks connections, shows status — and only digs deeper when you ask.

---

## What It Is

**TGC Alpha Core** is a lean automation hub. On start it loads plugins, performs **base‑layer probes** via a scoped connection broker, and prints a clear status report. No crawling or writes by default. 🧭

**Use it to:**

* See which integrations are reachable (Notion, Drive, Sheets, etc.)
* Verify your plugin setup
* Optionally trigger a crawl or index when you’re ready

---

## Safety & Transparency

* 🔒 **Scoped clients**: `read_base`, `read_crawl`, `write`
* 🚫 **No scope escalation**: a plugin can’t jump from read → write
* 🧪 **Probe‑only boot**: the default path is read‑only
* 🧾 **One‑line header + status table** every run

---

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Boot, list plugins, probe connections, print status, exit
python app.py alpha

# Start a crawl or index (optional)
python app.py alpha --crawl --fast --timeout 60 --max-files 500 --max-pages 5000 --page-size 100
```

---

## First Run (Alpha)

1. Run: `python app.py` → creates `credentials/`, `data/`, `logs/`, and `.env` with helpful defaults.
2. Drop your Google **service-account.json** into `credentials/` (or set an absolute path in `.env`).
3. Set `DRIVE_ROOT_IDS` and `SHEET_INVENTORY_ID` in `.env` (optional for boot; required for crawl).
4. Re-run: `python app.py` → status shows OK/PENDING along with hints.
5. Start crawl on demand: `python app.py alpha --crawl --fast --max-files 500 --timeout 60`.

### Troubleshooting

- Shared Drives: invite the service account email as a member of each shared drive you want indexed.

## Plugin API (v2)
## Commands

* `alpha` → boot + probe + status ✅
* `alpha --crawl` → perform full index/crawl (respects limits) ⛏️
* `--fast`, `--timeout`, `--max-files`, `--max-pages`, `--page-size` → constrain crawls ⚙️

---

## Plugin v2 (Alpha)

A minimal contract for integrations:

```python
class PluginV2:
    id: str
    name: str
    def probe(self, broker) -> dict: ...      # return {"ok": bool, "detail"?: str}
    def describe(self) -> dict: ...           # {"services": ["drive"], "scopes": ["read_base"]}
    def run(self, broker, options: dict | None = None) -> dict: ...
```

Guidelines: declare services in `describe()`, keep `probe()` fast, expect **scoped** handles from the broker.

---

## Example Output

```
[run:2025-10-13T19:40:31Z] mode=alpha fast=False timeout_sec=None max_files=None max_pages=None page_size=None
Services: 2/3 reachable
  - drive: OK
  - notion: FAIL (missing token)
  - sheets: OK
Plugins enabled: 2
  - master_index
  - my_custom_plugin
```

---

## License & Ownership

* 🧿 **Core Ownership**: The **core** is proprietary to True Good Craft (TGC). All rights reserved. I retain control over the core and all decisions related to it.
* 🔌 **Plugins**: You may create and add plugins for use **within this software’s access scope**. Your plugins remain yours; the core remains mine.
* ✅ **Permitted**: Build plugins, use the broker, run crawls.
* ❌ **Not Permitted**: Extracting or re‑licensing the core, or bypassing the broker/safety model.

If this helps you, buy your software a coffee. ☕️

# 🤖 TGC Alpha Core

> A small, opinionated controller that boots, checks connections, shows status — and only digs deeper when you ask.

---

## What It Is

**TGC Alpha Core** is a lean automation hub. On start it loads plugins, performs **base‑layer probes** via a scoped connection broker, and prints a clear status report. No crawling or writes by default. 🧭

**Use it to:**

* See which integrations are reachable (Notion, Drive, Sheets, etc.)
* Verify your plugin setup
* Optionally trigger a crawl or index when you’re ready

---

## Safety & Transparency

* 🔒 **Scoped clients**: `read_base`, `read_crawl`, `write`
* 🚫 **No scope escalation**: a plugin can’t jump from read → write
* 🧪 **Probe‑only boot**: the default path is read‑only
* 🧾 **One‑line header + status table** every run

---

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Boot, list plugins, probe connections, print status, exit
python app.py alpha

# Start a crawl or index (optional)
python app.py alpha --crawl --fast --timeout 60 --max-files 500 --max-pages 5000 --page-size 100
```

---

## Commands

* `alpha` → boot + probe + status ✅
* `alpha --crawl` → perform full index/crawl (respects limits) ⛏️
* `--fast`, `--timeout`, `--max-files`, `--max-pages`, `--page-size` → constrain crawls ⚙️

---

## Plugin v2 (Alpha)

Place plugins in `plugins_alpha/` and export them via a `Plugin` subclass of `PluginV2` to have them auto-discovered during boot.

## Connection Broker
A minimal contract for integrations:

```python
class PluginV2:
    id: str
    name: str
    def probe(self, broker) -> dict: ...      # return {"ok": bool, "detail"?: str}
    def describe(self) -> dict: ...           # {"services": ["drive"], "scopes": ["read_base"]}
    def run(self, broker, options: dict | None = None) -> dict: ...
```

Guidelines: declare services in `describe()`, keep `probe()` fast, expect **scoped** handles from the broker.

---

## Example Output

```
[run:2025-10-13T19:40:31Z] mode=alpha fast=False timeout_sec=None max_files=None max_pages=None page_size=None
Services: 2/3 reachable
  - drive: OK
  - notion: FAIL (missing token)
  - sheets: OK
Plugins enabled: 2
  - master_index
  - my_custom_plugin
```

---

## License & Ownership

* 🧿 **Core Ownership**: The **core** is proprietary to True Good Craft (TGC). All rights reserved. I retain control over the core and all decisions related to it.
* 🔌 **Plugins**: You may create and add plugins for use **within this software’s access scope**. Your plugins remain yours; the core remains mine.
* ✅ **Permitted**: Build plugins, use the broker, run crawls.
* ❌ **Not Permitted**: Extracting or re‑licensing the core, or bypassing the broker/safety model.

If this helps you, buy your software a coffee. ☕️
