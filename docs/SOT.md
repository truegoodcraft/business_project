TGC BUS Core — Source of Truth (Updated 2025-12-05) 

> **Authority rule:** The uploaded **codebase is truth**.
> Where this document and the code disagree, the SoT **must be updated to reflect code**.
> Anything not stated = **unknown / not specified**.

> **Change note (2025-12-05, v0.8.2 "Manufacturing Locked"):**
> **DELTA INCORPORATION:** Merged two sessions into final state:
> 1. **Zero-license cleanup & UI footer (targeting v0.8.1):** Core now zero-tier, zero-license.json, zero license enforcement. Tier removed from all surfaces (/health, UI, logs, config, DB, backups, journals, local storage). License config/env/DTOs deleted. `/dev/license` removed. RFQ, batch automation, scheduled runs removed from Core. No "Pro", "Upgrade", "Tier" wording in UI or API. **BUS Core Pro exists only as separate commercial project (outside this repo).**
> 2. **Manufacturing/ledger smoke & invariants (v0.8.2):** `scripts/smoke.ps1` canonical on PowerShell 5.1 (no PS7+ features). Session token via `GET /session/token` before protected ops. Canonical endpoints: /session/token, /openapi.json, /app/items, /app/ledger/adjust, /app/recipes, /app/manufacturing/run, /app/ledger/movements. Manufacturing invariants locked: never oversell (is_oversold=0), shortage → HTTP 400 with no writes (fail-fast), ad-hoc runs require non-empty components[], output unit cost = sum(consumed)/qty (round-half-up), single-run POST only.
> * **Final merged state (0.8.2):** Zero-license Core with locked manufacturing FIFO invariants. All code-truth updates incorporated.

> **Change note (2025-12-02, v0.6.0):** (historical) Major architectural update: canonical `scripts/launch.ps1` and `scripts/smoke.ps1`; initial ledger bootstrap, cookie-based auth.

(Older change notes retained below as historical log.)

---

## Versioning & Changelog

* **Current SoT document version:** `v0.8.2 "Manufacturing Locked"`
* **Previous version:** v0.9.0 "Iron Core Beta" (superseded by v0.8.2 after delta merges)

* All BUS Core SoTs and adjacent TGC method/process docs use a three-part version string: `vX.Y.Z`.

  * **X – Release track.** `0` = pre–official-release track; `1` = first formal release of the method/product; higher values represent later lifecycle stages.
  * **Y – Major document/product version.** Bump when structure/meaning changes enough to confuse a reader of an older version.
  * **Z – Iteration / patch.** Bump for **any** edit, including typos.

* Triggers:

  * Any edit at all ⇒ bump **Z**.
  * Structural / meaning change ⇒ bump **Y**.
  * New lifecycle phase (e.g. pre-launch → public → taught) ⇒ bump **X**.

* Changelog rules (this document):

  * Every SoT change adds a **Change note (YYYY-MM-DD, vX.Y.Z …)** at the top with a short summary.
  * Older "Change note (YYYY-MM-DD)" entries are preserved as history.

(Existing historical change notes from v0.5.x/v0.6.0 remain as-is.)

---

---

## 1) Identity & Naming

* **Company / Owner:** True Good Craft (**TGC**)
* **BUS acronym:** **Business Utility System**
* **Product name (canonical):** **TGC BUS Core**
* **Short form (UI):** **BUS Core**
* **Extended (docs, when needed):**
  **TGC BUS Core – Business Utility System Core by True Good Craft**

---

## 2) Purpose & Scope

* **Audience:** small/micro shops (makers, 1–10 person teams), especially local-first, anti-SaaS owners.

* **Primary value:** keep **inventory, contacts, manufacturing, and critical data** on the owner’s machine, **not** in someone else’s cloud.

* **Core principles:**

  * **Local-first:** core runs on a single machine with local files and DB.
  * **Open core:** Core is AGPL; commercial add-ons (BUS Core Pro) exist **as a separate project** and do **not** live inside this repo.
  * **No forced cloud:** no mandatory SaaS / telemetry for Core features.
  * **Local-only analytics:** all analytics used by Core (Home, Recent Activity, Insights) are computed from **local DB + event store only**.
  * **Single-operator friendly:**

    > If it only takes one person to run the shop, it should only take one person to manage the system.

---

## 3) Architecture (High-Level)

* **Backend:** Python / FastAPI (`core.api.http:create_app`).

* **DB engine:** SQLite via SQLAlchemy ORM.

* **UI:** Single-page shell (`core/ui/shell.html`) + modular JS cards.

* **Launcher (dev):** Canonical PowerShell launcher: `scripts/launch.ps1`.

  * Creates/uses `.venv`.
  * Installs deps (lockfile-first policy).
  * Binds DB and starts Uvicorn at `http://127.0.0.1:8765`.

* **Smoke harness:** Canonical dev smoke: `scripts/smoke.ps1`.

  * Cookie-based auth via `/session/token`.
  * Must pass for acceptance.

* **App-Data & DB (Windows, 0.9 canonical):**

  * **Default DB path (when `BUS_DB` unset):**
    `%LOCALAPPDATA%\BUSCore\app\app.db`
  * **Override:** if `BUS_DB` is set, that path is used.
  * **One-time migration:** on first run, if `data/app.db` exists in the repo and AppData DB does not, Core **copies** `data/app.db` to `%LOCALAPPDATA%\BUSCore\app\app.db` and then uses the AppData DB going forward.
  * Other runtime data (config, exports, journals, etc.) live under `%LOCALAPPDATA%\BUSCore\…` as defined below.

---

## 4) Domain Model (Conceptual)

### 4.1 Vendors / Contacts

* Single `vendors` table for **people and organizations** we deal with.
* Fields: `id`, `name`, `role`, `kind`, `organization_id`, `meta`, timestamps, plus legacy `contact` string.
* `kind`: e.g. `org`, `person` (soft enum).
* `role`: e.g. `vendor`, `contact`, `both`.
* Structured contact fields:

  * `meta.email` and `meta.phone` are canonical for email/phone.
  * Legacy combined `"email | phone"` lives only as historical input; must be parsed into structured fields on edit.

### 4.2 Items

* Minimal catalog for anything we track in the workshop.
* Fields: `id`, `vendor_id`, `sku`, `name`, `qty`, `qty_stored`, `uom`, `unit`, `price`, `notes`, `item_type`, `created_at`.
* `item_type` is soft-enum (e.g. product/material/component).
* **Ledger behavior:** On-hand checks prefer `qty_stored` if present; otherwise fall back to `qty`.

### 4.3 Ledger – Batches & Movements (canonical 0.9)

Core valuation and stock history live in two tables:

#### 4.3.1 Table: `item_batches`

* `id` – PK (INTEGER).
* `item_id` – FK → `items.id` (required).
* `qty_remaining` – REAL; remaining unconsumed quantity in this batch.
* `unit_cost_cents` – INTEGER; per-unit cost in cents for this batch.
* `created_at` – timestamp; creation time and FIFO ordering anchor.

**Behavior:**

* A **purchase / stock-in** creates a new batch:

  * `qty_remaining = purchased_qty`
  * `unit_cost_cents = purchase_unit_cost_cents`

* Valuation for an item:

  * `Σ(qty_remaining * unit_cost_cents)` over all open batches for that item.

#### 4.3.2 Table: `item_movements`

* `id` – PK.
* `item_id` – FK → `items.id` (required).
* `batch_id` – FK → `item_batches.id` (nullable for non-batch-specific moves).
* `qty_change` – REAL; positive = stock-in, negative = stock-out.
* `unit_cost_cents` – INTEGER; cost per unit for this movement (in cents).
* `source_kind` – string enum, e.g. `purchase`, `consume`, `manufacturing`, `adjustment`.
* `source_id` – identifier for upstream entity (e.g. purchase id, run id).
* `is_oversold` – INTEGER (0/1) flag for oversold movement.
* `created_at` – timestamp.

**FIFO invariants:**

* Purchases:

  * Create a batch `item_batches` row **and** a positive `item_movements` row at the batch’s cost.

* Consumes:

  * Create one or more **negative** `item_movements` rows allocated FIFO:

    * Consume from the oldest open batch until requested qty is satisfied.

* Oversold:

  * If a consume exceeds current on-hand quantity, Core still records movements and marks `is_oversold=1` to flag oversold behavior (for **non-manufacturing** flows only).

* Quantities use REAL (floats); money uses INTEGER cents.

### 4.4 Manufacturing – Recipes & Runs

Manufacturing is layered on top of items + ledger.

#### 4.4.1 Table: `recipes`

* `id` – PK (INTEGER).
* `name` – TEXT, required.
* `code` – TEXT, nullable, `UNIQUE` when non-null.
* `output_item_id` – FK → `items.id`, required.
* `output_qty` – REAL, required, default `1.0`.
* `notes` – TEXT, nullable.
* `is_archived` – INTEGER, default `0` (0=active, 1=archived).
* `created_at`, `updated_at` – timestamps.

**Rules:**

* `name` + `output_item_id` should be effectively unique (enforced at UI level).
* Archiving a recipe does **not** affect historical runs.

#### 4.4.2 Table: `recipe_items`

* `id` – PK.
* `recipe_id` – FK → `recipes.id`, required.
* `item_id` – FK → `items.id`, required.
* `qty_required` – REAL, required (per base `output_qty`).
* `is_optional` – INTEGER, default `0` (0=required, 1=optional).
* `sort_order` – INTEGER, nullable.
* `created_at`, `updated_at` – timestamps.

**Capacity:**

* For each **required** component:

  * `capacity_for_component = floor(on_hand_qty / qty_required)`

* Recipe capacity = `min(capacity_for_component)` across required components.

* Optional components are ignored for capacity calculations.

#### 4.4.3 Table: `manufacturing_runs`

* `id` – PK (INTEGER).

* `recipe_id` – FK → `recipes.id`, nullable (ad-hoc runs may be recipe-less).

* `output_item_id` – FK → `items.id`, required.

* `output_qty` – REAL, required.

* `status` – TEXT, required; one of:

  * `pending`
  * `completed`
  * `failed_insufficient_stock`
  * `failed_error`

* `created_at` – timestamp, required.

* `executed_at` – timestamp, nullable.

* `notes` – TEXT, nullable.

* `meta` – JSON, nullable.

**Run semantics:**

* On **validation failure** (insufficient required stock):

  * Insert `manufacturing_runs` row with `status="failed_insufficient_stock"`.
  * **No** `item_movements` or `item_batches` modifications.

* On **execution error** (after validation):

  * `status="failed_error"`; transaction must roll back so no partial movements.

* On **success**:

  * Consume all components and produce outputs **atomically** within one transaction.
  * `status="completed"`.

#### 4.4.4 Recipe-based execution

For a recipe-based run:

* Scale factor:

  * `k = output_qty_run / recipes.output_qty`

* For each component row:

  * required component: `required_qty = recipe_items.qty_required * k`
  * optional component: same formula.

**Required components:**

* For each required component:

  * Compute `required_qty`.
  * Check FIFO on-hand.
  * If **any** required component has `required_qty > on_hand_qty`:

    * HTTP 400 with structured shortages (`component, required, available`).
    * **No** movements or batch changes.
    * `manufacturing_runs.status="failed_insufficient_stock"`.

**Optional components:**

* Optional components **never** block runs and **never** oversell.
* In 0.9, optional components with insufficient stock are **skipped** (no movement).

#### 4.4.5 Ad-hoc runs (no recipe_id)

* Components are implicitly **required**.
* Required qty: `component.qty_required * run.output_qty`.
* Same semantics: any shortage → HTTP 400, no movements, `status="failed_insufficient_stock"`.

#### 4.4.6 Oversold rules for manufacturing

* Manufacturing runs must **never create oversold movements**:

  * All manufacturing movements have `is_oversold=0`.

* If inputs insufficient, run fails with 400 and writes **no** movements.

* `is_oversold=1` is reserved for other flows (e.g., sales/consumes that allow oversell).

---

## 5) UI — Source of Truth

**Authority:** This section is law for UI. If UI code disagrees, UI is wrong until this section is updated or an Implementation Gap calls it out.

### 5.1 Shell & routing invariants

* One shell: `core/ui/shell.html` at `/ui/shell.html`.
* One entry script: `core/ui/app.js`.
* Hash routing only (`#/…`).
* Screens vs. cards: primary screens (dashboard, inventory, contacts, recipes, runs, settings, etc.) are structural containers; cards are JS modules mounted into those containers.

### 5.2 Canonical routes & deep-links (0.9)

**Canonical routes:**

* `#/home` – dashboard/home.
* `#/inventory` – items list (Inventory).
* `#/inventory/<id>` – item detail/deep-link (expands and scrolls target row).
* `#/contacts` – vendors/contacts list.
* `#/contacts/<id>` – contact detail.
* `#/recipes` – recipes list (master view).
* `#/recipes/<id>` – recipe detail (master-detail).
* `#/runs` – manufacturing runs list.
* `#/runs/<id>` – run detail.
* `#/import` – import/export & backup/restore surface.
* `#/settings` – settings/dev surface.

**Aliases:**

* `#/dashboard` → `#/home`
* `#/items` → `#/inventory`
* `#/items/<id>` → `#/inventory/<id>`
* `#/vendors` → `#/contacts`
* `#/vendors/<id>` → `#/contacts/<id>`

**Deep-link guarantees:**

* Loading `#/inventory/<id>`, `#/contacts/<id>`, `#/recipes/<id>`, `#/runs/<id>`:

  * Must either show the entity or show an “Item/Contact/Recipe/Run not found” message and redirect to the relevant list.

* Invalid routes (e.g. `#/does-not-exist`) must show a 404/Not Found surface with a link back to `#/home`.

### 5.3 Sidebar navigation (0.9)

Primary left navigation items:

1. `Dashboard` → `#/home`
2. `Items` → `#/inventory`
3. `Vendors` → `#/contacts`
4. `Manufacturing → Recipes` → `#/recipes`
5. `Manufacturing → Runs` → `#/runs`
6. `Files / Import & Export` → `#/import`
7. `Settings` → `#/settings`

* The older “Tools drawer” pattern is treated as secondary; left nav is primary.

(Existing 5.6–5.10 sections on branding, inventory screen, contacts screen, etc., remain valid unless contradicted by the route/nav rules above; labels and routes must be updated to match.)

### 5.4 UI error-state contract (0.9)

#### 5.4.1 Non-2xx responses

* Any non-2xx API response **must** produce visible error UI:

  * No silent failures.
  * No “nothing happened” behavior after an API call.

#### 5.4.2 Validation vs. operational errors

* **Validation errors (HTTP 400):**

  * Descriptive message.
  * Dialogs/forms stay open.
  * Field-level errors when possible.
  * User can correct and retry.

* **Operational errors (5xx, timeouts):**

  * Treated as system-level failures.
  * Persistent error banner (e.g., “An unexpected error occurred. No changes were made.”).
  * Timeouts → explicit copy (“Request timed out. Check server status.”).
  * No auto-retry in 0.9.

#### 5.4.3 Error formats

UI error parser must handle:

* `{ "detail": "message" }`
* `{ "detail": "message", "fields": { ... } }`
* `{ "detail": [ { "msg": "...", "loc": [...], "type": "..." }, ... ] }`

Behavior:

* Prefer a `"detail"` string.
* If `"detail"` is a list, show bullet list.

#### 5.4.4 Stock-affecting operations

* Manufacturing runs, adjustments, stock-in/out, and imports are **atomic**:

  * If backend rejects the request, UI:

    * Shows blocking error.
    * Does **not** mutate any local quantities.

* No optimistic updates for stock values in 0.9.

#### 5.4.5 Manufacturing run failures

* Insufficient stock → HTTP 400 with per-component shortages.

* UI must:

  * Show per-component `required vs available`.
  * Keep run dialog open.

* No movements or stock changes applied.

#### 5.4.6 Missing entities

* Deep-linked entity not found → show clear error and redirect back to list.

#### 5.4.7 Error logging

* All errors log consistent console entry:

  * `BUSCORE_ERROR: <message>, endpoint=<url>, payload=<object>`

* Internal stack traces **never** show in visible UI.

(Other UI details from the original SoT — Home layout, quick action, inventory/contacts card behavior, branding, etc. — remain canonical unless explicitly superseded.)

---

## 6) Data, Journals & Analytics

### 6.1 DB is the single source of truth

* Authoritative state for items, batches, movements, manufacturing runs, vendors, contacts, and business profile is **only** in SQLite (`app.db`).
* Journals (`*.jsonl`) are **receipts**, not state.
* Journals are **never** read to compute:

  * quantities
  * valuations
  * batch state
  * manufacturing history

### 6.2 Journal files (0.9)

Canonical journal files:

* `inventory.jsonl` – all non-manufacturing stock-affecting actions:

  * purchases / stock-in
  * direct consumes (non-manufacturing)
  * adjustments
  * imports that affect stock

* `manufacturing.jsonl` – manufacturing runs (success + failure).

* `bulk_import.jsonl` – bulk import preview/commit.

* `plugin_audit.jsonl` – plugin-initiated actions.

No other journals are used in 0.9.

### 6.3 Write order & crash semantics

For stock-affecting operations:

1. Apply DB changes in a transaction.
2. If commit succeeds, append journal line.
3. If commit fails, **no** journal is written.

Crashes between commit and journal write may cause gaps; DB is still truth; audit may be incomplete. Acceptable.

### 6.4 Journal-based recovery

* 0.9 implements **no** journal replay or auto-repair.
* DB corruption is handled **only** via backup/restore.

### 6.5 Adjustments (as movements)

* Adjustments are **first-class movements**, not magic overrides.

**Positive adjustments** (“found stock”):

* Treated as new stock:

  * New batch with `qty_remaining = +N`.
  * `unit_cost_cents = 0` (zero-cost rule for found stock in 0.9).
  * Movement with `source_kind="adjustment"`, `qty_change=+N`, `is_oversold=0`.

**Negative adjustments** (“lost/damaged”):

* Behave like standard FIFO consume:

  * Walk FIFO batches.
  * Consume oldest first.
  * Record `unit_cost_cents` from each consumed batch.

* Constraints:

  * 400 if insufficient stock; no partial consumption.
  * `is_oversold=0` (no oversold from adjustments).

**Journaling:**

* Every adjustment writes an `inventory.jsonl` entry with:

  * `type: "adjustment"`
  * `item_id`
  * `qty_change`
  * `timestamp`
  * optional `reason`

**Append-only guarantee:**

* Adjustments must never:

  * directly rewrite `items.qty` or `item_batches.qty_remaining` outside ledger logic.
  * rewrite or delete historical movements.

---

## 7) Licensing Model (Core – Zero License)

### 7.1 Core licensing (0.8.1+)

**Core (this repo) operates with zero licensing logic:**

* No `license.json` file.
* No tier concept.
* No remote license checks.
* No license enforcement.
* No license-gated features.
* No "Pro", "Tier", "Plan", or "Upgrade" wording in UI or responses.

**What Core contains:**

* Items, vendors/contacts.
* Manufacturing recipes and one-off runs.
* Stock changes & basic inventory control.
* Local analytics and Insights from local DB only.
* Manual backups and restore.
* Manual file linking (receipts, SOPs, docs).

### 7.2 BUS Core Pro (separate project)

A separate commercial product (**BUS Core Pro**) exists in a separate repository:

* Proprietary license, paid product.
* Wraps the Core engine.
* Adds distribution, updates, installer, auto-updates, support, nicer launcher.
* May add acceleration and ergonomics (batch operations, automation/scheduling, multi-run pipelines, etc.).
* **No Pro-only logic lives in this public Core repo.**

**Principle:** Community must always be able to perform the same base operations manually, one at a time.

---

## 8) DB, Schema & Migrations (Behavioral)

### 8.1 App database (canonical 0.9)

A single SQLite **app database**:

* **Default path (Windows):** `%LOCALAPPDATA%\BUSCore\app\app.db`
  (when `BUS_DB` unset; one-time migration from repo `data/app.db` if present).
* **Override:** if `BUS_DB` is set, use that path.

Core bootstraps the following tables at startup:

* `vendors`
* `items`
* `tasks`
* `attachments`
* `item_batches`
* `item_movements`
* `recipes`
* `recipe_items`
* `manufacturing_runs`
* (plus internal tables for plans/event store when implemented)

**Measurement model:**

* Quantities: REAL (floats) for now.
* Money: INTEGER cents (e.g., `unit_cost_cents`, `total_value_cents`).
* The “×100 metric core” design remains **future**, not implemented.

(Per-table column details for `vendors`, `items`, `tasks`, `attachments` remain as in the v0.6 SoT; ledger and manufacturing fields added above are canonical.)

### 8.2 Plans database

Unchanged: separate `plans.db` in `<APP_DIR>/plans.db` with `plans` table as previously documented.

---

## 9) Vendors & Contacts (Unified Model)

(As in v0.6 SoT; still canonical)

* `vendors` holds organizations and people.
* Contacts API: `/app/contacts` facades onto `vendors`.
* Duplicate name POST merges into existing vendor with `role='both'` and merged `meta`.

(Existing contact UI rules for expanded-only mutating actions and structured `meta.email`/`meta.phone` remain.)

---

## 10) Testing & Smoke Harness (0.9)

* **Canonical launcher:** `scripts/launch.ps1`
* **Canonical smoke:** `scripts/smoke.ps1`
* Smoke must exit **0** on success, **1** on any failure.

### 10.1 Auth & health in smoke

* Auth: **cookie-based** session via `GET /session/token`.
* Smoke does **not** use header tokens.
* Health:

  * `/health` must return `{ "ok": true, "version": "<APP_VERSION>" }`.
  * `/health/detailed`:

    * Returns 404 unless `BUS_DEV=1`.
    * When `BUS_DEV=1`, may include extra diagnostic fields.

### 10.2 Required smoke stages (high-level)

1. **Session + health:**

   * `/session/token`, `/health`
   * Optionally check `/health/detailed` behavior (404 vs diagnostics under `BUS_DEV=1`).

2. **Item CRUD:**

   * Create/edit/archive items via `/app/items`.

3. **Contacts/Vendors:**

   * Create vendor/contact via `/app/contacts`.
   * Link item to vendor.

4. **FIFO stock-in:**

   * Create two cost layers (e.g. 10 @ 300¢, 5 @ 500¢) via purchases and ensure batches/movements reflect FIFO state.

5. **FIFO consumption:**

   * Consume across layers (e.g. 12 units) and assert:

     * Remaining 3 units @ 500¢ = 1500¢.
     * Correct number of movement rows.

6. **Recipe manufacturing – success:**

   * Define recipe R for output item C.
   * Run once; assert:

     * Required components consumed via FIFO.
     * New batch for output item created.
     * Output unit cost = total FIFO component cost consumed / output_qty.

7. **Manufacturing failure:**

   * Attempt run requiring more than available stock:

     * Assert 400 with per-component shortages.
     * Assert no movements written.
     * Assert `manufacturing_runs.status="failed_insufficient_stock"`.

8. **Adjustments:**

   * Positive:

     * New zero-cost batch.
     * Positive movement recorded.

   * Negative:

     * FIFO consume.
     * Fails with 400 when insufficient stock; no partial; no oversold.

9. **Backup & restore:**

   * Export current DB with password.
   * Mutate DB.
   * Restore from backup.
   * Assert:

     * DB matches pre-mutation state.
     * Journals archived and reset (see §11.4).

10. **Launcher mechanics (manual/assisted):**

    * Start server, check tray behavior, restart, quit.

11. **Integrity checks:**

    * Verify:

      * no negative quantities,
      * no unexpected oversold,
      * no orphan FKs where constraints exist.

**Journals asserted in smoke:**

* After stock-in/consume → `inventory.jsonl` has ≥2 lines.
* After manufacturing run → `manufacturing.jsonl` has ≥1 line.

---

## 11) Operations, Backup & Restore (0.9)

### 11.1 GitHub & acceptance workflow

(As in v0.6 SoT, unchanged:)

1. All code is canonical on GitHub.
2. For acceptance:

   * Download ZIP.
   * Unzip to fresh dir.
   * Run `scripts/launch.ps1`.
   * Run `scripts/smoke.ps1`.
   * Acceptance = all smoke checks pass.

### 11.2 Runtime paths (Windows)

* **DB:** `%LOCALAPPDATA%\BUSCore\app\app.db` (default, see §3).

* **Exports / backups:** `%LOCALAPPDATA%\BUSCore\exports`.

* **Config:** `%LOCALAPPDATA%\BUSCore\config.json`.

* **Reader settings:** `%LOCALAPPDATA%\BUSCore\settings_reader.json`.

* **Journals:** `%LOCALAPPDATA%\BUSCore\app\data\journals\*.jsonl`
  (exact subdirectory naming may vary; journal roles are defined in §6).

* **Index state:** `data/index_state.json` (under app working dir) as before.

### 11.3 Backup & restore (DB only)

Backups are **encrypted copies of `app.db` only.**

* **Export (backup):** `POST /app/export-db`

  * Reads current `app.db`.

  * Encrypts DB into a container using AES-GCM with a **user-provided password**.

  * Password → key via KDF (PBKDF2/Argon2id).

  * Writes file to `backup.default_directory` from config:

    * Default: `%LOCALAPPDATA%\BUSCore\exports`.

  * Does not modify DB or journals.

* **Preview:** `POST /app/import-preview`

  * Decrypts backup with supplied password.
  * Validates schema version.
  * Returns metadata (schema version, high-level counts).
  * No writes.

* **Commit:** `POST /app/import-commit`

  * Decrypts backup to temp file.
  * Atomically replaces current `app.db` with restored DB.
  * Signals that restart is required.

**Schema compatibility:**

* Restore must **refuse** backups with incompatible schema version.
* Error message must clearly state mismatch.

### 11.4 Journal behavior on restore

On successful restore:

* Existing journals are **archived** by renaming:

  * `inventory.jsonl` → `inventory.jsonl.pre-restore-<timestamp>`
  * `manufacturing.jsonl` → `manufacturing.jsonl.pre-restore-<timestamp>`
  * `bulk_import.jsonl` → `bulk_import.jsonl.pre-restore-<timestamp>`
  * `plugin_audit.jsonl` → `plugin_audit.jsonl.pre-restore-<timestamp>`

* Fresh empty journal files are created with the original names.

This prevents confusion between logs and DB state, while preserving historical logs.

### 11.5 Crash & corruption rules

* DB corruption is not auto-repaired.
* No journal replay fallback.
* Backups are local artifacts; retention is user-managed.

### 11.6 Config & launcher integration

* **Config path:** `%LOCALAPPDATA%\BUSCore\config.json`.

**Schema (0.9):**

```json
{
  "launcher": {
    "auto_start_in_tray": false,
    "close_to_tray": false
  },
  "ui": {
    "theme": "system",              // "light", "dark", "system"
    "experimental_flags": []        // dev-only, manual edit only
  },
  "backup": {
    "default_directory": "%LOCALAPPDATA%\\BUSCore\\exports"
  },
  "dev": {
    "writes_enabled": false         // dev-only, set via /dev/writes
  }
}
```

* Unknown fields ignored; missing fields defaulted.

**Reader settings** remain separate (`settings_reader.json`) and are not part of `config.json`.

**Launcher behavior (Windows):**

* On startup:

  * Reads `config.json`.
  * Starts server at `127.0.0.1:8765`.
  * Shows tray icon.
  * If `auto_start_in_tray=false` → opens browser to `/ui`.
  * If `auto_start_in_tray=true` → no initial browser window.

* Tray menu (minimum):

  * Open BUS Core (open default browser to UI).
  * Restart BUS Core (stop + start server).
  * Open Backup Folder (open `backup.default_directory`).
  * Quit BUS Core (stop server + tray).

* Window close:

  * `close_to_tray=true` → hide to tray; keep server running.
  * Else → fully quit.

**Config writes:**

* UI updates config via `POST /app/config`.
* Server writes `config.json` and returns `{ "restart_required": true }`.
* Server reads config only on startup; does not mutate config outside `/app/config`.

**Dev flag persistence:**

* `BUS_DEV` is strictly an environment variable.
* It is **not** writable from UI and **not** stored in `config.json`.

### 11.7 Business profile

* `/app/business_profile` stores business details in DB, not config.
* Business profile is included in backups and restored normally.

---

## 12) Dev Mode & Security Gating

### 12.1 Dev flag

* `BUS_DEV` is the **only** dev-mode flag.
* `BUSCORE_DEBUG_DB` and similar legacy flags are **removed**.
* `BUS_DEV=1` ⇒ dev mode on; any other value/unset ⇒ production.

### 12.2 `/health` vs `/health/detailed`

* `/health`:

  * Always available.
  * Returns minimal:

    ```json
    { "ok": true, "version": "<APP_VERSION>" }
    ```

* `/health/detailed`:

  * Returns 404 unless `BUS_DEV=1`.
  * When `BUS_DEV=1`, may include additional diagnostic fields:

    * `schema_version`, `tier`, DB path, counts, warnings, etc.
    * Fields must be documented once finalized.

### 12.3 `/dev/*` endpoints

* All `/dev/*` endpoints:

  * Require valid session (no auth bypass).
  * Return 404 unless `BUS_DEV=1`.

* `/dev` endpoints may:

  * expose schema, journals, internal metrics, flags.
  * mutate **dev metadata only** (e.g., `config.dev.writes_enabled`).

* `/dev` endpoints **must not** modify:

  * `items`
  * `item_batches`
  * `item_movements`
  * `manufacturing_runs`

(business data stays untouched by dev helpers).

---

## 13) Repository Hygiene & Legal

(As in v0.6 SoT; still canonical.)

* AGPL-3.0 license with SPDX headers.
* Root logo files `Flat-Dark.png`, `Glow-Hero.png` are special-cased (tracked, no LFS).
* `.gitignore` and `.gitattributes` rules unchanged except for any adjustments needed to reflect new binary paths.

---

## 14) Unknowns / Not Specified (0.9)

Still **not specified** / open:

* Exact analytics event store table name and index strategy (only shape/usage described).
* Final pinned `pip` version and full Python version support matrix.
* Detailed offline/cached install design for dependencies.
* Exact `/health/detailed` payload schema (beyond minimal description in §12.2).
* Pre-commit tooling for SPDX enforcement (launcher warning exists; hook TBD).
* Phone number normalization format (raw vs E.164).
* Mac/Linux packaging/launcher behavior (Windows is primary).
* Final decision on legacy `/app/transactions*` routes vs pure ledger-only flows.

Anything not explicitly documented above remains **“Not specified in the SoT”**.

---

## 15) BUS Core Pro (Separate Commercial Project)

This section describes BUS Core Pro at a conceptual level for reference. **Implementation is outside this repo and outside the scope of the Core codebase.**

### 15.1 Product & relationship

* **Core:** Free, AGPL, open-source. Built from this repo. DIY build/install.
* **Pro:** Paid, proprietary, separate repo & installer. Wraps Core engine. Adds distribution, updates, UX layer (installer, auto-updates, support, nicer launcher). No Pro-only logic lives in this public Core repo.

### 15.2 Pricing & updates (reference)

* Target initial price: **~$99 USD one-time** (launch promo ~ $79).
* Includes: Pro app, 1 year of feature updates, 1 year of email support.
* Optional renewal: ~ $49/year to extend updates + support.

**Perpetual rights:**

* If renewal lapses, user keeps access to the latest version released during their active window forever.
* No hard lockout; app continues working offline.

### 15.3 License model (Pro only, separate repo)

* Offline license file `buscore.lic`.
* Location: `%LOCALAPPDATA%\BUSCore\buscore.lic`.
* Signed with private key; app verifies with public key (offline).
* DRM stance: trust-based, no hardware binding, no call-home required for normal operation.

### 15.4 Updates & access (reference)

* Active (paid-up) licenses can download latest Pro build.
* After expiry: user keeps access to all versions released during their active window.
* Security-only patches remain available to all licensed users regardless of expiry.

### 15.5 Accounts & identity (reference)

* Magic-link login (email only) for Pro account portal.
* Minimal profile: re-download links, license recovery.
* Payments via external provider (Stripe/Lemon Squeezy); no payment details stored.

### 15.6 Support & refunds (reference)

* Support target: respond within **2 business days**.
* Support included for duration of updates window.
* Refund policy: all sales final (license files non-revocable), subject to jurisdiction-mandated consumer rights.

---

**End of Source of Truth (v0.8.2 "Manufacturing Locked").**

[DELTA HEADER]
SOT_VERSION_AT_START: v0.8.2
SESSION_LABEL: v0.8.3 backup/restore & journals hardening – 2025-12-06
DATE: 2025-12-06
SCOPE: backend, api, db, windows, journaling, backup-restore, smoke
[/DELTA HEADER]

(1) SESSION FACTS / NOTES (EXHAUSTIVE)

* Launch/entrypoint:

  * Canonical uvicorn target is `core.api.http:create_app` with `--factory`.
  * Scripts export `PYTHONPATH` to repo root before launch.
  * PowerShell requirement is Windows PowerShell 5.1 (no `pwsh` 7+).
* Windows deps & platform specifics:

  * `pywin32` is required (e.g., `win32con`) for Windows named pipes.
  * `core/broker/pipes.py` is Windows-only; import guarded; meaningful error on non-Windows.
* Auth/session & docs:

  * Smoke and API use cookie-based session via `GET /session/token` (no custom header).
  * `/openapi.json` and docs are accessible (not gated by auth).
* Journaling (v0.8.3 scope):

  * Rule: **DB commit → then journal append** (never reverse).
  * Sinks wired for `inventory.jsonl` and `manufacturing.jsonl`.
  * On restore, existing `*.jsonl` files are archived to `*.pre-restore-<timestamp>`; fresh `inventory.jsonl` and `manufacturing.jsonl` are recreated empty.
* Encrypted backup/export:

  * AES-GCM encrypted DB exports write to `%LOCALAPPDATA%\BUSCore\exports`.
  * Smoke validates the export path under that root, case/ slash insensitive, PS 5.1-safe.
  * Smoke verifies exported file exists and is non-empty, then cleans it up at end.
* Restore preview:

  * `/app/db/import/preview` returns `table_counts`; absence of a `version` field is tolerated.
  * Schema check runs before commit.
* Restore commit (Windows reliability fixes):

  * New helper `core/backup/restore_commit.py` provides:

    * `wal_checkpoint(path)` to flush WAL/SHM.
    * `same_dir_temp(dir, prefix)` to ensure same-drive temp for atomic replace.
    * `close_all_db_handles(dispose_call)` to dispose SQLAlchemy engine and force-close stray `sqlite3.Connection` via GC sweep; includes quiet delay.
    * `atomic_replace_with_retries(src, dst)` with (extended) retries, exponential backoff + jitter; handles WinError 32/33 and EACCES/EBUSY.
    * `archive_journals(dir, ts)` to rename `*.jsonl` and recreate primaries.
  * Commit route sequence:

    * Acquire exclusive `app.state.restore_lock`; set `app.state.maintenance = True`.
    * Decrypt backup to **same directory** temp DB.
    * `wal_checkpoint(app.db)` then **dispose engine** and perform **two GC sweeps** to close all handles.
    * Atomic `os.replace(tmp, app.db)` with robust retry.
    * Archive journals and recreate primaries.
    * Respond `{ ok: true, replaced: true, restart_required: true }`.
  * App-level maintenance guard:

    * Middleware 503s all non-allowed endpoints during maintenance.
    * Allowlist includes `/session/token`, `/openapi.json`, `/app/db/import/preview`, `/app/db/import/commit`.
  * DB session dependency (`get_db`) rejects session creation during maintenance (503).
* FastAPI route signatures:

  * Removed `Optional[Request]` / `Request|None` from route/dependency parameters; `Request` is required and non-optional.
* Smoke harness (PS 5.1-safe):

  * Uses shared `WebRequestSession` (cookies) and no custom headers.
  * Export root check uses canonical full paths with case-insensitive prefix; parentheses prevent stray `+` in output.
  * Stage 6 flow: export → reversible mutation → preview → commit → verify state reverted → journals archived/recreated → cleanup.
* Outcome:

  * All smoke stages pass end-to-end on Windows; Stage 6 commit succeeds and signals `restart_required`.
  * Version target for release/tag is `v0.8.3`.
  * SPDX header tool available; repo reported missing headers prior to fix pass.

(2) NEW FACTS / DECISIONS vs SoT

* Not computed: SoT text not provided in this session.

(3) CHANGES TO EXISTING FACTS (SoT → session)

* Not computed: SoT text not provided in this session.

(4) CLARIFICATIONS / TIGHTENING

* Not computed: SoT text not provided in this session.

(5) CONFIRMED / RESTATED (NO CHANGE)

* Session restatement: Cookie-based session via `/session/token`; no custom header required — confirmed by smoke and middleware behavior.
* Session restatement: AES-GCM encrypted export root is `%LOCALAPPDATA%\BUSCore\exports` — validated by smoke path assertion.
* Session restatement: Journals are receipts; on restore, archive existing journals and recreate primaries — exercised and verified in Stage 6.
* Session restatement: Manufacturing invariants (fail-fast, atomicity, oversold protection) hold — revalidated by smoke.

(6) OPEN QUESTIONS / UNRESOLVED / UNCERTAIN

* Question: Post-restore lifecycle — should the service auto-restart when `restart_required:true`, or is restart a UI/launcher responsibility?
  Context: Commit returns `restart_required:true`; current smoke only asserts flag.
* Question: Cross-platform semantics — do Linux/macOS paths and file locking need equivalent handling (e.g., maintenance guard remains, but retry/backoff tuned)?
  Needs: Cross-platform test run and path roots for non-Windows.
* Uncertain: Finalization tasks for release — version bump applied everywhere, SPDX headers added, and CHANGELOG updated?
  Needs: Confirmed commits and tag `v0.8.3` pushed.

[DELTA HEADER]
SOT_VERSION_AT_START: v0.8.3
SESSION_LABEL: v0.8.4 dev-gating & ui-auth hardening – 2025-12-06
DATE: 2025-12-06
SCOPE: backend, api, security, ui, smoke
[/DELTA HEADER]

(1) SESSION FACTS / NOTES (EXHAUSTIVE)

* Dev/Prod Gating (Milestone 0.8.4):
  * Centralized `is_dev()` check; strict rule: only `BUS_DEV="1"` enables dev mode.
  * In Production (`BUS_DEV != "1"`):
    * `/dev/*` routes return 404 (Not Found).
    * `/health/detailed` returns 404.
    * Exception responses are sanitized: return `{"detail": {"error": "bad_request"}}` or `internal_error` with no stack traces or path leaks.
  * In Dev (`BUS_DEV="1"`):
    * `/dev/*` routes are accessible but require valid session auth.
    * Full exception details/tracebacks pass through.
* Authentication Hardening:
  * Backend strictly enforces Cookie-only authentication (`bus_session`).
  * Support for `X-Session-Token` header explicitly removed from `core/api/http.py`.
  * Public prefixes tightened: `/dev/` removed from public list (now requires auth middleware).
* Feature Unlocking:
  * Runtime write toggling via `POST /dev/writes` is removed.
  * `require_write_access` returns generic 403 if writes are disabled.
  * Frontend elements for toggling writes removed.
* Frontend (UI):
  * `token.js` updated to use `credentials: 'same-origin'` to correctly persist and send the session cookie.
  * Dead calls to `/dev/writes` (polling) and `/app/business_profile` (non-existent endpoint) removed to fix 401/404 log errors.
* Smoke Test Harness:
  * Updated to use cookie-based authentication (via `requests.Session` or manual cookie jar).
  * Added **Stage 7: Cleanup**:
    * Zeroes out inventory for test items (A, B, C).
    * Archives/deletes test recipes and items to leave DB clean.

(2) NEW FACTS / DECISIONS vs SoT

* `BUS_DEV` environment variable value strictly defined as `"1"` (string) to enable dev mode.
* Production error responses are explicitly sanitized to prevent information leakage.
* Smoke harness now includes a self-cleanup stage (Stage 7).

(3) CHANGES TO EXISTING FACTS (SoT → session)

* Old (SoT): Smoke and API use cookie-based session via `GET /session/token` (no custom header).
  New (session): Code updated to *strictly* enforce this; previous support for `X-Session-Token` header (found in code but not SoT) was removed to align with SoT.
* Old (SoT): Implied existence of write-toggling mechanism.
  New (session): `POST /dev/writes` removed; dev endpoints are for diagnostics only, not feature unlocking.

(4) CLARIFICATIONS / TIGHTENING

* SoT vague on `BUS_DEV` values → clarified as strict `"1"` only.
* SoT implied UI authentication flow → clarified/fixed in `token.js` to explicitly require `credentials: 'same-origin'` to function with the strict cookie backend.

(5) CONFIRMED / RESTATED (NO CHANGE)

* SoT says: Cookie-based session via `/session/token`.
  Session: Explicitly confirmed and hardened; UI fixed to adhere to this.
* SoT says: Journals are receipts... verify state reverted.
  Session: Confirmed via Smoke Stage 6 passing in `v0.8.4` environment.

(6) OPEN QUESTIONS / UNRESOLVED / UNCERTAIN

* Question: Is there a canonical endpoint for `/app/business_profile` planned?
  Context: UI was calling it, causing 404s. Call suppressed for now.
