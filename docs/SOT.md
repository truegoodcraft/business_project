
# TGC BUS Core — Source of Truth (Final)

**Authority rule:** The uploaded **codebase is truth**. Where this document and the code disagree, the SoT **must be updated to reflect code**. Anything not stated = **unknown / not specified**.  
**Change note (2025-11-20):** Promotes `scripts/dev_bootstrap.ps1` to canonical dev launcher; preserves manual dev/smoke flow for clarity; documents Pro gating surfaces and current gaps (DB still under repo; AppData not yet cut over). Adds explicit canonical launch/smoke commands.
**Change note (2025-11-22):** DB is now bound to `%LOCALAPPDATA%\BUSCore\app\app.db` on Windows; engine + sessions are centralized in `core.appdb.engine`; `/dev/db/where` and `BUSCORE_DEBUG_DB` were added for DB diagnostics; Windows Store/MSIX Python is explicitly unsupported.

---

## 1) Identity & Naming

* **Company / Owner:** True Good Craft (**TGC**)
* **BUS acronym:** **Business Utility System**
* **Product name (canonical):** **TGC BUS Core**
* **Short form (UI):** **BUS Core**
* **Extended (docs, when needed):** **TGC BUS Core – Business Utility System Core by True Good Craft**

---

## 2) Purpose & Scope
* **Audience:** small and micro shops (makers, 1–10 person teams), especially those who prefer local-first tools.
* **Primary value:** keep **inventory, contacts, basic manufacturing**, and **critical data** on the owner’s machine, **not** in someone else’s cloud.
* **Core principles:**
  * **Local-first:** core runs on a single machine with local files and DB.
  * **Open core:** core is AGPL; commercial add-ons allowed (see Licensing).
  * **No forced cloud:** no mandatory SaaS / telemetrics for core features.
  * **Explicit Pro surfaces:** anything Pro-only must be clearly documented.

---

## 3) Architecture (High-Level)

* **Backend:** Python / FastAPI app (`core.api.http:create_app`).
* **DB:** SQLite (`sqlite+pysqlite`) via SQLAlchemy ORM.
* **UI:** Single-page shell (`core/ui/shell.html`) + modular JS cards.
* **Launcher:** PowerShell dev bootstrap (`scripts/dev_bootstrap.ps1`) plus smoke harness (`buscore-smoke.ps1`) for acceptance.
* **App-Data (Windows):** runtime data under `%LOCALAPPDATA%\BUSCore\…` (DB, secrets, state, exports) as detailed later.

---

## 4) Domain Model (Conceptual)

* **Vendors / Contacts:**
  * Vendors table unified for **organizations** and **people**.
  * Contacts behave as vendor rows with appropriate `role` / `kind`.
  * Dedupe and merge semantics defined in §9.
* **Items:**
  * Minimal core fields: `id`, `name`, `sku`, `item_type`, `vendor_id`, `qty`, `unit`, `meta`.
  * `item_type` enum is **soft-defined** (no strict SoT list yet; see Unknowns).
* **RFQ:**
  * Request for Quotation; currently early-stage / stub UI & endpoints.
* **Manufacturing:**
  * Manufacturing runs (formerly “Inventory run”) now anchored at `POST /app/manufacturing/run`.
  * Journals capture manufacturing actions as jsonl entries.

---

## 5) UI — Source of Truth (Binding, Zero-Drift)

**Authority:** This section is law for UI. If UI code disagrees, UI code is wrong until this section is updated first or Implementation Gaps call it out explicitly.

> **Note:** RFQ UI is currently **partial/stub** and the exact tab/screen layout is intentionally under-specified. Anything not explicitly stated is **unknown**. Treated as implementation gaps, not contradictions.

### 5.1 Shell & routing invariants

* **One shell:** `core/ui/shell.html` at `/ui/shell.html`.
* **One entry script:** `core/ui/app.js` (routing, boot, hashchange, navigate).
* **Hash routing only** (`#/…`).
* **Screens vs. cards:** primary screens (home / inventory / contacts / settings) are structural containers; cards are JS modules mounted into those containers. Only one of them is the *primary* visible screen per canonical route.

### 5.2 Canonical routes (edit this table first)

| Route / state        | Primary screen            | `data-role`            | Card file                              | Mount function     | License surface                           |
| -------------------- | ------------------------- | ---------------------- | -------------------------------------- | ------------------ | ----------------------------------------- |
| *No hash* / `#/home` | Home                      | `home-screen`          | static                                 | `mountHome()`      | None                                      |
| `#/BUSCore`          | Home (alias)              | `home-screen`          | static                                 | `mountHome()`      | None                                      |
| `#/inventory`        | Inventory (items + bulk)  | `inventory-screen`     | `core/ui/js/cards/inventory.js`       | `mountInventory()` | Pro intent: `POST /app/manufacturing/run` |
| `#/contacts`         | Contacts (vendors/people) | `contacts-screen`      | `core/ui/js/cards/vendors.js`         | `mountContacts()`  | None                                      |
| `#/settings`         | Settings / Dev            | `settings-screen`      | `core/ui/js/cards/settings.js`         | `settingsCard()`   | None                                      |

**Deliberate omissions:** no canonical `#/items`, `#/vendors`, `#/rfq` routes yet; RFQ UI remains a card within legacy Tools surface.

### 5.3 Tools drawer (sidebar) — structure & behavior

* **Toggle “Tools”** to show a drawer with links to **Inventory** and **Contacts** (navigates to `#/inventory` / `#/contacts`, then closes).
* Legacy `tools-screen` exists but stays **hidden**; no route binds to it.

### 5.4 License & UI gating style (soft)

* **Badge:** `[data-role="license-badge"]` shows `License: <tier>` from the protected health payload.
* **Gating policy:** backend enforces; UI keeps Pro controls visible but disabled or clearly labeled where appropriate (RFQ Generate, **Execute Manufacturing Run**, Import Commit).
* **Button/tooltip copy (Inventory card):**
  * Button: **“Execute Manufacturing Run”**
  * Tooltip (community): “Run a single recipe now (free) – save & automate in Pro”
* **Implementation state:** backend gates not yet enforced; UI not yet tier-aware.

### 5.4.1 Settings screen — Local Writes (updated 2025-11-22)

* **Route:** `#/settings` (see §5.2).
* **Primary screen:** `[data-role="settings-screen"]` containing `[data-role="settings-root"]`.
* **Card:** `settingsCard(host)` from `core/ui/js/cards/settings.js`.
* **Behavior:**
  * On mount, fetches `GET /dev/writes` and binds the **Local Writes** toggle to the `enabled` flag.
  * When the toggle changes, sends `POST /dev/writes` to persist the new value and shows a transient status (“saved” / “save failed”).
  * The existing Business Profile editor (backed by `/app/business_profile`) remains unchanged; the Local Writes toggle is an additional control, not a replacement.

### 5.5 Safe iteration rules

* Update §5.2–§5.4 **before** changing routes/primary screens/Pro surfaces.
* Use `ui(sot):` commit prefix when this section changes.
* New Pro surface ⇒ add a **community negative test** in smoke.

---

## 6) Data & Journals (High-Level)

* **Core DB:** SQLite, single primary file (see §11 for location and path rules).
* **Journals:** append-only `.jsonl` logs for sensitive actions (manufacturing, imports, plugin audits).
  * Manufacturing: `data/journals/manufacturing.jsonl` (name tracked in gaps until fully migrated from `inventory.jsonl`).
  * Import/bulk: `data/journals/bulk_import.jsonl`.
  * Plugin audit: `data/journals/plugin_audit.jsonl`.

---

## 7) Licensing (features)

* **Default tier:** `community`.
* **License file (Windows):** `%LOCALAPPDATA%\BUSCore\license.json`.
* **Gating policy (v1):** gate **only**:
  1. `POST /app/rfq/generate`
  2. `POST /app/manufacturing/run` — **gates Pro automation surface only**, not the free single-run button (community can still run one-off manufacturing runs manually).
  3. `POST /app/import/commit`
* **Community guarantees:**
  * Inventory, contacts, basic manufacturing, and backups are **always free** to run locally.
  * No “surprise” gates: any new Pro surface must be added to this section before release.

---

## 8) DB, Schema & Migrations (Behavioral)

### 8.1 ORM & Models (current scope)

* **ORM:** SQLAlchemy ORM models live under `core/appdb/models.py`.
* **Key tables (non-exhaustive):**
  * `vendors` — unified org/person/contacts model (see §9).
  * `items` — minimal item catalog with `item_type` and `vendor_id` FK.
  * `plans`, `policies`, `journal_*` tables/structures as needed.

### 8.2 Database schema (idempotent runtime migration)

* **Migration style:** **runtime, idempotent migrations** run on startup via `_ensure_schema_upgrades`.
* **Guarantee:** it is safe to call **multiple times**; no manual SQL migrations required.
* **Scope:** only minimal, additive changes (new columns with defaults, safe indexes); no destructive alters without explicit SoT change.
* **Upgrade hook locations:**
  * `core/appdb/engine.py` or equivalent central DB bootstrap.
  * Startup sequence in `core/api/app.py` / `core/api/http.py`.

---

## 9) Vendors & Contacts (Unified Model)

* **Single table:** `vendors` holds both organizations and people.
* **Columns (high level):**
  * `id`, `name`, `kind`, `role`, `organization_id`, `meta`, timestamps.
  * `kind`: e.g. `org`, `person`; **not strictly enumerated** yet.
  * `role`: e.g. `vendor`, `contact`, `both`.
* **Contacts API (current behavior):**
  * **Endpoint:** `/app/contacts` (CRUD).
  * **Storage:** persists to **`vendors`** table (unified model).
  * **Defaults (POST):** when omitted → `role='contact'`, `kind='person'`.
  * **Duplicate-name policy (POST):** if an existing row with the **same `name`** exists:
    * **Merge** instead of insert; set `role='both'`.
    * Merge `meta` JSON (incoming keys overwrite existing).
    * Optionally update `kind` and `organization_id`.
    * Respond **200** (idempotent create/merge).

---

## 10) Testing & Smoke Harness (authoritative for dev/test)

* **Canonical harness:** `buscore-smoke.ps1` at repo root. Must pass **100%** for acceptance.
* **Auth pattern:** mint via `GET /session/token`; send **`X-Session-Token`** on protected calls (tests don’t rely on cookies).
* **Success policy (smoke):** treat **`200 OK`** as CRUD success; other **2xx = fail** (smoke rule).
* **Diagnostics:** for any non-200 response, print first **200 bytes** of body with status.
* **Health assertions:**
  * Public: status 200; `{"ok": true}` seen **True**.
  * Protected: status 200; keys `[version, policy, license, run-id]` present **[True, True, True, True]**.

**Canonical smoke command (from repo root):**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\buscore-smoke.ps1
`````

### 10.1 Canonical dev launcher (law)

* **Canonical dev launcher script:** `scripts/dev_bootstrap.ps1` (repo root).

**Canonical dev launch command (from repo root):**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev_bootstrap.ps1
```

* Design intent for `dev_bootstrap.ps1`:

  * Run from a **fresh clone** directory.
  * Ensure Python deps (`requirements.txt`) are installed.
  * Export the same key env vars as the manual flow:

**Manual dev flow (Windows, still valid for clarity):**

**Window A — Server**

```powershell
cd "\TGC-BUS-Core-main"
python -m pip install -r requirements.txt
$env:PYTHONPATH = (Get-Location).Path
# Ensure a default license for dev if missing
$lic = Join-Path $env:LOCALAPPDATA 'BUSCore\license.json'
if (!(Test-Path $lic)) {
  New-Item -ItemType Directory -Force -Path (Split-Path $lic) | Out-Null
  '{"tier":"community","features":{},"plugins":{}}' | Set-Content -Path $lic
}
$env:BUS_UI_DIR = (Join-Path (Get-Location) 'core\ui')
python -m uvicorn core.api.http:create_app --host 127.0.0.1 --port 8765 --reload
```

**Window B — Smoke**

```powershell
cd "\TGC-BUS-Core-main"
$u = 'http://127.0.0.1:8765/session/token'
$max = 30
for ($i=0; $i -lt $max; $i++) {
  try { Invoke-WebRequest -UseBasicParsing $u -TimeoutSec 2 | Out-Null; break }
  catch { Start-Sleep -Seconds 1 }
}
powershell -NoProfile -ExecutionPolicy Bypass -File ".\buscore-smoke.ps1"
```

### 10.2 Windows Python requirement (updated 2025-11-22)

* **Supported Windows runtime:** BUS Core must run on the official **CPython** installer from python.org.
* **Microsoft Store / MSIX Python builds are explicitly unsupported** (they break `%LOCALAPPDATA%` path expectations and DB binding).
* **Reference build for public alpha:** `Python 3.14.0` (64-bit installer).
* Any Windows bug report must confirm:

  * `python --version` reports `3.14.0`.
  * `Get-Command python` resolves to the CPython installer under the user profile (not the `PythonSoftwareFoundation` MSIX path).

---

## 11) Operations & Release Process (authoritative)

* **Canonical source:** GitHub. There is **no** functional copy outside GitHub.
* **Acceptance workflow (every change):**

  1. Merge to GitHub (PR flow).
     *(Recent work may be squashed to streamline history.)*
  2. Download ZIP from GitHub.
  3. Unzip into a **fresh working directory**.
  4. Start BUS Core for dev/test (preferred: `scripts/dev_bootstrap.ps1`; alternative: manual flow in §10).
  5. Run `buscore-smoke.ps1` and record results.
  6. **Acceptance = all smoke assertions pass.**
* **Environment separation:**

  * **Local work/testing:** runs from the **fresh working directory** (unzipped tree; ephemeral).
  * **Production/state paths (Windows):**

    * **Design target:** all runtime data (DB, journals, exports/imports, secrets, state) live under **`%LOCALAPPDATA%\BUSCore\…`**.
    * **Current implementation (2025-11-22):** the **core SQLite database** is stored at **`%LOCALAPPDATA%\BUSCore\app\app.db`**. Any DB files under the repo working directory are considered **legacy/dev artifacts only**.
    * Secrets/config/state paths under `%LOCALAPPDATA%\BUSCore\…` remain authoritative for non-DB runtime data.
  * **Windows-only scope** for these path rules; other OS paths are **unchanged / not specified**.

---

## 12) Repository Hygiene & Legal

* **Privacy scrub:** removed hard-coded local paths/usernames and debug logs from code/comments/docs.
* **Top-level `LICENSE`:** present with official **AGPL-3.0** text; **SPDX headers** inserted across source files.
* **`.gitignore`:** added (Python template + project entries: envs, local DBs, UI `node_modules`, logs).

---

## 13) Implementation Gaps

* **License gating:** add checks on the **three** gated endpoints; surface tier/flags to UI to lock controls.
* **Manufacturing rename follow-through:**

  * Ensure all server references use **`/app/manufacturing/run`** (with alias from `/app/inventory/run` only if needed during transition).
  * **Optional:** rename journal file from `data/journals/inventory.jsonl` → `data/journals/manufacturing.jsonl` (adjust diagnostics).
* **Launcher scope:**

  * `scripts/dev_bootstrap.ps1` is now the **canonical dev launcher** (law) for local development.
  * Still pending: packaging/updater story and single-instance behavior for non-dev/desktop launch scenarios.
* **RFQ UI:** complete client workflow (inputs → call → results/attachments).
* **Items CRUD alignment:** ensure `/app/items` GET/POST/PUT and `/app/items/{id}` align with SoT expectations while keeping the **free** one-off qty rule.
* **(Optional next)** Smoke coverage for **`/app/contacts` merge semantics** (duplicate-name POST → merge).

---

## 14) Unknowns / Not Specified

* Cross-platform paths (macOS/Linux).
* Exact status code for license rejections (smoke asserts “not 200”).
* Full domain model field list / minimal payload shapes for CRUD.
* Enum validation for `item_type` or stricter dedupe constraints for contacts (e.g., `(name, organization_id)`).
* `organization_id` FK action (`SET NULL` / cascade / restrict).
* SPDX variant (`AGPL-3.0-only` vs `AGPL-3.0-or-later`) for headers.

---

## HTTP API – Endpoints

### Auth / Session / UI

* **GET `/session/token`** — returns current token as JSON; writes token to `data/session_token.txt`. Public; callers pass header later.
* **GET `/`**, **GET `/ui`**, **GET `/ui/index.html`** — redirect to **`/ui/shell.html`**.
* **GET `/ui/plugins/{plugin_id}[/{resource_path}]`** — serve plugin UI assets; 404 when missing.
* **GET `/health`** — **single token-aware route**:

  * Without `X-Session-Token` → `{"ok": true}` (200).
  * With `X-Session-Token` → detailed payload (200) with **tests for presence of keys** `version`, `policy`, `license`, `run-id` (no token validation).

### Dev / Diagnostics

* **GET `/dev/license`** — reloads or returns cached LICENSE dict.
* **GET `/dev/writes`** (async + sync) — report writes-enabled flag (one enforces token; one refreshes from disk).
* **POST `/dev/writes`** — `{enabled: bool}` persists flag.
* **GET `/dev/paths`** — enumerates filesystem roots.
* **GET `/dev/db/where`** — returns DB binding info (`engine_url`, `database`, `resolved_fs_path`, `PRAGMA database_list`). *(Added 2025-11-22).*
* **Env: `BUSCORE_DEBUG_DB=1`** — when set, logs DB path, engine URL, and `PRAGMA database_list` at startup for diagnostics. *(Added 2025-11-22).*
* **GET `/dev/journal/info`** — tails `data/journals/**manufacturing.jsonl` *(or legacy `inventory.jsonl` until rename is completed)* (protected).
* **GET `/dev/ping_plugin`** — Windows-only plugin host ping.

### App Domain (`/app/**`) — *legacy monolith removed; modular routers active*

* All `/app/**` inherit `Depends(require_token_ctx)`.
* **Vendors:** `GET/POST/PUT/DELETE /app/vendors[/{vendor_id}]`.
* **Contacts (unified with vendors):** `GET/POST/PUT/DELETE /app/contacts[/{id}]` (see §9).
* **Items:** `GET/POST/PUT/DELETE /app/items[/{item_id}]` (vendor validation; null-safe qty; supports `item_type`).
* **Transactions:** `POST /app/transactions`, `GET /app/transactions`, `GET /app/transactions/summary`.
* **Bulk import:** `POST /app/items/bulk_preview`, `POST /app/items/bulk_commit` (CSV/XLSX; journals `bulk_import.jsonl`; uses `X-Plugin-Name`).
* **Manufacturing:** `POST /app/manufacturing/run` (manual manufacturing run; Pro features gate automation/scheduling).
* **RFQ:** `POST /app/rfq/generate` (gated by license; UI partial).

### Plugin / Broker / Drive

* **Plugin broker:** HTTP-level endpoints mediated via `get_broker` and policy checks.
* **Drive provider:** Google Drive adapter exposed via REST:

  * **POST `/drive/connect`**, **GET `/drive/status`**, **POST `/drive/disconnect`**
  * **POST `/drive/list`**, **POST `/drive/download`**, **POST `/drive/upload`**
* **Catalog:** plugin catalog introspection:

  * **GET `/catalog/list`**
  * **POST `/catalog/open`**, **POST `/catalog/next`**, **POST `/catalog/close`**
  * **GET/POST `/index/state`**, **GET `/index/status`** — JSON index state; may schedule a **startup-only** background scan if stale.
  * **GET `/drive/available_drives`** — broker-backed Google Drive listing.

### OAuth (Google Drive)

* **POST `/oauth/google/start`** — consent URL + HMAC state (requires valid session).
* **GET `/oauth/google/callback`** — validate state, exchange tokens, store refresh via Secrets, redirect back to UI.
* **POST `/oauth/google/revoke`**, **GET `/oauth/google/status`** — revoke + status; clear caches on revoke.

### Policy, Plans, and Health

* **GET/POST `/policy`** — `%LOCALAPPDATA%\BUSCore\config.json`.
* **POST `/plans`**, **GET `/plans`**, **GET `/plans/{id}`**, **GET `/plans/{id}/export`** — plan lifecycle; `require_owner_commit` on commit.

### Local Filesystem & Control

* **GET `/local/available_drives`**, **GET `/local/validate_path`**, **POST `/open/local`**
* **POST `/server/restart`** — schedules process exit so launcher can restart.

### Helpers and Core Utilities

* **SessionGuard & helpers** (`require_token`, `require_token_ctx`, `require_owner_commit`, `get_session_token`) enforce header token on non-public routes.
* **`require_writes` / `get_writes_enabled`**; `/dev/writes` persists flag to `config.json`.
* **License utilities** (`_license_path`, `get_license`, `fetch_and_cache_license`) resolve `%LOCALAPPDATA%\BUSCore\license.json` (or `BUS_ROOT`) and normalize tier/flags.
* **App-data path helpers (Windows):** centralized helpers resolve and **create if missing**:

  * `%LOCALAPPDATA%\BUSCore\secrets`
  * `%LOCALAPPDATA%\BUSCore\state`
* **Backup/restore helpers** (`export_db`, `import_preview`, `import_commit`) guard against traversal; AES-GCM containers.
* **Bulk/journal helpers** (`journal_mutate`, `_append_plugin_audit`, etc.) write `bulk_import.jsonl`, `plugin_audit.jsonl`, capture previews in `data/imports`.
* **Index utilities** (`compute_local_roots_signature`, `_index_state`) manage sync; **startup-only** background scan when stale.
* **Policy helpers** (`load_policy`, `save_policy`, `require_owner_commit`).
* **Plan storage** (`save_plan`, `get_plan`, `list_plans`, `preview_plan`, `commit_local`).
* **DB/session (updated 2025-11-22):** `core.appdb.engine` constructs the single SQLAlchemy engine for the core database.

  * It exposes `ENGINE`, `SessionLocal`, and `get_session()` as the only supported entry points for DB access.
  * On Windows, the SQLite URL is built as `sqlite+pysqlite:///<posix_path>` (exactly three slashes) pointing to `%LOCALAPPDATA%\BUSCore\app\app.db`.
  * No other module may call `create_engine()` for the core DB; all sessions must come from `SessionLocal` / `get_session()`.
* **Broker:** `get_broker` initializes plugin broker with Secrets, capability registry, reader settings.

### Headers, Files, and Config Conventions

* **Custom headers:** `X-Session-Token` on protected requests; plugin API uses `X-TGC-Plugin-Name`, `X-TGC-License-URL`; bulk import auditing records `X-Plugin-Name`.

  * *Tests rely on the header; cookie may also be set.*
* **License file:** `%LOCALAPPDATA%\BUSCore\license.json` (or `BUS_ROOT\license.json`).
* **Runtime paths (Windows, updated 2025-11-22):**

  * `BUS_ROOT`, `APP_DIR`, `DATA_DIR`, `JOURNALS_DIR`, `IMPORTS_DIR` derive from `%LOCALAPPDATA%\BUSCore\app`.
  * **DB path:** `DB_PATH` is `%LOCALAPPDATA%\BUSCore\app\app.db` on Windows (canonical). Any DB files under the repo working directory are **ignored** for normal operation.
* **Backup artifacts:** `%LOCALAPPDATA%\BUSCore\exports`; journals under `data/journals`; previews under `data/imports`.
* **Manufacturing journal:** `data/journals/manufacturing.jsonl` *(or `inventory.jsonl` until renamed)*.
* **Session token persistence:** `data/session_token.txt` (launcher reuse).
* **Reader settings:** `%LOCALAPPDATA%\BUSCore\settings_reader.json`; **policy config:** `%LOCALAPPDATA%\BUSCore\config.json`.
* **Index state JSON:** `data/index_state.json`.

### API/Status Conventions (Tests)

* **CRUD success:** `200 OK` only (smoke policy).
* **Auth:** header token required on protected routes; cookie not relied on in tests.

---

**End of Source of Truth.**



