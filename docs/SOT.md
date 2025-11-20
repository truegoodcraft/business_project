# TGC BUS Core — Source of Truth (Final)

> **Authority rule:** The uploaded **codebase is truth**. Where documents conflicted, resolutions below reflect code. Anything not stated = **unknown / not specified**.

## 1) Identity & Naming

* **Company / Owner:** True Good Craft (**TGC**)
* **BUS acronym:** **Business Utility System**
* **Product name (canonical):** **TGC BUS Core**
* **Short form (UI):** **BUS Core**
* **Extended (docs, when needed):** **TGC BUS Core – Business Utility System Core by True Good Craft**

## 2) Baseline & Version

* **Current version:** **v0.5.0** (from `VERSION`).
* **Project baseline:** **Post-v0.5**.

## 3) Scope & Non-Goals

* **Local app** (FastAPI + SQLite).
* **No telemetry / external network calls:** not implemented; policy is to avoid.
* **Background automation:** allowed only for a one-shot **index-stale scan at startup**. No periodic schedulers/auto-crawls beyond that.
* Anything else: **not specified**.

## 4) Architecture & Runtime

* **Backend:** FastAPI; SQLite via SQLAlchemy.
* **Auth/session:** session token required; 401 retry flow present.
* **Writes guard:** explicit “writes enabled” gate exists.
* **Business logic location:** **Core** service (plugins exist; core holds business features).
* **Default local base URL:** `http://127.0.0.1:8765`.
* **Routing structure (modular):**

  * `core/api/http.py` initializes the app and **includes** modular routers under prefix **`/app`**.
  * Domain routers live in:

    * `core/api/routes/vendors.py`
    * `core/api/routes/items.py`
    * (Contacts CRUD is registered under the same `/app` prefix; see §9)
* **Startup hook:** `_ensure_schema_upgrades` runs **once on boot** to perform idempotent DB migrations (see §8.2).

## 5) UI — Source of Truth (Binding, Zero-Drift)

**Authority:** This section is law for UI. If UI code disagrees, UI code is wrong until this section is updated first or Implementation Gaps call it out explicitly.

> **Note:** RFQ UI is currently **partial/stub** and the **token/401/F5** behavior is **unknown**. Treated as implementation gaps, not contradictions.

### 5.1 Shell & routing invariants

* **One shell:** `core/ui/shell.html` at `/ui/shell.html`.
* **One entry script:** `core/ui/app.js` (routing, boot, hashchange, navigate).
* **Hash routing only** (`#/…`).
* **Screens vs. cards:** primary screens (home / inventory / contacts) can host multiple cards; exactly one of them is the *primary* visible screen per canonical route.

### 5.2 Canonical routes (edit this table first)

| Route / state        | Primary screen            | `data-role`        | Card / JS file                    | Mount function     | License surface                           |
| -------------------- | ------------------------- | ------------------ | --------------------------------- | ------------------ | ----------------------------------------- |
| *No hash* / `#/home` | Home                      | `home-screen`      | `core/ui/js/cards/home.js`        | `mountHome()`      | None                                      |
| `#/BUSCore`          | Home (alias)              | `home-screen`      | `core/ui/js/cards/home.js`        | `mountHome()`      | None                                      |
| `#/inventory`        | Inventory (items + bulk)  | `inventory-screen` | `core/ui/js/cards/inventory.js`   | `mountInventory()` | Pro intent: `POST /app/manufacturing/run` |
| `#/contacts`         | Contacts (vendors/people) | `contacts-screen`  | `core/ui/js/cards/vendors.js`     | `mountContacts()`  | None                                      |
| `#/settings`         | Settings / Dev (planned)  | *TBD*              | `core/ui/js/cards/settings.js`(p) | *TBD*              | None                                      |

**Deliberate omissions:** no canonical `#/items`, `#/vendors`, `#/tasks`, `#/rfq` routes yet; RFQ UI remains a card within legacy Tools surface.

### 5.3 Tools drawer (sidebar) — structure & behavior

* **Toggle “Tools”** to show a drawer with links to **Inventory** and **Contacts** (navigates to `#/inventory` / `#/contacts`, then closes).
* Legacy `tools-screen` exists but stays **hidden**; no route binds to it.

### 5.4 License & UI gating style (soft)

* **Badge:** `[data-role="license-badge"]` shows `License: <tier>` from the protected health payload.
* **Gating policy:** backend enforces; UI keeps Pro controls visible but **disabled/marked** on community (RFQ Generate, **Execute Manufacturing Run**, Import Commit).
* **Button/tooltip copy (Inventory card):**

  * Button: **“Execute Manufacturing Run”**
  * Tooltip (community): “Run a single recipe now (free) – save & automate in Pro”
* **Implementation state:** backend gates not yet enforced; UI not yet tier-aware.

### 5.5 Safe iteration rules

* Update §5.2–§5.4 **before** changing routes/primary screens/Pro surfaces.
* `ui(sot):` commit prefix when this section changes.
* New Pro surface ⇒ add a **community negative test** in smoke.

## 6) Features — Current Status

* **RFQ generation:** `POST /app/rfq/generate` (backend implemented); UI **partial/stub**.
* **Manufacturing run (formerly “Inventory run”):** `POST /app/manufacturing/run` implemented.

  * **Free (community):** one-off manual execution of a single recipe.
  * **Pro (future):** saved recipes, scheduling, multi-run queues, triggers, history, rollback.
* **Encrypted backup & restore:** implemented
  `POST /app/export` (AES-GCM; Argon2id/PBKDF2) • `POST /app/import/preview` • `POST /app/import/commit` (audited)
* **Domain CRUD (modular):**

  * **Vendors:** `/app/vendors` CRUD.
  * **Items:** minimal `/app/items` CRUD (GET/POST/PUT/DELETE); supports `item_type` (**default `product`**).
  * **Contacts:** `/app/contacts` CRUD (unified Vendors/Contacts; see §9).

## 7) Licensing (features)

* **Default tier:** `community`.
* **License file (Windows):** `%LOCALAPPDATA%\BUSCore\license.json`.
* **Gating policy (v1):** gate **only**:

  1. `POST /app/rfq/generate`
  2. `POST /app/manufacturing/run` — **gates Pro automation surfaces** (saved recipes, scheduling, queues, triggers, history/rollback).
     *Note: one-off manual execution remains **free**.*
  3. `POST /app/import/commit`

  * `POST /app/import/preview` stays **free** (still respects **writes**).
  * Simple one-off qty `PUT /app/items/{id}` stays **free**.
* **Implementation state:** license gates **not yet enforced in code** (to be added).
* **UI awareness:** UI must **read tier/flags** (from protected `/health`) to disable gated controls.

## 8) Security, Health & Schema

### 8.1 Security & Health

* **Session token** on all app routes; 401 retry in UI.
  **Exception:** `/health` has **no dependency**; header presence only selects payload.
* **Writes guard** on mutating ops.
* **Health (single, token-aware route):**
  `GET /health`

  * **No `X-Session-Token`:** `{"ok": true}` (200).
  * **With `X-Session-Token`:** `_health_details_payload()` (200) with top-level keys: `version`, `policy`, `license`, `run-id`.
  * **No token validation** is required; header presence selects detail payload.
* **Audit** lines on import commit.

### 8.2 Database schema (idempotent runtime migration)

* **Vendors** (unified Vendors/Contacts) — **additive columns**:

  * `role` (`vendor|contact|both`, **default `vendor`**; backfilled)
  * `kind` (`org|person`, **default `org`**; backfilled)
  * `organization_id` (FK to `vendors.id`)
  * `meta` (TEXT storing JSON; API returns parsed object)
* **Indexes & uniqueness:**

  * **Drop** any **unique** index on `vendors(name)`; **replace** with **non-unique** index (to support unified model & merge semantics).
  * Helpful indexes created: `vendors(role)`, `vendors(kind)`, `vendors(organization_id)`, `items(item_type)`, non-unique `vendors(name)`.
* **Items** — **additive column**:

  * `item_type` (TEXT; **default `product`**).

## 9) Contacts API & Semantics (unified with Vendors)

* **Endpoints:** `/app/contacts` — GET list, GET by id, POST, PUT, DELETE.
* **Storage:** persists to **`vendors`** table (unified model).
* **Defaults (POST):** when omitted → `role='contact'`, `kind='person'`.
* **Duplicate-name policy (POST):** if an existing row with the **same `name`** exists:

  * **Merge** instead of insert; set `role='both'`.
  * Merge `meta` JSON (incoming keys overwrite existing).
  * Optionally update `kind` and `organization_id`.
  * Respond **200** (idempotent create/merge).

## 10) Testing & Smoke Harness (authoritative for dev/test)

* **Canonical harness:** `buscore-smoke.ps1` at repo root. Must pass **100%** for acceptance.
* **Auth pattern:** mint via `GET /session/token`; send **`X-Session-Token`** on protected calls (tests don’t rely on cookies).
* **Success policy (smoke):** treat **`200 OK`** as CRUD success; other **2xx = fail** (smoke rule).
* **Diagnostics:** for any non-200 response, print first **200 bytes** of body with status.
* **Readiness wait:** wait on `/session/token` (≤ ~30s) before assertions.
* **UI presence:** `/ui/shell.html` returns 200 with non-empty body.
* **Path enforcement (hard cutover):**

  * **Fail** if any `%LOCALAPPDATA%\TGC\*` exists after a run.
  * **Ensure** `%LOCALAPPDATA%\BUSCore\secrets` and `%LOCALAPPDATA%\BUSCore\state` exist (create if needed).
  * On success, print **“paths: hard cutover validated”**.
* **Health assertions:**

  * Public: status 200; `{"ok": true}` seen **True**.
  * Protected: status 200; keys `[version, policy, license, run-id]` present **[True, True, True, True]**.

### Two-window PowerShell dev/test flow (canonical)

**Window A — Server**

```powershell
cd "D:\Vault Overhaul\TGC-BUS-Core-main"
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
cd "D:\Vault Overhaul\TGC-BUS-Core-main"
$u = 'http://127.0.0.1:8765/session/token'
$max = 30
for ($i=0; $i -lt $max; $i++) {
  try { Invoke-WebRequest -UseBasicParsing $u -TimeoutSec 2 | Out-Null; break }
  catch { Start-Sleep -Seconds 1 }
}
powershell -NoProfile -ExecutionPolicy Bypass -File ".\buscore-smoke.ps1"
```

## 11) Operations & Release Process (authoritative)

* **Canonical source:** GitHub. There is **no** functional copy outside GitHub.
* **Acceptance workflow (every change):**

  1. Merge to GitHub (PR flow).
     *(Recent work may be squashed to streamline history.)*
  2. Download ZIP from GitHub.
  3. Unzip into a **fresh working directory**.
  4. Run Window A (server) to bootstrap **community** `license.json`.
  5. Run Window B (smoke) and record results.
  6. **Acceptance = all smoke assertions pass.**
* **Environment separation:**

  * **Local work/testing:** runs from the **fresh working directory** (unzipped tree; ephemeral).
  * **Production/state paths (Windows):** all runtime data (DB, journals, exports, imports, settings, policy, **secrets**, **state**) live under **`%LOCALAPPDATA%\BUSCore\…`**.
  * **Windows-only scope** for these path rules; other OS paths are **unchanged / not specified**.

## 12) Repository Hygiene & Legal

* **Privacy scrub:** removed hard-coded local paths/usernames and debug logs from code/comments/docs.
* **Top-level `LICENSE`:** present with official **AGPL-3.0** text; **SPDX headers** inserted across source files.
* **`.gitignore`:** added (Python template + project entries: envs, local DBs, UI `node_modules`, logs).

## 13) Implementation Gaps

* **License gating:** add checks on the **three** gated endpoints; surface tier/flags to UI to lock controls.
* **Manufacturing rename follow-through:**

  * Ensure all server references use **`/app/manufacturing/run`** (keep temporary alias from `/app/inventory/run` only if needed during transition).
  * **Optional:** rename journal file from `data/journals/inventory.jsonl` → `data/journals/manufacturing.jsonl` (adjust diagnostics).
* **Launcher scope:** add license bootstrap, single-instance focus, updater stub (packaging/ops).
* **RFQ UI:** complete client workflow (inputs → call → results/attachments).
* **Items CRUD alignment:** ensure `/app/items` GET/POST/PUT and **simple qty PUT** on `/app/items/{id}` while keeping the **free** one-off qty rule.
* **(Optional next)** Smoke coverage for **`/app/contacts` merge semantics** (duplicate-name POST → merge).

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

* **GET `/session/token`** — returns current token as JSON; entry mint persists to `data/session_token.txt`. Public; callers pass header later.
* **GET `/`**, **GET `/ui`**, **GET `/ui/index.html`** — redirect to **`/ui/shell.html`**.
* **GET `/ui/plugins/{plugin_id}[/{resource_path}]`** — serve plugin UI assets; 404 when missing.
* **GET `/health`** — **single token-aware route**:

  * Without `X-Session-Token` → `{"ok": true}` (200).
  * With `X-Session-Token` → detailed payload (200) with **top-level** `version`, `policy`, `license`, `run-id` (no token validation).

### Dev / Diagnostics

* **GET `/dev/license`** — reloads or returns cached LICENSE dict.
* **GET `/dev/writes`** (async + sync) — report writes-enabled flag (one enforces token; one refreshes from disk).
* **POST `/dev/writes`** — `{enabled: bool}` persists flag.
* **GET `/dev/paths`** — enumerates filesystem roots.
* **GET `/dev/journal/info`** — tails `data/journals/**manufacturing**.jsonl` *(or `inventory.jsonl` until journal rename is completed)* (protected).
* **GET `/dev/ping_plugin`** — Windows-only plugin host ping.

### App Domain (`/app/**`) — *legacy monolith removed; modular routers active*

* All `/app/**` inherit `Depends(require_token_ctx)`.
* **Vendors:** `GET/POST/PUT/DELETE /app/vendors[/{vendor_id}]`.
* **Contacts (unified with vendors):** `GET/POST/PUT/DELETE /app/contacts[/{id}]` (see §9).
* **Items:** `GET/POST/PUT/DELETE /app/items[/{item_id}]` (vendor validation; null-safe qty; supports `item_type`).
* **Transactions:** `POST /app/transactions`, `GET /app/transactions`, `GET /app/transactions/summary`.
* **Bulk import:** `POST /app/items/bulk_preview`, `POST /app/items/bulk_commit` (CSV/XLSX; journals `bulk_import.jsonl`; uses `X-Plugin-Name`).
* **Attachments:** `GET/POST/DELETE /app/attachments/*`.
* **Export/Import:**

  * `POST /app/export` — encrypted DB archive; **requires writes**.
  * `POST /app/import/preview` — **free by license; requires writes**.
  * `POST /app/import/commit` — **gated by license**; **requires writes**.
* **RFQ:** `POST /app/rfq/generate` — **gated by license**; **requires writes**.
* **Manufacturing:** `POST /app/manufacturing/run` — **free for one-off manual**; **Pro-gated** when invoking saved/automated flows; **requires writes**.
* **Tasks:** `GET/POST/PUT/DELETE /app/tasks[/{task_id}]`.

### Reader / Organizer (protected)

* **POST `/reader/local/resolve_ids`**, **POST `/reader/local/resolve_paths`**
* **POST `/organizer/duplicates/plan`**, **POST `/organizer/rename/plan`**

### Settings, Catalog, and Indexing

* **GET/POST/DELETE `/settings/google`**
* **GET/POST `/settings/reader`**
* **POST `/catalog/open`**, **POST `/catalog/next`**, **POST `/catalog/close`**
* **GET/POST `/index/state`**, **GET `/index/status`** — JSON index state; may schedule a **startup-only** background scan if stale.
* **GET `/drive/available_drives`** — broker-backed Google Drive listing.

### OAuth (Google Drive)

* **POST `/oauth/google/start`** — consent URL + HMAC state (requires valid session).
* **GET `/oauth/google/callback`** — validate state, exchange tokens, store refresh via Secrets, redirect back to UI.
* **POST `/oauth/google/revoke`**, **GET `/oauth/google/status`** — revoke + status; clear caches on revoke.

### Policy, Plans, and Health

* **GET/POST `/policy`** — `%LOCALAPPDATA%\BUSCore\config.json`.
* **POST `/plans`**, **GET `/plans`**, **GET `/plans/{id}`**, **POST `/plans/{id}/preview`**, **POST `/plans/{id}/commit`**, **POST `/plans/{id}/export`** — plan lifecycle; `require_owner_commit` on commit.

### Local Filesystem & Control

* **GET `/local/available_drives`**, **GET `/local/validate_path`**, **POST `/open/local`**
* **POST `/server/restart`** — schedules process exit so launcher can restart.

### Helpers and Core Utilities

* **SessionGuard & helpers** (`require_token`, `require_token_ctx`, `_require_session`, `get_session_token`) enforce header token on non-public routes.
* **`require_writes` / `get_writes_enabled`**; `/dev/writes` persists flag to `config.json`.
* **License utilities** (`_license_path`, `get_license`, `feature_enabled`) read `%LOCALAPPDATA%\BUSCore\license.json` (or `BUS_ROOT`) and normalize tier/flags.
* **App-data path helpers (Windows):** centralized helpers resolve and **create if missing**:

  * `%LOCALAPPDATA%\BUSCore\secrets`
  * `%LOCALAPPDATA%\BUSCore\state`
* **Backup/restore helpers** (`export_db`, `import_preview`, `import_commit`) guard against traversal; AES-GCM containers.
* **Bulk/journal helpers** (`journal_mutate`, `_append_plugin_audit`, bulk import helpers) write `bulk_import.jsonl`, `plugin_audit.jsonl`, capture previews in `data/imports`.
* **Index utilities** (`compute_local_roots_signature`, `_index_status_payload`, `_catalog_background_scan`, `_run_background_index`) manage sync; **startup-only** background scan when stale.
* **Policy helpers** (`load_policy`, `save_policy`, `require_owner_commit`).
* **Plan storage** (`save_plan`, `get_plan`, `list_plans`, `preview_plan`, `commit_local`).
* **DB/session:** `get_session` yields SQLAlchemy sessions with `_resolve_db_path`.
* **Broker:** `get_broker` initializes plugin broker with Secrets, capability registry, reader settings.

### Headers, Files, and Config Conventions

* **Custom headers:** `X-Session-Token` on protected requests; middleware may add `X-TGC-License` / `X-TGC-License-URL`; bulk import auditing records `X-Plugin-Name`.
  *Tests rely on the header; cookie may also be set.*
* **License file:** `%LOCALAPPDATA%\BUSCore\license.json` (or `BUS_ROOT\license.json`).
* **Runtime paths:** `BUS_ROOT`, `APP_DIR`, `DATA_DIR`, `JOURNALS_DIR`, `IMPORTS_DIR`, `DB_PATH` derive from `%LOCALAPPDATA%\BUSCore\app`.
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
