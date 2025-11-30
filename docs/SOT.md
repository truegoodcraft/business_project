TGC BUS Core — Source of Truth (Updated 2025-11-30) 

> **Authority rule:** The uploaded **codebase is truth**. Where this document and the code disagree, the SoT **must be updated to reflect code**. Anything not stated = **unknown / not specified**.
>
> **Change note (2025-11-30, v0.3.1 "Iron Core"):** Captures first pass of canonical **Inventory** and **Contacts** UI behavior (Shallow/Deep inputs, expanded-only mutating actions, structured contact meta), clarifies **session token** response shapes and the requirement that all `/app/**` calls send an authoritative `X-Session-Token` header, and defines launcher dependency rules (pinned `pip`, `requirements.lock` priority, offline/cached install planned) plus the **Python 3.12** Windows runtime target.
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

  * `Inventory` – “View & edit all items”
  * `Vendors` – “Manage sources & contacts”
  * `Runs` – “Execute manufacturing runs”
  * `Insights` – “Shop stats & analytics”

* Card labels (`Inventory`, `Vendors`, `Runs`, `Insights`) are canonical; subtitles and supporting copy may evolve, but any new cards or renames must update this section.

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

### 5.8 Sidebar navigation structure (canonical 2025-11-24, label updated 2025-11-30)

This section defines the **visible labels** and semantics of the primary left navigation (distinct from the Tools drawer).

* The left navigation must contain the following **top-level entries**:

  1. `Home`
  2. `Inventory`
  3. `Vendors`
  4. `Runs`
  5. `Files / Docs`
  6. `Insights`
  7. `Settings`

* Label-to-route mapping (current state):

  * `Home` → `#/home` (or `#/BUSCore` alias).
  * `Inventory` → `#/inventory` (Inventory screen; UI label is **Inventory**).
  * `Vendors` → currently points to `#/contacts` (unified vendors/contacts screen) until a dedicated `#/vendors` is introduced.
  * `Runs` → implementation-defined route or filtered view within inventory/manufacturing; until a dedicated `#/runs` route exists, this entry may deep-link into the appropriate section.
  * `Files / Docs` → reserved for file/SOP/receipt handling screens (implementation-defined until fully specified).
  * `Insights` → reserved for Shop Insights screens powered by local analytics.
  * `Settings` → `#/settings`.

* The Tools drawer (§5.3) remains a secondary access pattern; the left nav defined here is **primary** for normal users.

* Any addition/removal/rename of a top-level nav label must update this section and, where applicable, the canonical route table in §5.2.

### 5.9 Inventory screen – layout & behavior (canonical 2025-11-30)

This section defines the behavior of the **Inventory** screen and its primary CRUD UI.

* **Route:** `#/inventory`.
* **Primary screen:** `[data-role="inventory-screen"]` containing `[data-role="inventory-root"]`.

  * The router must **unhide** `inventory-screen` when the hash is `#/inventory`.
* **UI label:** canonical label for this screen is **“Inventory”** (Home card, sidebar entry, and any tiles/buttons pointing at this screen).

#### 5.9.1 Shallow/Deep input pattern (items)

* Inventory input uses a **Shallow/Deep** pattern for Add/Edit:

  * **Shallow (default) fields:**

    * `Name`
    * **Smart Qty** (parsed quantity input)
    * `Price`
    * `Location` (UI-level field; storage details are implementation-defined until DB/meta mapping is finalized)
  * **Deep (expanded) fields:**

    * `SKU`
    * `Vendor`
    * `Type`
    * `Notes`

* **Smart Qty:**

  * Uses a canonical parser (e.g. `parseSmartInput`) to interpret user input into a numeric `qty`.
  * The UI shows a **live parse badge** while typing, indicating the interpreted value (e.g., `+5`, `-2`, or final numeric).

* **Type field:**

  * Maps onto `items.item_type`.
  * **Default value:** `Product`.
  * Allowed options (UI-level): `Product | Material | Component`.
  * These values are a **soft enum**; DB still treats `item_type` as a free string field per §8.1.2.

* **Null/optional fields (Inventory UI contract):**

  * `sku`, `vendor_id`, and `notes` are **explicitly allowed to be `null`** on create/update.
  * Saving from Shallow state (without opening Deep) is valid; these fields may remain unset.
  * `qty` and `item_type` must satisfy DB constraints (§8.1.2) but may be provided via defaults when the user leaves them blank.

#### 5.9.2 Table layout & interactions

* **Inventory table:**

  * No dedicated **Actions** column.
  * Clicking a row **expands an inline details panel** beneath that row.
  * The expanded panel shows the full item fields plus **Edit** / **Delete** buttons.

* **Vendor field behavior:**

  * The Vendor field is a **dropdown** populated from `GET /app/vendors`.
  * If there are **no vendors** available:

    * Do **not** show an empty dropdown.
    * Instead render an inline **help link** pointing to the **Contacts** screen (`#/contacts`) to manage vendors/contacts.

* **Delete behavior:**

  * Deleting an item **always requires an explicit confirmation** before issuing `DELETE /app/items/{id}`.
  * No single-click or unconfirmed deletes from the table.

* **Expanded vs row view:**

  * Row view focuses on the high-signal fields (e.g. `Name`, Smart Qty/Qty, Price, Vendor, Location) depending on layout.
  * Expanded view shows the full item, including Deep fields and mutating actions.

* **Refresh behavior:**

  * The explicit “Refresh” button is removed from the Inventory table.
  * The table **automatically refreshes** after **create**, **edit**, or **delete** operations.

#### 5.9.3 Add/Edit modal behavior

* Add/Edit Item uses a **centered modal** with a dark backdrop.

* Modal close rules:

  * The modal **does not close on click-outside**.
  * It must be closed explicitly via **Save** or **Cancel**.
  * This is to prevent accidental loss of partially entered input.

* Shallow vs Deep in the modal:

  * The modal opens in **Shallow** mode by default (Name, Smart Qty, Price, Location visible).
  * Deep fields (SKU, Vendor, Type, Notes) are shown behind an explicit expand/“More details” interaction.
  * Saving is allowed from Shallow alone; Deep is optional.

#### 5.9.4 Responsiveness

* The Inventory table allows **horizontal scroll** on narrow screens.

* Below approximately **700px** viewport width:

  * The **Vendor** and **Location** columns may be **hidden** to preserve readability.
  * Column widths are otherwise treated as fixed for consistency.

* The exact breakpoint and CSS behavior can evolve, but:

  * Vendor/Location are considered **secondary columns** for small screens.
  * Primary fields (`Name`, Smart Qty/Qty, Price) remain visible.

### 5.10 Contacts screen – layout & behavior (canonical 2025-11-30)

This section defines the behavior of the **Contacts** screen, which presents the unified `vendors` model as contacts/vendors.

* **Route:** `#/contacts`.
* **Primary screen:** `[data-role="contacts-screen"]` containing `[data-role="contacts-root"]` (mounted by `mountContacts()` from `core/ui/js/cards/vendors.js`).
* **Scope:** shows people and organizations from the `vendors` table, filtered and decorated by `role` / `kind`.

#### 5.10.1 Keyboard policies

* There are **no plain-letter global shortcuts** on the Contacts screen unless explicitly approved in this SoT.
* Specifically, the legacy **`N` / `n` = “New Contact”** behavior is **removed**:

  * Pressing `N` or `n` on the Contacts screen does **nothing**.
  * “New Contact” is available via an explicit UI button only.

#### 5.10.2 Row vs expanded behavior

* **Row view is read-only:**

  * Table rows **do not** expose **Edit** or **Delete** buttons.
  * Rows are for selection/inspection only.

* **Expanded contact panel:**

  * Clicking a row expands an inline panel directly beneath it.
  * The expanded panel:

    * Shows badges indicating roles (e.g. **Contact**, **Vendor**, **Both**).

    * Shows `kind` (person vs organization) in a compact, labeled way.

    * Displays contact details (Email/Phone; see §9 for meta shape).

    * Displays organization status:

      * If no organization is linked, shows the literal status line: **“No organization linked”**.
      * If an organization is linked, shows its name (display rules are still evolving; see §13).

    * Provides the **mutating actions**:

      * **Edit** button → opens Edit Contact dialog.
      * **Delete** button → confirms and issues `DELETE /app/contacts/{id}` (or `/app/vendors/{vendor_id}` depending on façade).

* **Mutating actions rule:**

  * **All mutating actions** (Edit/Delete) for contacts **live inside the expanded detail**.
  * Row view must remain **non-mutating**.

#### 5.10.3 Edit Contact dialog – structured contact fields

* The Edit Contact dialog reads/writes **structured fields** from `vendors.meta`:

  * `meta.email` → **Email** input.
  * `meta.phone` → **Phone** input.

* The Contacts table **“Contact” column** is **display-only** and computed as:

  * `[meta.email, meta.phone].filter(Boolean).join(' | ')`

* **Backwards compatibility guard:**

  * If legacy combined strings of the form `"email | phone"` were previously stored, they must be treated as **input only**, not as the new canonical shape.

  * On load/edit:

    * Detect such combined strings.
    * **Split on `|`** and trim parts into `meta.email` and `meta.phone`.
    * Treat `meta.email` / `meta.phone` as the canonical source of truth going forward.

  * The combined `"email | phone"` format must **not be re-stored** as the long-term representation.

* Other Edit Contact fields:

  * **Name** — required (maps to `vendors.name`).
  * **Role** — UI control for `vendors.role` (e.g. Vendor / Contact / Both).
  * **Kind** — UI control for `vendors.kind` (e.g. Person / Organization).
  * **Organization** — optional link to a parent org (`organization_id`); exact behavior is currently an implementation gap (see §13).
  * **Advanced metadata** — reserved area for future `meta` keys beyond `email` / `phone`.

* Modal behavior:

  * Dialog is centered with dark backdrop, matching Inventory modal style.
  * Close behavior follows the same rules as Inventory:

    * No click-outside close.
    * Explicit **Save** or **Cancel** is required.

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
* `contact` — `String`, nullable. Freeform contact line (email/phone/label); treated as legacy for newly structured contact data.
* `role` — `String`, not null, server default `"vendor"`.
  Used to distinguish vendor/contact/both (exact values are not yet hard-constrained).
* `kind` — `String`, not null, server default `"org"`.
  Identifies whether this row represents an organization vs person, etc.
* `organization_id` — `Integer`, nullable, foreign key → `vendors.id`.
  Optional parent organization; self-referential hierarchy.
* `meta` — `Text`, nullable. JSON blob for extra structured data.

  * For contacts, **structured fields** `meta.email` and `meta.phone` are the **source of truth** for email/phone, and may be surfaced separately in the UI.
* `created_at` — `DateTime`, not null, server default `now()`.

Relationships:

* Self-reference: `vendors.organization_id` → `vendors.id`.
* One-to-many: `vendors.id` → `items.vendor_id`.

### 8.1.2 Table: `items`

Minimal item catalog for anything we track in the workshop.

Columns:

* `id` — `Integer`, primary key, indexed, not null.
* `vendor_id` — `Integer`, nullable, foreign key → `vendors.id`.
  Optional “preferred vendor” / primary source for the item. May be `null` on create/update.
* `sku` — `String`, nullable. External or internal SKU; uniqueness not enforced in DB today; may be `null` when not used.
* `name` — `String`, not null. Human-readable item name.
* `qty` — `Float`, not null, server default `"0"`.
  Current on-hand quantity; units defined by `unit`.
* `unit` — `String`, nullable. Unit of measure label (e.g. `each`, `m`, `kg`).
* `price` — `Float`, nullable.
  Current unit price / cost used by the UI (exact accounting semantics not yet formalized).
* `notes` — `Text`, nullable. Freeform notes; may remain `null` for items with no notes.
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

---

## 9) Vendors & Contacts (Unified Model)

* **Single table:** `vendors` holds both organizations and people.

* **Columns (high level):**

  * `id`, `name`, `kind`, `role`, `organization_id`, `meta`, timestamps, plus legacy `contact` string.
  * `kind`: e.g. `org`, `person`; **not strictly enumerated** yet.
  * `role`: e.g. `vendor`, `contact`, `both`.

* **Structured contact fields (canonical):**

  * The canonical structured email/phone fields for contacts are:

    * `meta.email`
    * `meta.phone`

  * The legacy `contact` string column is treated as **freeform/legacy** for new data.

  * Any previously stored combined `"email | phone"` strings must be **parsed** into `meta.email` / `meta.phone` on load/edit and not re-stored in that combined form.

* **Contacts API (current behavior):**

  * **Endpoint:** `/app/contacts` (CRUD).
  * **Storage:** persists to **`vendors`** table (unified model).
  * **Defaults (POST):** when omitted → `role='contact'`, `kind='person'`.
  * **Duplicate-name policy (POST):** if an existing row with the **same `name`** exists:

    * **Merge** instead of insert; set `role='both'`.
    * Merge `meta` JSON (incoming keys overwrite existing).
    * Optionally update `kind` and `organization_id`.
    * Respond **200** (idempotent create/merge).

* **Contacts UI behavior (summary; full detail in §5.10):**

  * Table “Contact” column displays `[meta.email, meta.phone].filter(Boolean).join(' | ')` as **display-only**.
  * Row view is non-mutating; Edit/Delete live in the expanded panel only.
  * Keyboard: no plain-letter shortcuts by default; specifically, `N` does nothing.

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
```

### 10.1 Canonical dev launcher (law)

* **Canonical dev launcher script:** `scripts/dev_bootstrap.ps1` (repo root).

**Canonical dev launch command (from repo root):**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev_bootstrap.ps1
```

* Design intent for `dev_bootstrap.ps1`:

  * Run from a **fresh clone** directory.

  * Ensure Python deps are installed using the **lockfile-first** policy:

    * When `requirements.lock` is present, install from that file.
    * When `requirements.lock` is absent, install from `requirements.txt` (or equivalent source file) and then regenerate the lockfile via the chosen tool (see §13/§14 for open questions).

  * **`pip` version pin:**

    * `pip` must be pinned to a **single stable version** (exact version TBD).
    * The launcher is responsible for enforcing this pin:

      * It checks the current `pip` version in the venv.
      * It performs an **upgrade/downgrade** **only** when the version does **not** match the pin.
      * It never performs unconditional `pip install --upgrade pip` on every run.

  * Export the same key env vars as the manual flow:

    * `PYTHONPATH`
    * `BUS_UI_DIR`
    * Paths for license/config as needed.

* **Offline/cached install mode (design):**

  * An explicit **“offline/cached install” mode** is planned for air-gapped or flaky networks.
  * Target behavior:

    * Prefer a local wheelhouse/cache directory.
    * Use flags such as `--no-index --find-links` to install from cache.
  * This mode is **not yet implemented**; see §13/§14.

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

> **Note:** The manual flow above is a legacy baseline; the lockfile-first and pinned-`pip` rules described for the dev launcher are the canonical target behavior and should eventually be reflected here as well (e.g., prefer `requirements.lock` when present).

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

### 10.2 Windows Python requirement (updated 2025-11-30)

* **Supported Windows runtime:** BUS Core must run on the official **CPython** installer from python.org.
* **Microsoft Store / MSIX Python builds are explicitly unsupported** (they break `%LOCALAPPDATA%` path expectations and DB binding).
* **Reference build for public alpha:** the **Python 3.12.x** line (64-bit installer from python.org). The 3.12 series is the **primary supported target**; other versions may work but are not guaranteed or required by SoT.
* Any Windows bug report must confirm:

  * `python --version` reports `3.12.x`.
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
  * **Dependency enforcement:** ensure the launcher actually enforces the **pinned `pip` version** and **lockfile-first install behavior** described in §10.1, and update the manual dev flow to match once stabilized.
  * **Offline mode:** implement the planned offline/cached install mode (wheelhouse/cached wheels + appropriate `pip` flags).

* **RFQ UI:** complete client workflow (inputs → call → results/attachments).

* **Items CRUD alignment:** ensure `/app/items` GET/POST/PUT and `/app/items/{id}` align with SoT expectations while keeping the **free** one-off qty rule.

* **(Optional next)** Smoke coverage for **`/app/contacts` merge semantics** (duplicate-name POST → merge).

* **Analytics implementation:** formalize the app DB table name for the local analytics event store, ensure it matches §6, and wire Home/Insights to use it.

* **Nav/route alignment:** introduce dedicated routes (e.g. `#/vendors`, `#/runs`, `#/insights`) to align with the sidebar labels in §5.8, or update SoT once a final routing scheme is chosen.

* **Adjust quantity concept:** any dedicated server-side “adjust quantity” logic or endpoints are **deprecated**; item quantity changes should flow through standard **Edit Item** operations. Code should be revised to remove redundant adjust paths.

* **Contacts org linkage & scope parity:**

  * Decide whether the **Organization** field is editable in the Edit Contact dialog (including how “Treat as Vendor” should behave: auto-create vs require linking to an existing org).
  * Define how linked organizations should display in the **table vs expanded panel**.
  * Clarify whether “expanded-only actions” and keyboard rules apply uniformly to **Vendors** and any future **All** tab, or remain Contacts-only.

* **Contacts data hygiene:**

  * Decide on phone-number **formatting/normalization** policy (raw vs normalized formats like E.164) for display and storage.
  * Decide whether legacy `"email | phone"` combined values should be **migrated** to structured `meta.email` / `meta.phone` in a one-time migration, vs relying solely on lazy parsing at read time.

* **Server incident follow-up:**

  * Investigate the observed `h11 LocalProtocolError: Too much data for declared Content-Length` during manual runs and determine which endpoint(s) need attention.
  * Clarify whether any 404s on `/app/transactions/summary`, `/dev/license`, `/dev/writes`, `/app/business_profile` are **expected stubs** or indicate missing endpoints that must be implemented and documented.

---

## 14) Unknowns / Not Specified

* Cross-platform paths (macOS/Linux).
* Exact status code for license rejections (smoke asserts “not 200”).
* Full domain model field list / minimal payload shapes for CRUD.
* Enum validation for `item_type` or stricter dedupe constraints for contacts (e.g., `(name, organization_id)`).
* `organization_id` FK action (`SET NULL` / cascade / restrict).
* SPDX variant (`AGPL-3.0-only` vs `AGPL-3.0-or-later`) for headers.
* Exact table name for the local analytics event store; SoT currently describes schema/usage only.
* **Pinned `pip` version** and final **Python version support matrix** across platforms; SoT requires “pinned to a single stable version” but the concrete version(s) remain TBA.
* Exact tool/process for generating `requirements.lock` (e.g. `pip-tools` / `pip-compile` vs `pip freeze`) and whether to record hashes/markers.
* Detailed design and flags for the **offline/cached install mode**, including cache directory layout and when it is triggered.

---

## HTTP API – Endpoints

### Auth / Session / UI

* **GET `/session/token`**

  * Returns the current session token as JSON: `{"ok": <bool>, "token": "<token>"}`.
  * Writes the token to `data/session_token.txt` for launcher reuse.
  * Public; callers must then send the token via `X-Session-Token` on subsequent protected calls.

* **GET `/session/token/plain`**

  * Returns the current session token as a raw `text/plain` string (no JSON wrapper).
  * Also writes the token to `data/session_token.txt`.

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

* All `/app/**` inherit `Depends(require_token_ctx)` and therefore **require a valid `X-Session-Token` header**; cookies may be set for convenience but the header is authoritative.

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

* **Custom headers:**

  * `X-Session-Token` on protected requests (all `/app/**`); this header is **authoritative** for auth decisions.
  * A session cookie may also be set for convenience, but tests and SoT assume the header is present.
  * Plugin API uses `X-TGC-Plugin-Name`, `X-TGC-License-URL`; bulk import auditing records `X-Plugin-Name`.

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
