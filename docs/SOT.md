**TGC BUS Core — Source of Truth (Updated 2025-12-02)**

> **Authority rule:** The uploaded **codebase is truth**. Where this document and the code disagree, the SoT **must be updated to reflect code**. Anything not stated = **unknown / not specified**.
>
> **Change note (2025-12-02, v0.3.1 "Iron Core"):** Documents unified Contacts/Vendors shallow+deep UI, façade defaults and delete semantics (cascade/null + facet-only removes via PUT), and extends smoke coverage for the dual façades.
> **Change note (2025-11-26, v0.3.0 "Iron Core"):** Roll-up version bump to v0.3.0 “Iron Core” reflecting integrated Home/dashboard layout and sidebar structure, single-operator design ethos, local-only analytics event store and “analytics from local events only” principle, optional anonymous license hash and push-only telemetry model, and clarified manufacturing run cost/capacity view and Core vs Pro philosophical split from the 2025-11-24 session.
> **Change note (2025-11-24, v0.1.1):** Documents canonical Home/dashboard layout and sidebar structure; adds single-operator design ethos; defines local-only analytics event store and “analytics from local events only” principle; documents optional anonymous license hash and push-only telemetry model; clarifies manufacturing run cost/capacity view and Core vs Pro philosophical split.
> **Change note (2025-11-23, v0.1.0):** Documents canonical Codex/GitHub patch-branch development workflow and `D:\BUSCore-Test` local test clone; clarifies that local clones are test-only and all code edits happen via Codex on GitHub.
> **Change note (2025-11-20):** Promotes `scripts/dev_bootstrap.ps1` to canonical dev launcher; preserves manual dev/smoke flow for clarity; documents Pro gating surfaces and current gaps (DB still under repo; AppData not yet cut over). Adds explicit canonical launch/smoke commands.
> **Change note (2025-11-21):** UI branding/layout updated: root-level logo PNGs (`Flat-Dark.png`, `Glow-Hero.png`), hero image removed, small brand mark added in left nav, favicon standardized to `ui/favicon.svg`, and Git rules tightened for these binaries.
> **Change note (2025-11-22):** DB is now bound to `%LOCALAPPDATA%\BUSCore\app\app.db` on Windows; engine + sessions are centralized in `core.appdb.engine`; `/dev/db/where` and `BUSCORE_DEBUG_DB` were added for DB diagnostics; Windows Store/MSIX Python is explicitly unsupported.

---

## Versioning & Changelog

* **Current SoT document version:** `v0.3.1 "Iron Core"`.
* All BUS Core SoTs and adjacent TGC method/process docs use a three-part version string: `vX.Y.Z`.

  * **X – Release track.** `0` = pre–official-release track; `1` = first formal release of the method/product; higher values represent later lifecycle stages.
  * **Y – Document / product major version.** Bump when the structure or meaning of the document changes in a way that could confuse someone reading an older version (sections moved, concepts redefined, new rules added, etc.).
  * **Z – Iteration / patch.** Bump for **any** edit, including typos, formatting, or other small deltas.
* Triggers (must stay consistent across all docs using this scheme):

  * Any edit at all ⇒ bump **Z**.
  * Structural or meaning change ⇒ bump **Y**.
  * New lifecycle phase (e.g., pre-launch → published case-study → taught-in-webinars) ⇒ bump **X**.
* Changelog rules (this document):

  * From this point forward, **every change** to this SoT (of any size) **must** add a corresponding changelog entry (“Change note …”) at the top of the document, including the new `vX.Y.Z` value and the date.
  * Existing `Change note (YYYY-MM-DD)` entries represent the pre-`X.Y.Z` history and remain valid as the historical changelog.

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
  * **Local-only analytics:** all analytics used by core (Home, Recent Activity, Shop Insights) are computed from **events stored locally** on the user’s machine. Core does **not** depend on remote telemetry for metrics.
  * **Single-operator friendly:**

    > **If it only takes one person to run the shop, it should only take one person to manage the system.**
    > UI, configuration, and maintenance must remain operable by a single busy owner without requiring “sysadmin brain” or a separate operator role.

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
  * Façade defaults: `POST /app/vendors` assumes `role=vendor, kind=org`; `POST /app/contacts` assumes `role=contact, kind=person` when omitted.
  * Deletes: `DELETE /app/vendors/{id}` auto-nulls child `organization_id`; `DELETE ...?cascade_children=true` removes dependents. If `role=both`, drop a single facet via `PUT ... {role: vendor|contact}` instead of DELETE.
  * Filters: `role`, `kind`, `q` (name/contact substring), and `organization_id` are supported on GET.
  * Dedupe and merge semantics defined in §9.

* **Items:**

  * Minimal core fields: `id`, `name`, `sku`, `item_type`, `vendor_id`, `qty`, `unit`, `meta`.
  * `item_type` enum is **soft-defined** (no strict SoT list yet; see Unknowns).

  ## domain modle is stale as of curent update to section 8- db map.

* **RFQ:**

  * Request for Quotation; currently early-stage / stub UI & endpoints.

* **Manufacturing:**

  * Manufacturing runs (formerly “Inventory run”) now anchored at `POST /app/manufacturing/run`.

  * Journals capture manufacturing actions as jsonl entries.

  * Each manufacturing run takes a **recipe** and a **quantity** and must produce a **run result view** that shows, in one place:

    1. **Stock changes** (per item):

       * Outputs: positive deltas, e.g. `Copper Rose – Classic: +3`.
       * Inputs: negative deltas, e.g. `Petal A1: -15`, `Stem Wire S1: -3`.

    2. **Material cost consumed**:

       * For each input material: `used_qty × cost_per_unit`.
       * Total material cost for the run = sum of all input material costs.

    3. **Value of stock added (optional, if defined)**:

       * If a target cost/value per output unit exists (e.g. `target_cost_per_rose`), compute `quantity × target_cost_per_unit`.
       * Optionally surface the **margin-like delta**: `(value_of_stock_added – total_material_cost)` as an approximate indicator (not accounting-grade).

    4. **Capacity remaining**:

       * For each limiting input material, compute how many **additional units** can be produced with current stock:

         * `capacity = floor(on_hand_qty / recipe_qty_required)`.
       * Surface this as “You can still produce **N** more units with current [material] stock.”

  * These calculations are **Core behavior** (community tier) and must be computed locally from the items table and recipe definitions; they do **not** require Pro, remote services, or any LLM features.

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

| Route / state        | Primary screen            | `data-role`        | Card file                       | Mount function     | License surface                           |
| -------------------- | ------------------------- | ------------------ | ------------------------------- | ------------------ | ----------------------------------------- |
| *No hash* / `#/home` | Home                      | `home-screen`      | static                          | `mountHome()`      | None                                      |
| `#/BUSCore`          | Home (alias)              | `home-screen`      | static                          | `mountHome()`      | None                                      |
| `#/inventory`        | Inventory (items + bulk)  | `inventory-screen` | `core/ui/js/cards/inventory.js` | `mountInventory()` | Pro intent: `POST /app/manufacturing/run` |
| `#/contacts`         | Contacts (vendors/people) | `contacts-screen`  | `core/ui/js/cards/vendors.js`   | `mountContacts()`  | None                                      |
| `#/settings`         | Settings / Dev            | `settings-screen`  | `core/ui/js/cards/settings.js`  | `settingsCard()`   | None                                      |

**Deliberate omissions:** no canonical `#/items`, `#/vendors`, `#/rfq` routes yet; RFQ UI remains a card within legacy Tools surface.

#### Contacts card (shallow/deep parity with Inventory)

* The Contacts card mirrors Inventory’s **Shallow/Deep** modal: Shallow (default) = Name (required), Contact, Role chips (Vendor/Contact/Both), Kind toggle (Person/Organization); Deep = Organization selector (`GET /app/vendors?kind=org`), read-only Created At, and reserved metadata area.
* Collapsed rows show **Name + chips** and a second line with **Contact** and optional **Org: …**. List columns: Name, Contact, Role chip, Kind chip/icon. Filters: **All | Vendors | Contacts | Both** chips plus search on name/contact.
* Expanded rows present Name (read-only), Role chip, Kind chip, Organization label/link (if set) on the left; Contact + Created At on the right; footer buttons **Edit** + **Delete**. Delete flow supports facet-only (role=`both`) via PUT role change and org cascade/null decisions.

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

### 5.6 Branding, logo assets, and favicon (updated 2025-11-21)

#### 5.6.1 Canonical brand images (root PNGs)

* The repository has exactly **two** canonical root-level brand images:

  * `Flat-Dark.png` — primary flat logo for dark backgrounds.
  * `Glow-Hero.png` — hero/glow variant used in selected surfaces (docs, marketing, etc.).
* These two files live at the **repo root**. They are treated as stable binary assets:

  * Do **not** rename or relocate them without updating this section first.
  * Any additional logo variants must be explicitly added to this section.

#### 5.6.2 Home layout — hero removed

* The **Home** screen (`#/home` / `#/BUSCore`) does **not** show a large center “hero” image.
* The primary content area is reserved for:

  * Introductory copy,
  * Status/diagnostics,
  * Links to core actions.
* Any reintroduction of a large hero-style graphic in the Home content area must be explicitly documented here first.

#### 5.6.3 Left navigation branding

* The left navigation keeps the existing **dot icon** (status/marker) **unchanged**.
* A **single** small brand mark is displayed next to the “BUS Core” label:

  * Height: **16–18px** (hard cap at 18px; preserve aspect ratio).
  * Position: **immediately before** the “BUS Core” text, in the same horizontal row.
  * No additional logo marks in the left nav (no duplicates, no secondary hero).
* Any theme-specific variants (e.g., future light/dark logo swaps) must respect:

  * Same size envelope (≤18px height),
  * Same position,
  * Still exactly one logo per label.

#### 5.6.4 Favicon (single source of truth)

* Favicon source of truth is **one** SVG file in the UI tree:

  * `ui/favicon.svg` — BUS Core gear + orange wedge.
* In `core/ui/shell.html`:

  * There is exactly **one** favicon link:

    ```html
    <link rel="icon" type="image/svg+xml" href="ui/favicon.svg?v=BUSCORE_VER">
    ```

    * `BUSCORE_VER` (or equivalent) is a cache-busting token, not a second asset.
  * Remove or forbid any additional `<link rel="icon">` tags or scripts that attempt to inject extra favicons at runtime.
* PNG favicon variants (16×16, 32×32, etc.) are **not canonical** unless this section is updated to include them explicitly.

#### 5.6.5 Binary handling for branding assets

* Branding work must be **binary-safe**:

  * `Flat-Dark.png` and `Glow-Hero.png` are treated as long-lived binary assets.
  * Only text files (HTML/JS/CSS/markdown) that reference these assets should change under normal circumstances.
* Any change to the **filenames** or **locations** of these two PNGs requires:

  * A SoT update here in §5.6, and
  * Matching `.gitignore` / `.gitattributes` adjustments in §12.

### 5.7 Home screen layout & Quick Action (canonical 2025-11-24)

This section defines the **Home** screen layout for `#/home` / `#/BUSCore`.

**Top bar:**

* **Left side:**

  * Small brand mark + “BUS Core” label as defined in §5.6.3.
  * Tagline text (inline with title or immediately beneath):

    > `Local-first business core for small shops`

* **Right side:**

  * **Version indicator**, e.g. `v0.5.x` (derived from the running build).
  * **Environment indicator**, e.g. `Local • Windows` (format is implementation-defined but must clearly convey “local + OS”).
  * **Status pill**:

    * Values: at minimum `Healthy` and `Attention`.
    * Backed by health/diagnostics; exact thresholds are implementation-defined but must be documented once fixed.

**Primary stats row (4 cards):**

* Exactly four summary cards are reserved at the top of the main content:

  1. `Items (active)`
  2. `Vendors`
  3. `Runs (last 7 days)`
  4. `Units moved (last 7 days)` (or an equivalent hard shop metric derived from local analytics events).

* The metrics shown must be derived from the **local analytics event store** (§6) and/or app DB; they may **not** rely on remote telemetry.

**System info strip (under stats):**

A horizontal strip under the stats row shows core system status:

* `Database:` the **resolved filesystem path** of the core DB (see §8.1). On Windows this should resolve to `%LOCALAPPDATA%\BUSCore\app\app.db`, displayed via the central path helpers (not hardcoded strings).
* `Last backup:` timestamp of most recent backup, or the literal `Never` if no backup has been created; `Never` should be visually emphasized.
* `Journaling:` status string such as `Enabled (N entries)` or `Disabled`, reflecting whether manufacturing/import journals are active.
* `Telemetry:` status label reflecting the **telemetry mode**:

  * Default text: `Disabled (local-only)` while no anonymous push feature exists.
  * If optional anonymous push is implemented (§7.1), this label must reflect the user’s current opt-in/opt-out choice.
* `Last smoke test:` timestamp of the most recent successful smoke run plus `Pass` / `Fail` indicator (source of truth is the smoke harness output).

**Recent Activity panel (right column):**

* Home includes a **Recent Activity** panel, typically in a right-hand column, showing the last N significant events, e.g.:

  * `2025-11-24 19:32 – Run #14 – Copper Rose – 3 units`
  * `New vendor – BGM Metalworks`
  * `Item updated – Petal A1 cost`
  * `Backup created – app.2025-11-24.db`

* Entries are derived from the local analytics event store and/or journals, not remote services.

**Tool cards row (central cards):**

* A row of **large clickable cards** in the main content area provides primary navigation into core flows. Initial canonical slots:

  * `Items` – “View & edit all items”
  * `Vendors` – “Manage sources & contacts”
  * `Runs` – “Execute manufacturing runs”
  * `Insights` – “Shop stats & analytics”

* Card labels (`Items`, `Vendors`, `Runs`, `Insights`) are canonical; subtitles and supporting copy may evolve, but any new cards or renames must update this section.

**Home Quick Action button (user-mappable):**

* Home includes a single **Quick Action** button, placed in the top-right area of the main content (not the browser chrome).

* **Default action:** `New Run` (entry into a “manual manufacturing run” flow).

* The user may remap this button to:

  * `New Item`
  * `New Vendor`
  * “Open Items”, “Open Vendors”, or “Open Runs”
  * Entry point of a plugin (e.g. Etsy sync, analytics plugin) once such plugins are available.

* **Mapping controls:**

  * From a tool card: context or overflow menu item such as `Set as Home Quick Action`.
  * From the button itself: small settings/menu affordance such as `Change Quick Action`.

* The mapping is stored locally and must be respected on subsequent launches.

### 5.8 Sidebar navigation structure (canonical 2025-11-24)

This section defines the **visible labels** and semantics of the primary left navigation (distinct from the Tools drawer).

* The left navigation must contain the following **top-level entries**:

  1. `Home`
  2. `Items`
  3. `Vendors`
  4. `Runs`
  5. `Files / Docs`
  6. `Insights`
  7. `Settings`

* Label-to-route mapping (current state):

  * `Home` → `#/home` (or `#/BUSCore` alias).
  * `Items` → `#/inventory` (Inventory screen; UI label is `Items` even though route is `#/inventory`).
  * `Vendors` → currently points to `#/contacts` (unified vendors/contacts screen) until a dedicated `#/vendors` is introduced.
  * `Runs` → implementation-defined route or filtered view within inventory/manufacturing; until a dedicated `#/runs` route exists, this entry may deep-link into the appropriate section.
  * `Files / Docs` → reserved for file/SOP/receipt handling screens (implementation-defined until fully specified).
  * `Insights` → reserved for Shop Insights screens powered by local analytics.
  * `Settings` → `#/settings`.

* The Tools drawer (§5.3) remains a secondary access pattern; the left nav defined here is **primary** for normal users.

* Any addition/removal/rename of a top-level nav label must update this section and, where applicable, the canonical route table in §5.2.

---

## 6) Data & Journals (High-Level)

* **Core DB:** SQLite, single primary file (see §11 for location and path rules).

* **Journals:** append-only `.jsonl` logs for sensitive actions (manufacturing, imports, plugin audits).

  * Manufacturing: `data/journals/manufacturing.jsonl` (name tracked in gaps until fully migrated from `inventory.jsonl`).
  * Import/bulk: `data/journals/bulk_import.jsonl`.
  * Plugin audit: `data/journals/plugin_audit.jsonl`.

* **Local analytics event store (conceptual):**

  * BUS Core maintains a **structured event log** inside the app DB for analytics and activity feeds. The exact table name is not yet specified in SoT; implementation must document it once fixed.

  * Each event row must include at least:

    * `id`
    * `timestamp`
    * `event_type`
    * `entity_type` (e.g. `item`, `vendor`, `run`, …)
    * `entity_id`
    * Optional numeric `qty`
    * Optional numeric `value`
    * `meta` (JSON blob for extra structured fields)

  * Typical event types include (non-exhaustive):

    * `item_sold`
    * `item_moved`
    * `run_completed`
    * `vendor_created`
    * `item_created`
    * `item_archived`

  * **Usage requirements:**

    * Home stats cards (§5.7), Recent Activity (§5.7), and future **Shop Insights** screens (§5.8) must derive their metrics from this **local event store and core DB only**.
    * No analytics used by Core may require remote telemetry or third-party services.

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

### 7.1 Anonymous ID & push-only telemetry (design)

This subsection describes the **target behavior** for any future telemetry-like feature; implementation status is TBD and must match this spec when introduced.

* Each installation or license may have a **stable random 24-character hash** (anonymous ID), generated locally and stored with the license or config.

* This anonymous ID:

  * Must **not** contain PII or be derived from user-identifying data.
  * Is used solely to **deduplicate and group anonymous submissions** from the same install.

* **Telemetry model (if implemented):**

  * **Push-only and optional:**

    * Core never pulls or auto-subscribes to remote data collection.
    * Users must explicitly opt in before any stats are sent.

  * **Payload shape (high level):**

    * Anonymous ID (hash) described above.
    * Aggregated metrics and counters (e.g., feature usage counts, event totals).
    * Optional plugin or feature flag usage indicators (on/off or coarse-grained counts).

  * **Forbidden in payload:**

    * Item names, vendor names, specific quantities per individual run.
    * Any data that could be reasonably tied back to a specific business or person without additional context.

* **UI reflection:**

  * The `Telemetry:` line on Home (§5.7) must accurately reflect the current state:

    * Default: `Disabled (local-only)` when no push feature is active or user has not opted in.
    * If an opt-in push is implemented: values like `Opted-in (anonymous stats)` / `Disabled (local-only)`.

* Any introduction of telemetry that does **not** match this design requires an explicit SoT update and justification.

### 7.2 Core vs Pro philosophical boundaries

This section captures the **philosophical split** between Core (free) and Pro (paid), aligning with the current technical gating.

* **Core (Community, free, local-first):**

  * Items (materials and products).

  * Vendors / contacts (unified model).

  * Manufacturing recipes & one-off runs.

  * Stock changes and basic inventory control.

  * Local analytics events and **Shop Insights** computed from local DB (§6).

  * Run-level cost and capacity calculations (§4).

  * Manual file linking:

    * Attach receipts, invoices, SOPs, product docs to items/vendors/runs via attachments.

  * Name normalization via:

    * Canonical names in tables.
    * Optional alias structures (once formalized).

  * Journaling and Recent Activity.

* **Pro (Paid, automation):**

  * Etsy/Shopify/other sales-channel sync.

  * Any **scheduled jobs** or background automations (e.g., scheduled runs, recurring imports/exports).

  * Advanced analytics dashboards beyond the local, single-user views.

  * LLM-powered helpers:

    * Name normalization suggestions.
    * SOP Q&A.
    * File parsing / auto-linking of documents.

  * Possible multi-user or multi-machine sync and automated backup flows.

* **Plugin marketplace interaction:**

  * BUS Core exposes an **open API** that allows third parties (including the user) to build plugins.
  * Third-party plugins may replicate some Pro-like behaviors for advanced users; Pro remains the **official**, maintained, and supported automation/integration path.

* **Design line (must be preserved):**

  > **Core = data & admin brain.
  > Pro = robots & integrations.**

---

## 8) DB, Schema & Migrations (Behavioral)

## 8.1 App database schema (canonical as of 2025-11-22)

BUS Core uses a single SQLite **app database** at:

* Windows: `%LOCALAPPDATA%\BUSCore\app\app.db`

This section is canonical for the app DB. If code or old docs disagree, this section wins and must be treated as an implementation gap.

### 8.1.1 Table: `vendors`

Unified model for organizations and people we deal with (contacts, suppliers, customers, etc.).

Columns:

* `id` — `Integer`, primary key, indexed, not null.
* `name` — `String`, unique, not null.
* `contact` — `String`, nullable. Freeform contact line (email/phone/label).
* `role` — `String`, not null, server default `"vendor"`.
  Used to distinguish vendor/contact/both (exact values are not yet hard-constrained).
* `kind` — `String`, not null, server default `"org"`.
  Identifies whether this row represents an organization vs person, etc.
* `organization_id` — `Integer`, nullable, foreign key → `vendors.id`.
  Optional parent organization; self-referential hierarchy.
* `meta` — `Text`, nullable. JSON blob for extra structured data.
* `created_at` — `DateTime`, not null, server default `now()`.

Relationships:

* Self-reference: `vendors.organization_id` → `vendors.id`.
* One-to-many: `vendors.id` → `items.vendor_id`.

### 8.1.2 Table: `items`

Minimal item catalog for anything we track in the workshop.

Columns:

* `id` — `Integer`, primary key, indexed, not null.
* `vendor_id` — `Integer`, nullable, foreign key → `vendors.id`.
  Optional “preferred vendor” / primary source for the item.
* `sku` — `String`, nullable. External or internal SKU; uniqueness not enforced in DB today.
* `name` — `String`, not null. Human-readable item name.
* `qty` — `Float`, not null, server default `"0"`.
  Current on-hand quantity; units defined by `unit`.
* `unit` — `String`, nullable. Unit of measure label (e.g. `each`, `m`, `kg`).
* `price` — `Float`, nullable.
  Current unit price / cost used by the UI (exact accounting semantics not yet formalized).
* `notes` — `Text`, nullable. Freeform notes.
* `item_type` — `String`, not null, server default `"product"`.
  Soft classification field (e.g. product/material/etc.); values not yet enforced by constraint.
* `created_at` — `DateTime`, not null, server default `now()`.

Relationships:

* Many items may point to a single vendor: `items.vendor_id` → `vendors.id`.
* One item may have many tasks: `tasks.item_id` → `items.id`.
* Attachments may reference items via (`attachments.entity_type = 'item'`, `attachments.entity_id = items.id`).

### 8.1.3 Table: `tasks`

Lightweight task/reminder rows, optionally attached to items.

Columns:

* `id` — `Integer`, primary key, indexed, not null.
* `item_id` — `Integer`, nullable, foreign key → `items.id`.
  Optional link to the item this task is about.
* `title` — `String`, not null. Short task title.
* `status` — `String`, not null, server default `"pending"`.
  Status string; allowed values are not enforced in DB today.
* `due` — `Date`, nullable. Optional due date.
* `notes` — `Text`, nullable. Longer freeform notes.
* `created_at` — `DateTime`, not null, server default `now()`.

Relationships:

* Many tasks may point to a single item: `tasks.item_id` → `items.id`.
* Attachments may reference tasks via (`attachments.entity_type = 'task'`, `attachments.entity_id = tasks.id`).

### 8.1.4 Table: `attachments`

Generic attachment/annotation table, polymorphic across entities.

Columns:

* `id` — `Integer`, primary key, indexed, not null.
* `entity_type` — `String`, not null.
  Logical type of the attached entity (e.g. `"vendor"`, `"item"`, `"task"`, others in future).
* `entity_id` — `Integer`, not null.
  Primary key of the target entity in its table.
* `reader_id` — `String`, not null.
  Identifier for the process/reader that created this attachment.
* `label` — `String`, nullable. Optional human label / tag.
* `created_at` — `DateTime`, not null, server default `now()`.

Relationships:

* Polymorphic; no enforced foreign keys. Valid pairs today include:

  * `("vendor", vendors.id)`
  * `("item", items.id)`
  * `("task", tasks.id)`

Any new `entity_type` values must be documented in SoT before use.

---

## 8.2 Plans database schema (canonical as of 2025-11-22)

BUS Core uses a separate SQLite **plans database** at:

* Windows: `<APP_DIR>/plans.db`

This DB holds long-lived “plans” for the planner system.

### 8.2.1 Table: `plans`

Columns:

* `id` — `TEXT`, primary key, not null.
  Stable plan identifier.
* `created_at` — `TEXT`, not null.
  ISO-8601 timestamp string of when the plan was created.
* `source` — `TEXT`, not null.
  Where the plan came from (e.g. which tool or workflow).
* `title` — `TEXT`, not null.
  Human-readable plan title.
* `note` — `TEXT`, nullable.
  Optional user note / description.
* `status` — `TEXT`, not null.
  String enum stored as text (Planner status value).
* `stats_json` — `TEXT`, not null.
  JSON-encoded statistics for the plan.
* `actions_json` — `TEXT`, not null.
  JSON-encoded list of actions in the plan.

There are no additional tables in `plans.db` as of 2025-11-22.

## 9) Vendors & Contacts (Unified Model)

* **Single table:** `vendors` holds both organizations and people.

* **Columns (high level):**

  * `id`, `name` (unique), `kind`, `role`, `contact`, `organization_id`, `meta`, timestamps.
  * `kind`: `org` or `person` (soft enum).
  * `role`: `vendor`, `contact`, or `both`.

* **API façades:** `/app/vendors` and `/app/contacts` operate on the same table.

  * **POST defaults:** vendors → `role=vendor, kind=org`; contacts → `role=contact, kind=person` (when omitted).
  * **GET filters:** `role`, `kind`, `q` (substring match on `name`/`contact`), and `organization_id`.
  * **PUT:** partial update; only provided fields are patched.
  * **DELETE:** org rows null child `organization_id` by default; `?cascade_children=true` deletes dependents. `role='both'` facet removal occurs via `PUT ... {role: vendor|contact}` instead of DELETE.

---

## 10) Testing & Smoke Harness (authoritative for dev/test)

* **Canonical harness:** `buscore-smoke.ps1` at repo root. Must pass **100%** for acceptance.
* **Auth pattern:** mint via `GET /session/token`; send **`X-Session-Token`** on protected calls (tests don’t rely on cookies).
* **Expected steps (contacts/vendors coverage):**

  1. `POST /app/vendors {name:"ACME"}` → `201` with `role=vendor`, `kind=org`.
  2. `POST /app/contacts {name:"Sam"}` → `201` with `role=contact`, `kind=person`.
  3. `PUT /app/contacts/{samId} {role:"both"}` → `200` with `role=both`.
  4. Facet delete path: `PUT /app/contacts/{samId} {role:"vendor"}` → `200`; `DELETE /app/contacts/{samId}` → `204`.
  5. `POST /app/contacts {name:"Ava", kind:"person", organization_id: acmeId}` → `201`.
  6. `DELETE /app/vendors/{acmeId}` (no cascade) → `204`; `GET /app/contacts/{avaId}` shows `organization_id=null`.
  7. Recreate `ACME` + `Ava2`; `DELETE /app/vendors/{acmeId}?cascade_children=true` → `204`; `GET /app/contacts?q=Ava2` returns empty.

* **Status handling:** 201 for creates, 200 for fetch/updates, 204 for deletes. Print first **200 bytes** of body and status on failure.

**Canonical smoke command (from repo root):**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\buscore-smoke.ps1
```

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

### 11.1 Dev workflow — Codex/GitHub patch branches and local test clone

* **Stable branch:** `main` is treated as stable; no direct local edits or Codex runs against `main`.
* **Work branches:** disposable patch branches created from `main`, named `patch/<short-name>` (e.g. `patch/UI-CRUD-Piping-Pass`).

**Windows dev root (local test clone):**

* **Dev/test clone root (Windows):** `D:\BUSCore-Test`.

* This directory is a **Git clone of the GitHub repo** and is used **only** to:

  * Pull current patch branches from GitHub.
  * Run `scripts/dev_bootstrap.ps1` and `buscore-smoke.ps1` for local testing.

* Rule: **no manual edits or local commits** are made in `D:\BUSCore-Test`; all code changes are made via Codex on GitHub.

**Patch workflow (per change):**

1. Ensure `main` is green/stable on GitHub`.

2. Create a new patch branch from `main`, e.g. `patch/UI-CRUD-Piping-Pass`.

3. In Codex, target that patch branch for all work (Codex edits live on GitHub).

4. On Codex completion, use “Make PR” and merge the PR into the patch branch (the patch branch is disposable and accumulates work).

5. To test locally:

   ```powershell
   cd D:\BUSCore-Test
   git fetch origin
   git checkout -B patch/UI-CRUD-Piping-Pass origin/patch/UI-CRUD-Piping-Pass
   ```

   Then run the canonical dev launcher and smoke scripts from that clone.

6. If tests fail, repeat steps 3–5 (new Codex task targeting the same patch branch; pull and retest).

7. When the patch branch is stable, open a final GitHub PR from `patch/<short-name>` into `main` and merge.

8. After merge, update the local clone and clean up the local patch branch:

   ```powershell
   cd D:\BUSCore-Test
   git checkout main
   git pull origin main
   git branch -D patch/UI-CRUD-Piping-Pass
   git fetch --prune
   ```

---

## 12) Repository Hygiene & Legal (updated 2025-11-21)

* **Privacy scrub:** removed hard-coded local paths/usernames and debug logs from code/comments/docs`.

* **Top-level `LICENSE`:** present with official **AGPL-3.0** text; **SPDX headers** inserted across source files`.

* **`.gitignore`:**

  * Based on standard Python template, plus project-specific entries:

    * Virtual environments, build artifacts, local DBs, UI `node_modules`, logs.
  * Image handling:

    * It is permitted to use broad patterns (e.g., `*.png`) to ignore non-critical image assets.
    * **Exception:** two root-level logo files must always be tracked:

      * `Flat-Dark.png`
      * `Glow-Hero.png`
    * `.gitignore` must explicitly **allowlist** these files (e.g., via `!Flat-Dark.png`, `!Glow-Hero.png`) so they remain versioned even if PNGs are generally ignored.

* **`.gitattributes`:**

  * If the repo uses wildcard rules (e.g., `*.png filter=lfs`) to store images via Git LFS, the two canonical logo files are explicitly exempt:

    * `/Flat-Dark.png` and `/Glow-Hero.png` must be stored as **normal Git blobs**, not LFS pointers.
  * The `.gitattributes` file must therefore contain per-path overrides for these two files that disable any inherited LFS filters.

* **Branding binary invariants:**

  * Do **not** rename, move, or re-encode `Flat-Dark.png` or `Glow-Hero.png` without:

    * Updating §5.6 (branding/asset section), and
    * Updating this §12 to reflect any new paths/filenames.

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

* **Analytics implementation:** formalize the app DB table name for the local analytics event store, ensure it matches §6, and wire Home/Insights to use it.

* **Nav/route alignment:** introduce dedicated routes (e.g. `#/vendors`, `#/runs`, `#/insights`) to align with the sidebar labels in §5.8, or update SoT once a final routing scheme is chosen.

---

## 14) Unknowns / Not Specified

* Cross-platform paths (macOS/Linux).
* Exact status code for license rejections (smoke asserts “not 200”).
* Full domain model field list / minimal payload shapes for CRUD.
* Enum validation for `item_type` or stricter dedupe constraints for contacts (e.g., `(name, organization_id)`).
* `organization_id` FK action (`SET NULL` / cascade / restrict).
* SPDX variant (`AGPL-3.0-only` vs `AGPL-3.0-or-later`) for headers.
* Exact table name for the local analytics event store; SoT currently describes schema/usage only.

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

* **DB/session (updated 2025-11-22):** `core.appdb.engine` constructs the single SQLAlchemy engine for the core database`.

  * It exposes `ENGINE`, `SessionLocal`, and `get_session()` as the only supported entry points for DB access.
  * On Windows, the SQLite URL is built as `sqlite+pysqlite:///<posix_path>` (exactly three slashes) pointing to `%LOCALAPPDATA%\BUSCore\app\app.db`.
  * No other module may call `create_engine()` for the core DB; all sessions must come from `SessionLocal` / `get_session()`.

* **Broker:** `get_broker` initializes plugin broker with Secrets, capability registry, reader settings`.

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
* **Auth:** header token required on protected routes; cookie not relied on in tests`.

---

**End of Source of Truth.**

