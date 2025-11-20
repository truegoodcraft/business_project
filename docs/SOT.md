# TGC BUS Core — Source of Truth (Final)

> **Authority rule:** The uploaded **codebase is truth**. Where documents conflicted, you selected resolutions below. Anything not stated = **unknown / not specified**.

# TGC BUS Core — Source of Truth (Final)

> **Authority rule:** The uploaded **codebase is truth**. Where documents conflicted, resolutions below reflect code. Anything not stated = **unknown / not specified**.

---

## 1) Identity & Naming

- **Company / Owner:** True Good Craft (**TGC**)
- **BUS acronym:** **Business Utility System**
- **Product name (canonical):** **TGC BUS Core**
- **Short form (UI):** **BUS Core**
- **Extended (docs, when needed):** **TGC BUS Core – Business Utility System Core by True Good Craft**

---

## 2) Baseline & Version

- **Current version:** **v0.5.0** (from `VERSION`).
- **Project baseline:** **Post-v0.5**.

---

## 3) Scope & Non-Goals

- **Local app** (FastAPI + SQLite).
- **No telemetry / external network calls:** not implemented; policy is to avoid.
- **Background automation:** allowed only for a one-shot **index-stale scan at startup**. No periodic schedulers/auto-crawls beyond that.
- Anything else: **not specified**.

---

## 4) Architecture & Runtime

- **Backend:** FastAPI; SQLite via SQLAlchemy.
- **Auth/session:** session token required; 401 retry flow present.
- **Writes guard:** explicit “writes enabled” gate exists.
- **Business logic location:** **Core** service.
- **Plugin loader:** present; business features live in core.
- **Default local base URL:** `http://127.0.0.1:8765`.

---

## 5) UI — Source of Truth (Binding, Zero-Drift)

**Authority:** This section is law for UI. If UI code disagrees with this section, UI code is considered wrong until this section is updated first or Implementation Gaps call it out explicitly.

> **Note:** RFQ UI is currently **partial/stub** and there is a known **“token/401/F5” UI bug status: unknown**. Those are treated as implementation gaps, not contradictions.

### 5.1 Shell & routing invariants

- **One shell:** `core/ui/shell.html` is the **only** HTML shell served at `/ui/shell.html`.  
  No alternate SPA entry is allowed without a SoT update.
- **One entry script:** `core/ui/app.js` is the **only** UI entry module:
  - Owns routing (`getRoute()`), boot, hashchange handling, and the top-level `navigate` behavior.
- **Hash routing only:**
  - All navigation is via `location.hash` (e.g. `#/home`, `#/inventory`, `#/contacts`).
  - No history API / path-based routing is defined in SoT.
- **Screens vs. cards:**
  - The UI is organized into **screen wrappers**:
    - `[data-role="home-screen"]`
    - `[data-role="inventory-screen"]`
    - `[data-role="contacts-screen"]`
    - `[data-role="tools-screen"]` (legacy, normally hidden)
  - Within screens, multiple **cards/panels/modals** may be visible at the same time.
  - SoT **does not enforce** a global “only one card on screen” rule.
  - For main navigation, SoT expects **exactly one of Home / Inventory / Contacts** to be the *primary* visible screen for its route (see table below).
- **License badge:**
  - Top bar contains an element with `data-role="license-badge"` (currently `#license-badge`).
  - On boot, UI calls `GET /dev/license` with `X-Session-Token` and updates this badge to `License: <tier>` (fallback: `community`).

### 5.2 Canonical routes (2025-11-19 — edit this table first)

This table is the **binding map** from hash routes → primary screen → JS entry. Any change to routes, screen roles, or mount functions must update this table **before** code changes land.

| Route / state         | Primary screen            | `data-role`        | Card / JS file                        | Mount function         | License surface (intent)       |
|-----------------------|---------------------------|--------------------|----------------------------------------|------------------------|--------------------------------|
| _No hash_ / `#/home`  | Home                      | `home-screen`      | `core/ui/js/cards/home.js`            | `mountHome()`          | None                           |
| `#/BUSCore`           | Home (alias)              | `home-screen`      | `core/ui/js/cards/home.js`            | `mountHome()`          | None                           |
| `#/inventory`         | Inventory (items + bulk)  | `inventory-screen` | `core/ui/js/cards/inventory.js`       | `mountInventory()`     | **Planned Pro** for `Run` / recipes (`POST /app/inventory/run`) |
| `#/contacts`          | Contacts (vendors/people) | `contacts-screen`  | `core/ui/js/cards/vendors.js`         | `mountContacts()`      | None (all `/app/vendors` CRUD free) |
| `#/settings`          | Settings / Dev (planned)  | _TBD_ (currently none wired) | `core/ui/js/cards/settings.js` (planned), `core/ui/js/cards/dev.js` | _TBD_ (no mount wired yet) | None (diagnostic only)        |

**Aliases and normalization:**

- `getRoute()` in `app.js`:
  - Strips `#/`.
  - Treats `''`, `'home'`, and `'BUSCore'` as route `home`.
  - Treats `'settings'` as base `dev`. As of this SoT, `dev` is a **reserved base** intended for a future Settings/Dev screen; there is currently **no bound screen** for `dev`, which is an implementation gap.

**Deliberate omissions (current reality):**

- There is **no** canonical `#/items` route:
  - Items list is part of the **Inventory** experience and lives under `#/inventory`.
- There is **no** canonical `#/vendors` route:
  - Vendors are represented as **contacts**; all vendor CRUD flows run via `/app/vendors`, UI surface lives under `#/contacts`.
- There is **no** canonical `#/tasks` or `#/rfq` hash route yet:
  - Tasks and RFQ UI live as **cards** inside the legacy Tools area; they do not have independent routes.
  - RFQ UI remains **partial/stub**, while backend `POST /app/rfq/generate` exists.
  - Any future dedicated `#/tasks` or `#/rfq` route must be added to this table first.

### 5.3 Tools drawer — exact structure & behavior (2025-11-19)

**Sidebar structure (`#sidebar`):**

- Brand:
  - `<a href="#/BUSCore" data-link="brand-home">BUS Core</a>`
  - Behavior: always navigates to the **Home** route (`#/BUSCore` → canonical `home`).
- Nav items (minimum required):
  - **Tools drawer:**
    - `<a href="#" data-link="tools" data-action="toggle-tools">Tools</a>`
    - Below it: `<ul data-role="tools-subnav" class="hidden drawer">…</ul>`
  - **Settings:**
    - `<a href="#/settings" data-role="nav-link" data-route="dev">Settings</a>`

**Tools drawer contents (canonical):**

Inside `[data-role="tools-subnav"]`:

| Label     | Element selector            | Target route   |
|----------|-----------------------------|----------------|
| Inventory | `[data-link="tools-inventory"]` | `#/inventory`  |
| Contacts | `[data-link="tools-contacts"]`   | `#/contacts`   |

**Drawer behavior:**

- Opening Tools:
  - Clicking the **Tools** label toggles `[data-role="tools-subnav"]` `.hidden` class.
  - **Must not** change `location.hash`.
- Selecting an item (Inventory / Contacts):
  - Sets `location.hash` to the target route (`#/inventory` or `#/contacts`).
  - Forces the drawer closed (adds `.hidden` to `[data-role="tools-subnav"]`).
- The Tools drawer is the **only** sanctioned way to navigate to Inventory and Contacts from the sidebar (aside from direct URL entry).

**Legacy Tools screen:**

- `shell.html` still contains a legacy Tools page:

  - `<div data-role="tools-screen" class="hidden">…</div>`
  - `section data-route="tools"` with nested tabs (`data-role="tools-tabs-root"`, Tasks/Manufacturing/Backup).

- SoT state:

  - This Tools page is **legacy** and must remain hidden in normal flows.
  - `showScreen('tools')` is not used for any route in `onRouteChange()`; `#/tools` is **not** a canonical route.
  - No new logic may depend on `tools-screen` being visible, unless SoT is updated to make it a first-class screen again.

### 5.4 License & UI gating style (soft, user-friendly)

**License badge behavior:**

- On startup, `app.js` must:

  1. Acquire a token via `ensureToken()` (which in turn hits `/session/token` if needed).
  2. Call `GET /dev/license` with header `X-Session-Token`.
  3. Parse the LICENSE dict and update the element `[data-role="license-badge"]` to a human-readable string:
     - Preferred: `License: <tier>` (e.g., `License: community`).
     - If the call fails or tier cannot be determined → fallback: `License: community`.

- Badge is **informational** only; it does not block UI behavior.

**Gating policy (UI intent):**

- **Actual enforcement** of Pro vs Community is on the backend (see §7 Licensing).
- UI must **not** hide Pro-only features; instead it must:

  - Keep Pro surfaces **visible**.
  - Use soft affordances:
    - Greyed / disabled buttons for Pro-only actions when on `community`.
    - Small “Pro” badge or pill near Pro-only actions.
    - Optional tooltip such as “Available in paid tier”.

- For this version:

  - Pro-only backend endpoints are:
    - `POST /app/rfq/generate`
    - `POST /app/inventory/run`
    - `POST /app/import/commit`
  - UI **should** treat actions that call those endpoints as Pro surfaces and visually mark them once gating is wired.

**Implementation state (2025-11-19):**

- Backend license gating is **not yet enforced in code** (see §12 Implementation Gaps).
- UI currently:
  - Shows a license badge.
  - Does **not** yet disable/mark Pro controls in a tier-aware way.
- This section describes the **intended** UI style once gating is wired. Any Pro gating visuals implemented must follow this soft style.

**Token/401/F5 bug:**

- There is a known but not fully diagnosed behavior around:
  - Token handling,
  - 401 responses,
  - Manual `F5` reloads.
- SoT position: **bug status is unknown**; there is no formal spec here yet. Fixing this will require:
  - A separate SoT update describing the desired session refresh behavior,
  - Then matching UI/HTTP behavior.

### 5.5 Safe iteration rules (flexible but recorded)

These are **process guardrails** to keep the UI from drifting. Any UI PR must follow them unless a SoT update explicitly changes this section.

1. **Prototype freely in branches.**
   - You can spike layouts, new cards, and styling **inside screens** without changing routes or data-role wrappers.
2. **Before merging any change that affects:**
   - Hash routes,
   - Which `data-role` wrapper maps to which route,
   - Tools drawer structure / labels / order,
   - Pro surface visibility / license badge behavior,

   → **Update §5.2–5.4 first** (this UI section), then adjust code to match.

3. **Commit message convention:**
   - Any commit that updates this section of the SoT must contain:
     - `ui(sot):` in the message.
4. **Smoke must stay 100%.**
   - `buscore-smoke.ps1` remains the acceptance gate for backend + minimal UI presence (see §10).
   - UI changes must not break:
     - `/ui/shell.html` returning 200 + non-empty body,
     - Auth/token flow used by smoke.
5. **New Pro surface = new negative test:**
   - If UI exposes a new Pro-only action tied to a gated endpoint, a corresponding **community-tier negative test** must be added in `buscore-smoke.ps1` (or companion scripts) to assert “not 200” for that action under default `community`.
6. **No unnamed surfaces:**
   - If UI code introduces:
     - A new hash route,
     - A new primary screen (`data-role="…-screen"`),
     - A new license-dependent button,
   - Then SoT must either:
     - Add it to the tables in §5.2 / §5.3 / §7, or
     - Declare it explicitly as **removed/legacy** and delete the code.
7. **Legacy cleanup rule:**
   - Legacy fragments such as `<section data-route="tools">` and `data-role="tools-screen"` may be removed **only** when:
     - They are not referenced in `app.js`, and
     - This section has been updated to remove mentions of them, and
     - A PR explicitly notes their removal (e.g., `ui(clean): drop legacy tools screen`).

---

## 6) Features — Current Status

- **RFQ generation:**
  - Backend implemented: `POST /app/rfq/generate`.
  - UI: **partial/stub** (no dedicated route; lives in Tools card area).
- **Inventory runs (batch/recipes):**
  - Backend implemented: `POST /app/inventory/run`.
  - UI: exposed within Inventory card; Pro gating not yet applied.
- **Encrypted backup & restore:** implemented
  - `POST /app/export` (AES-GCM; Argon2id/PBKDF2)
  - `POST /app/import/preview`
  - `POST /app/import/commit` (audited)
- **Domain CRUD:**
  - Vendors/Items/Tasks present.
  - UI↔API parity not fully aligned (see §12 Implementation Gaps).

---

## 7) Licensing

- **Default tier:** `community`.
- **License file (Windows):** `%LOCALAPPDATA%\BUSCore\license.json`.
- **Gating policy (v1):** gate specific endpoints only:
  - `POST /app/rfq/generate`
  - `POST /app/inventory/run` — gates batch/recipes  
    _Note: simple one-off qty `PUT /app/items/{id}` remains **community (free)**._
  - `POST /app/import/commit`
  - `POST /app/import/preview` stays **free/community** (by license) and still respects the **writes toggle**.
- **Implementation state:** license gating **not yet enforced in code**.

---

## 8) Security & Policy

- **Session token** on all app routes; 401 retry in UI.  
  **Exception:** `/health` remains public (no dependency); header presence only selects payload (see below).
- **Writes guard** on mutating ops.
- **Health (single, token-aware route):**
  - **GET `/health`**
    - **No `X-Session-Token` header:** return `{"ok": true}` (200).
    - **With `X-Session-Token` header present:** return `_health_details_payload()` (200) with **top-level keys**: `version`, `policy`, `license`, `run-id`.
    - **No token validation** is required for this route; presence of the header alone switches to the detailed payload.
- **Audit** lines on import commit.
- Anything else: **not specified**.

---

## 9) Launcher

- **Responsibilities (packaging/ops):**
  - Create default license if missing: `{"tier":"community","features":{},"plugins":{}}` at `%LOCALAPPDATA%\BUSCore\license.json`.
  - Detect/focus existing instance (**planned**).
  - Provide an updater stub (**planned**).
  - Start server, open UI, and log.
- **Development & smoke usage:** **do not use launcher** for dev/smoke. See §10 for canonical flow.
- **Implementation state:** bootstrap/focus/updater not yet implemented (current: starts/opens/logs only).

---

## 10) Testing & Smoke Harness (authoritative for dev/test)

- **Canonical harness:** `buscore-smoke.ps1` at repo root. Must pass **100%** for acceptance.
- **Auth pattern:**
  - Mint via `GET /session/token`.
  - Send **`X-Session-Token`** on protected calls (tests don’t rely on cookies).
- **Success policy (smoke):**
  - Treat **`200 OK`** as CRUD success.
  - Other **2xx = fail** (smoke rule).
- **Diagnostics:** for any non-200 response, smoke prints the **first 200 bytes** of the body with the status.
- **Readiness wait:** smoke waits on `/session/token` (up to ~30s) before assertions.
- **UI presence:** `/ui/shell.html` returns 200 with non-empty body.

**Path enforcement (hard cutover):**

- **Fail** if any `\%LOCALAPPDATA%\TGC\*` path exists after a run.
- **Ensure** `\%LOCALAPPDATA%\BUSCore\secrets` and `\%LOCALAPPDATA%\BUSCore\state` exist (create if needed).
- On success, print **`paths: hard cutover validated`**.

**Health assertions (single route):**

- `health(public)`: status 200; body `{"ok": true}` seen: **True**.
- `health(protected)`: status 200; keys `[version, policy, license, run-id]` present: **[True, True, True, True]**.

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
