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
  
  [DELTA HEADER]
SOT_VERSION_AT_START: v0.8.4
SESSION_LABEL: v0.8.5 Desktop Lifecycle & Launcher – 2025-12-06
DATE: 2025-12-06
SCOPE: launcher, config, ui, dependencies
[/DELTA HEADER]

(1) SESSION FACTS / NOTES (EXHAUSTIVE)
- **Dependency Updates:** `requirements.txt` updated to explicitly include `requests`, `pystray`, `Pillow`, `pywin32` (Windows only), `fastapi`, `uvicorn`, `jinja2`, `aiofiles`, `python-multipart` to resolve runtime crashes.
- **Config Implementation:** `core/config/manager.py` created to manage `%LOCALAPPDATA%\BUSCore\config.json`.
- **Config API:** `GET /app/config` and `POST /app/config` endpoints implemented; POST returns `{"restart_required": true}`.
- **Launcher Modes (Dual-Mode):**
  - **Dev Mode (`BUS_DEV="1"` or `--dev`):** Runs `uvicorn` in blocking mode; console window remains visible; system tray disabled.
  - **Production Mode (Default):**
    - Console window is programmatically hidden on startup (using `ctypes` `SW_HIDE`).
    - `uvicorn` runs in a daemon thread.
    - System Tray icon (`pystray`) launches and blocks the main thread.
    - Browser opens in a standard new tab (via `webbrowser.open`) pointing to `/ui/shell.html#/home`.
- **Tray Functionality:**
  - Menu items: "Open Dashboard", "Show Console" (unhides window for debug), "Quit BUS Core" (forces `os._exit(0)`).
  - Icon: Loads `Flat-Dark.png` or falls back to a generated colored block if missing.
- **Browser Behavior:** Explicitly rejected "App Mode" (`--app` flag); launcher opens default system browser as a standard tab.
- **Settings UI:** Settings card updated to read/write `launcher` and `ui` config sections via new API.

(2) NEW FACTS / DECISIONS vs SoT
- **Stealth Launch Mechanism:** Production mode explicitly hides the host console window on Windows using `ctypes.windll.user32.ShowWindow`, behavior not previously detailed in SOT architecture.
- **CLI Argument:** Added `--dev` argument to `launcher.py` which sets `os.environ["BUS_DEV"] = "1"` internally, providing an explicit CLI trigger for dev mode alongside the environment variable.
- **Console Recovery:** Added "Show Console" option to System Tray menu to allow recovering the hidden console for debugging in production mode.

(3) CHANGES TO EXISTING FACTS (SoT → session)
- Old (SoT): [Implied] Launcher runs as a standard script, visible console.
  New (session): Launcher defaults to "Stealth Mode" (hidden console) unless explicitly gated into Dev Mode.
- Old (SoT): [SOT §11.6] Config schema defined.
  New (session): Config schema implemented exactly as defined in SOT §11.6.

(4) CLARIFICATIONS / TIGHTENING
- SoT §12.1 says "BUS_DEV is the only dev-mode flag" → clarified as: Launcher accepts `--dev` argument which *sets* this flag, remaining compliant while adding ergonomics.
- SoT §11.6 "Launcher behavior... if auto_start_in_tray=false -> opens browser" → tightened as: Opens browser in standard tab (not app mode/popup).

(5) CONFIRMED / RESTATED (NO CHANGE)
- SoT says: Config path is `%LOCALAPPDATA%\BUSCore\config.json`.
  Session: Explicitly confirmed and implemented in `core/config/manager.py`.
- SoT says: Config schema structure (`launcher`, `ui`, `backup`, `dev`).
  Session: Explicitly implemented in `core/config/manager.py` defaults.
- SoT says: `BUS_DEV=1` ⇒ dev mode on; any other value/unset ⇒ production.
  Session: Validated and enforced in `launcher.py` logic.

(6) OPEN QUESTIONS / UNRESOLVED / UNCERTAIN
- Uncertain: Handling of `Flat-Dark.png` path resolution in frozen/PyInstaller environments vs raw script execution (fallback generation logic added as safeguard).

[DELTA HEADER]
SOT_VERSION_AT_START: v0.8.2 "Manufacturing Locked" 
SESSION_LABEL: Error-UX & Windows restore reliability hardening – 2025-12-08 PM
DATE: 2025-12-08
SCOPE: backend, api, smoke, windows, restore, ui-error
[/DELTA HEADER]

(1) SESSION FACTS / NOTES (EXHAUSTIVE)

* Smoke harness: all stages pass locally; Stage 8 (encrypted backup/restore) completes with `{ ok:true, replaced:true, restart_required:true }`. 
* Manufacturing 400-failure payloads are now parsed by smoke; payload includes message `"Insufficient stock for required components."` and a `shortages` object; ad-hoc runs follow the same rule.
* `/app/db/import/commit` requires the cookie session; attempting without the cookie yields `401 Unauthorized`. Smoke now reuses the same cookie it obtained from `GET /session/token`. 
* Windows restore reliability: commit sequence instrumented and enforced to (a) stop/pause background indexer, (b) WAL checkpoint, (c) dispose/GC DB handles, (d) atomic replace with retries, (e) archive/recreate journals; failure mode `exclusive_timeout:win32=32` is surfaced as 400 when exclusive handle cannot be obtained. 
* Maintenance window: during restore commit the app enters maintenance and only an allowlist is reachable; DB session creation is blocked by dependency guard while in maintenance. 
* Error-UX intent: non-2xx responses must be visible in UI; 400 keeps dialogs open with field errors when possible; 5xx/timeout shows persistent banner; UI error parser supports string and list shapes. (Validated by smoke behavior and server payloads.)  
* Journals: on successful commit, existing journals are archived with timestamp suffix and primaries recreated empty. 

(2) NEW FACTS / DECISIONS vs SoT

* Restore commit explicitly **stops/pauses the background indexer** before handle disposal and file replace; indexer is resumed after commit or failure. (SoT listed maintenance guard and DB handle disposal but did not specify indexer pause.)
* Commit failure codes are **standardized** to include `exclusive_timeout` (with OS code, e.g., `win32=32`) in the `detail.info` string for diagnostics.

(3) CHANGES TO EXISTING FACTS (SoT → session)

* Old (SoT): Commit route sequence flushes WAL, disposes engine, atomically replaces DB, archives journals; maintenance guard blocks non-allowlisted routes. 
  New (session): Same as SoT **plus**: explicit **indexer stop/pause** around commit to reduce lock contention and avoid `WinError 32` stalls.

(4) CLARIFICATIONS / TIGHTENING

* SoT vague on **auth during maintenance** → clarified as: allowlisted endpoints remain **auth-protected**; `/app/db/import/commit` still requires the **cookie** session set via `GET /session/token` (no custom header).  
* SoT ambiguous about **manufacturing 400 message** → clarified as: canonical message string used by server is `"Insufficient stock for required components."`, and payload includes `shortages` per component (UI shows required vs available). 

(5) CONFIRMED / RESTATED (NO CHANGE)

* SoT says: **Cookie-based session via `GET /session/token`**, no custom header; `/openapi.json` is not gated. Session: exercised by smoke; cookie is required for protected routes. 
* SoT says: **Restore preview** returns `table_counts`; absence of a `version` field is tolerated. Session: exercised and confirmed. 
* SoT says: On **restore commit**, perform WAL checkpoint, dispose DB handles, atomic replace with retries, **archive journals** and recreate primaries; response signals `restart_required:true`. Session: exercised and confirmed end-to-end. 
* SoT says: **UI error contract** – all non-2xx surface visible errors; 400 vs 5xx rules; error shapes accepted. Session: validated by smoke and API behavior. 

(6) OPEN QUESTIONS / UNRESOLVED / UNCERTAIN

* Question: Should the **indexer pause/resume** be exposed as an app-level state for UI (e.g., maintenance banner) or remain server-internal only?
  Needs: Decision on UX signal during commit.
* Uncertain: Do we want to **bound** the overall commit attempt duration (e.g., ≤ N seconds) and return a consistent `exclusive_timeout` envelope, or retain extended backoff under heavy IO?
  Needs: Target SLO for restore commit latency on Windows HDD vs SSD.

[DELTA HEADER]
SOT_VERSION_AT_START: v0.8.8
SESSION_LABEL: Integer metric inventory + recipes/manufacturing UI and smoke hardening
DATE: 2025-12-11
SCOPE: db, api, inventory, recipes, manufacturing, ui, smoke, ops
[/DELTA HEADER]

(1) SESSION FACTS / NOTES (EXHAUSTIVE)

* DB / Schema (fresh-create only)

  * All inventory-related quantities are stored as INTEGER base units (no floats).
  * `items.dimension` added: one of `length|area|volume|weight|count` (required).
  * Base units: length=mm, area=mm², volume=mm³ (ml==cm³), weight=mg, count=milli-units (1 ea == 1000).
  * Fresh-DB bootstrap only; migrations disabled for this work. Developer deletes AppData between schema changes.
  * `recipes.archived` exists; default false.
* Metric Core

  * Central conversion map for each dimension; UI and API use it.
  * Rounding uses Decimal with ROUND_HALF_UP when converting user decimals → base ints.
  * Default count unit label = `ea` (maps to milli-counts).
* API behaviors

  * Item create/update requires `dimension` and accepts `{dimension, unit, quantity_decimal}`; server stores base `quantity_int`.
  * Movements/ledger quantities are ints; negative allowed where appropriate.
  * Recipe payload shape uses `items[].optional` (boolean) and **does not** use `output_qty`.
  * Recipe delete endpoint returns success and is now wired in UI with confirm→delete→refresh.
* Inventory UI

  * Table columns (ordered, centered, evenly spaced): `Name | Quantity | Price | Vendor | Location`.
  * `Quantity` shows **sum of active batches** (active := `qty_remaining > 0`) rendered in the item’s chosen unit (not base units).
  * Expanded item view shows batches (remaining/created-at) without duplicating the quantity summary.
  * Item edit dialog includes **Add Batch** flow; initial item add no longer fakes a batch.
* FIFO & Pricing

  * FIFO price shown in list is the unit cost of the **next** quantity to be consumed (oldest active batch).
* Recipes UI

  * Output item selection persists correctly; no “output count” input (single-run UI).
  * New recipe defaults: `archived = false`; input item `optional = false`.
  * “Add input item” dropdown starts blank; selections persist on reload.
  * “Items” section retitled **“Input Items”**; `sort` column removed.
  * “Remove” per input item is a small red “X”.
  * `code` field removed from the form; reserved for future use (no functional effect now).
  * Delete button fixed: confirm dialog → DELETE call → row removed / list refreshed.
* Manufacturing

  * UI triggers a single-output run for the selected recipe (no user-entered output quantity).
  * Backend semantics unchanged (atomicity, FIFO, validations).
* Smoke test harness

  * Kept all original steps/prints/checks.
  * Updated recipe payload shape (no `output_qty`; use `optional`).
  * If manufacturing returns `insufficient_stock` (400), smoke auto top-ups missing quantities via `/app/adjust` and retries once; otherwise fails.
  * End-to-end smoke passed with all sections green (including backup/restore, journals, invariants).
* Ops / runtime

  * Fresh DB on each run; bootstrap creates schema with new fields/types.
  * Prior errors encountered and addressed during dev: missing columns (e.g., `is_product`, `archived`), NameError for `func` import, and 404s for old ledger endpoints; resolved in-session.
  * Non-blocking: indexer logs “Drive/Local AttributeError” remain; not in current scope.

(2) NEW FACTS / DECISIONS vs SoT

* All inventory quantities are stored as INTEGER base units with explicit `dimension` on items.
* Count dimension uses milli-units for fractional counts; UI label `ea` maps to base=1000.
* UI Inventory table shows aggregated on-hand per item (sum of active batches) in the item’s unit, plus FIFO price.
* Recipes: remove `output_qty` concept from UI/API payloads; recipe has a single `output_item_id`.
* Recipes UI: default `archived=false`, input `optional=false`, blank default selectors, “Input Items” title, no `sort` column, red “X” remove, working Delete with confirm.
* Manufacturing UI: single-output run (no output multiplier input).
* Smoke harness: introduces automatic top-up-on-400-INSUFFICIENT_STOCK with a single retry; otherwise identical flow.

(3) CHANGES TO EXISTING FACTS (SoT → session)

* Old (SoT): Inventory quantities stored as REAL (floats) without enforced base units; `dimension` not required.
  New (session): All quantities are INTEGER base units; `items.dimension` is required (length/area/volume/weight/count).
* Old (SoT): Recipes included `output_qty` and ambiguous optional flags/sort semantics.
  New (session): `output_qty` removed; input rows use `optional` only; `sort` removed from UI; `archived` explicitly managed and defaults to false.
* Old (SoT): Inventory list did not guarantee aggregated quantity from active batches nor FIFO price surface.
  New (session): List shows sum of active batches and FIFO price (next-to-consume unit cost) per item.
* Old (SoT): Manufacturing UI allowed specifying output quantity.
  New (session): Manufacturing UI enforces single-run output per execution (no numeric output input).

(4) CLARIFICATIONS / TIGHTENING

* “Active batch” is defined as `qty_remaining > 0` for aggregation and FIFO pricing.
* Display unit per item: use the unit selected at item creation/edit for UI display; storage remains base ints.
* Count unit label standardized to `ea`; conversion = 1000 base units per 1 ea.
* Recipe delete UX: requires user confirm; success removes the recipe from the list without page reload.
* `code` field in recipes is reserved (hidden in UI); no current functional semantics.

(5) CONFIRMED / RESTATED (NO CHANGE)

* FIFO consumption and pricing semantics remain unchanged; confirmed during consume and manufacturing tests.
* Manufacturing validations (fail-fast on insufficient stock, atomic movement creation) remain as specified; verified by smoke invariants.
* Encrypted backup/restore flow (export, preview, commit, journal archiving/recreate) operates as previously specified; reconfirmed via smoke.

(6) OPEN QUESTIONS / UNRESOLVED / UNCERTAIN

* Indexer warnings (`Drive`/`Local` AttributeError) at startup: out of scope; needs triage to confirm if any feature depends on the indexer.
* Persisting a preferred **display unit** per item: currently implied by last selection; consider explicit `items.display_unit` to avoid ambiguity.
* Logs page (System → Logs) and “available later” `code` field semantics for recipes: define future behavior and constraints when scheduled.

[DELTA HEADER]
SOT_VERSION_AT_START: v0.8.8
SESSION_LABEL: INT FIFO, UI polish, Logs (ledger-only) & Stock-Out – 2025-12-11
DATE: 2025-12-11
SCOPE: backend, api, db, ui, logs
[/DELTA HEADER]

(1) SESSION FACTS / NOTES (EXHAUSTIVE)

* Ledger & quantities

  * Canonical ledger path is SQLAlchemy/ORM with base-unit **INT** quantities; consumption is **FIFO**.
  * Legacy sqlite/REAL FIFO codepaths removed; no REAL-typed tables remain.
  * Linux crash fixed by importing `Item` in `ledger_api.py` for `db.get(Item, ...)`.
* Inventory endpoints (INT + FIFO)

  * `/app/purchase`: creates FIFO batch; after commit appends inventory journal line.
  * `/app/consume`: FIFO consume; returns batch breakdown; after commit appends journal (aggregate).
  * `/app/adjust`: positive = add batch 0-cost; negative = FIFO consume; journals on success only.
* Manufacturing

  * Manufacturing run works against INT+FIFO; journaling added to include `recipe_id` and `recipe_name`.
  * UI shows **Recent Runs (30d)** with columns `Recipe | Date | Time`; defaults to ~10 rows, panel is resizable; maps names via `recipe_name` (journal) with dropdown/GET fallbacks.
  * Manufacturing UI changes: removed top “Manufacturing” H1, renamed card to **New Manufacturing Run**, removed **Multiplier**, confirmation dialog before “Run Production”.
* Logs (beta scope = stock changes only)

  * New **/app/logs** endpoint implemented to **read from `item_movements`** only (ledger-as-truth), newest-first; supports cursor pagination via `cursor_id`.
  * Logs UI calls `/app/logs`, renders `Date/Time | Domain | Summary`; no journal reading required.
  * Cross-platform journals dir helpers standardized (still used for receipts), but **Logs page** does not depend on JSONL.
* Stock Out (new capability)

  * New endpoint `/app/stock/out` to remove stock via FIFO with reason enum `{sold, loss, theft, other}` and optional note; persists via FIFO consume; journals aggregate line; appears in Logs as inventory event with `kind = reason`.
* Misc UI/UX

  * Recent runs and logs pages refresh after actions; error handling surfaces server 400 payloads (e.g., shortages).

(2) NEW FACTS / DECISIONS vs SoT

* Added endpoint: `POST /app/stock/out` with fields `{item_id:int, qty:int>0, reason: 'sold'|'loss'|'theft'|'other', note?:string}`; performs FIFO consume; returns lines and journals aggregate entry.
* Implemented `/app/logs` (ledger-driven): returns `events[]` from `item_movements` with `{id, ts, domain:'inventory', kind:source_kind, item_id, item_name, qty_change, unit_cost_cents, batch_id, is_oversold}` and `next_cursor_id`.
* Manufacturing UI: removed H1, renamed card to **New Manufacturing Run**, removed **Multiplier**, added run confirmation.
* Recent Runs UI: right panel titled **Recent Runs (30d)**; shows columns `Recipe | Date | Time`; default ~10 visible rows; resizable.
* Manufacturing journal lines now include `recipe_name` along with `recipe_id`.
* Fixed missing import of `Item` in `ledger_api.py` for Linux branch.

(3) CHANGES TO EXISTING FACTS (SoT → session)

* Old (SoT): Journals are the receipt mechanism; Logs page behavior unspecified.
  New (session): **Logs page** uses **ledger-only** (`item_movements`) for history in beta; journals remain as receipts but are not required for Logs rendering.
* Old (SoT): Legacy FIFO code existed alongside ORM.
  New (session): Legacy sqlite/REAL FIFO path **removed**; ORM INT path is sole authority.

(4) CLARIFICATIONS / TIGHTENING

* SoT vague on cross-OS paths → clarified as: journals dir resolves to `%LOCALAPPDATA%\BUSCore\app\data\journals` on Windows and `~/.local/share/BUSCore/app/data/journals` on Linux/macOS.
* SoT ambiguous about consumption reasons → clarified as: stock-out reasons are limited to `{sold, loss, theft, other}` and are written as `source_kind` (and journal `type`) for traceability.
* SoT vague on Logs pagination → clarified as: ledger-based Logs paginate with `cursor_id` (movement id), returning items with `id < cursor_id`.

(5) CONFIRMED / RESTATED (NO CHANGE)

* SoT says: Quantities stored as INT in base units; consumption is FIFO.
  Session: explicitly confirmed and exercised via smoke and new endpoints.
* SoT says: Commit DB changes before journaling; journals are non-blocking.
  Session: confirmed in inventory/consume/adjust/stock-out flows.
* SoT says: Manufacturing uses base units and should not oversell outputs.
  Session: confirmed via smoke invariants (no oversold; output unit cost 0).

(6) OPEN QUESTIONS / UNRESOLVED / UNCERTAIN

* Question: Should recipe CRUD history be visible in Logs post-beta?
  Context: Logs now show stock changes only; recipe events would need either a recipe_audit table or to continue using a recipes journal for UI.
* Uncertain: Standardized list and localization of stock-out reasons.
  Needs: Decision on final reason set and where to centralize labels (backend enum vs UI map).
* Question: Background indexer `AttributeError` seen during startup.
  Context: Non-blocking; not part of inventory/manufacturing scope but persists in logs.
