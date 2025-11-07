# TGC BUS Core — Source of Truth (Final)

> **Authority rule:** The uploaded **codebase is truth**. Where documents conflicted, you selected resolutions below. Anything not stated = **unknown / not specified**.

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
* **No background automation/schedulers/auto-crawls** (explicit user-trigger only).
* **No telemetry / external network calls**: not implemented; policy is to avoid.
* Anything else: **not specified**.

## 4) Architecture & Runtime

* **Backend:** FastAPI; SQLite via SQLAlchemy (as in code).
* **Auth/session:** session token required; 401 retry flow present.
* **Writes guard:** explicit “writes enabled” gate exists.
* **Business logic location:** **Core** service (resolved).
* **Plugin loader:** present; **business features live in core** per decision.

## 5) UI

* **Entry:** **`core/ui/shell.html`** (ESM) is the current shell.
* **RFQ UI:** **partial/stub**; backend exists.
* **UI bug status (token/401/F5):** **Unknown** (not runtime-verified).

## 6) Features — Current Status

* **RFQ generation:** **Backend implemented** (`POST /app/rfq/generate`); **UI incomplete**.
* **Inventory runs (batch/recipes):** **Backend implemented** (`POST /app/inventory/run`).
* **Encrypted backup & restore:** **Implemented**

  * `POST /app/export` (passworded AES-GCM; Argon2id/PBKDF2 KDF)
  * `POST /app/import/preview`
  * `POST /app/import/commit` (audited).
* **Domain CRUD:** Present for vendors/items at minimum; exact parity between UI expectations and server routes is **not fully aligned** (see gaps).

## 7) Licensing

* **Tier (default):** **`community`**.
* **License file path (Windows):** **`%LOCALAPPDATA%\BUSCore\license.json`**.
* **Pricing:** **Not specified** (omit).
* **Gating policy (v1):** **Gate specific endpoints only** (below).
* **Gated endpoints (authoritative list):**

  1. `POST /app/rfq/generate`
  2. `POST /app/inventory/run` — **gates batch / recipe runs**

     * **Note:** simple one-off qty via `PUT /app/items/{id}` remains **community (free)**
  3. `POST /app/import/commit`

  * `POST /app/import/preview` stays **free/community**.
* **Implementation state:** **License gating not yet enforced in code** (to be added).

## 8) Security & Policy

* **Session token** on all app routes; 401 retry in UI.
* **Writes guard** for mutating operations.
* **No background automation**; all actions are user-initiated.
* **Audit** lines on import commit.
* Anything else: **not specified**.

## 9) Launcher

* **Required responsibilities (decision):**

  * Create default license file if missing at `%LOCALAPPDATA%\BUSCore\license.json` with `{"tier":"community","features":{},"plugins":{}}`.
  * Detect/focus existing instance.
  * Provide a **future updater** mechanism.
  * Start server, open UI, and log.
* **Implementation state:** **License bootstrap/focus/updater not yet implemented** (code currently starts/opens/logs).

## 10) Implementation Gaps (to reconcile decisions with code)

* **License gating:** Add checks around the three gated endpoints; expose tier/flags to UI to lock controls.
* **Launcher scope:** Add license bootstrap, instance focus, and updater stub.
* **RFQ UI:** Complete client workflow (inputs → call → results/attachments).
* **Items CRUD alignment:** UI expects `/app/items` GET/POST/PUT and simple qty PUT on `/app/items/{id}`; server currently emphasizes bulk preview/commit + delete. Implement missing endpoints **or** adjust UI to current API while keeping the **free** one-off qty rule.

## 11) Unknowns / Not Specified

* Cross-platform paths for license/config (macOS/Linux): **not specified**.
* Comprehensive list of all domain models and fields: **not specified**.
* Any scheduler/cron design: **intentionally none** (banned).
* Exact UI navigation/sections beyond shell/app: **not specified**.

---

**End of Source of Truth.**
Edits require explicit updates here; unspecified areas remain **unknown** until defined.







HTTP API – Endpoints
Auth / Session / UI
GET /session/token — session_token returns the current token as JSON, while get_session_token (app entry point) overrides the path to mint a UUID, persist it to data/session_token.txt, and set the X-Session-Token cookie for the browser. Public endpoint with no dependency checks.

GET /health — health returns {"ok": True} for liveness checks; public.

GET /, GET /ui, GET /ui/index.html — _root, ui_root, and ui_index redirect all root traffic to /ui/shell.html to load the SPA shell.

GET /ui/plugins/{plugin_id}[/{resource_path}] — ui_plugin_asset serves static assets from plugin UI folders, returning 404 when a resource is missing.

Dev / Diagnostics
GET /dev/license — first dev_license reloads the license file and returns it with the resolved path; a later redeclaration returns the cached LICENSE dict. Neither instance enforces authentication beyond best-effort token loading.

GET /dev/writes — implemented twice: the async version calls require_token and reports the in-memory flag, while the later sync version refreshes from disk without requiring auth. Both surface the writes-enabled toggle.

POST /dev/writes — both definitions accept {"enabled": bool} and persist the flag via set_writes_enabled, allowing the UI to flip write access.

GET /dev/paths — dev_paths enumerates key filesystem roots (BUS_ROOT, DATA_DIR, etc.) for diagnostics.

GET /dev/journal/info — journal_info (protected router) tails data/journals/inventory.jsonl to aid troubleshooting.

GET /dev/ping_plugin — dev_ping_plugin launches a sandboxed Windows plugin host to verify broker connectivity; only available when Windows primitives are present.

App Domain (/app/**)
All /app/** endpoints inherit Depends(require_token_ctx) through SessionGuard and the router inclusion, so callers must supply X-Session-Token.

GET /app/app/vendors, POST /app/app/vendors — compatibility aliases (get_vendors, create_app_vendor) that fetch or create vendors using the legacy /app/vendors path pattern; they rely on SQLAlchemy models and session tokens.

POST /app/transactions, GET /app/transactions, GET /app/transactions/summary — expense-only add_transaction, paginated list_transactions, and windowed transactions_summary maintain and report on the SQLite transactions table.

GET /app/vendors, POST /app/vendors, PUT /app/vendors/{vendor_id}, DELETE /app/vendors/{vendor_id} — vendor CRUD with conflict handling and optimistic updates via SQLAlchemy (list_vendors, create_vendor, update_vendor, delete_vendor).

POST /app/items/bulk_preview, POST /app/items/bulk_commit — bulk import helpers that parse CSV/XLSX uploads, write import previews, emit plugin audit entries (respecting X-Plugin-Name), and journal row outcomes to bulk_import.jsonl. Both enforce an authenticated session via _ensure_session.

GET /app/items, POST /app/items, PUT /app/items/{item_id}, DELETE /app/items/{item_id} — item CRUD (list_items, create_item, update_item, delete_item) with vendor validation and null-safe quantity updates.

GET /app/tasks, POST /app/tasks, PUT /app/tasks/{task_id}, DELETE /app/tasks/{task_id} — task management bound to items via _require_item, supporting status/due-date updates and deletion.

GET /app/attachments/{entity_type}/{entity_id}, POST /app/attachments/{entity_type}/{entity_id}, DELETE /app/attachments/{attachment_id} — attachment APIs validating entity existence before listing, creating, or deleting attachment rows.

POST /app/export — app_export wraps export_db to produce encrypted database archives; depends on require_writes so writes must be enabled.

POST /app/import/preview, POST /app/import/commit — invoke _import_preview/_import_commit to decrypt and restore exports, with write gating for both stages.

POST /app/rfq/generate — rfq_generate collects items/vendors, renders Markdown/PDF RFQs, saves them under exports, and returns the file stream; requires session token and writes enabled.

POST /app/inventory/run — inventory_run applies batch deltas to item quantities and journals the run (including inputs/outputs) to data/journals/inventory.jsonl; requires token and write access.

Reader / Organizer
Protected via the protected router dependency on require_token_ctx.

POST /reader/local/resolve_ids, POST /reader/local/resolve_paths — translate between local filesystem paths and reader IDs using the configured allowed roots.

POST /organizer/duplicates/plan, POST /organizer/rename/plan — crawl permitted directories, build MOVE/RENAME Plan actions, and persist them via save_plan for later execution.

Settings, Catalog, and Indexing
GET/POST/DELETE /settings/google — expose Google Drive OAuth client configuration, masking stored secrets and using the encrypted Secrets manager; responses disable caching.

GET/POST /settings/reader — read and persist reader configuration, updating the allowed local roots list when provided.

POST /catalog/open, POST /catalog/next, POST /catalog/close — thin proxies over the broker’s catalog APIs with argument validation for source, stream ID, and paging limits.

GET/POST /index/state, GET /index/status — load/update the JSON index state file, compute signatures/tokens via _index_status_payload, and report synchronization status for drive and local roots.

GET /drive/available_drives — fetches Google Drive listings from the broker’s google_drive provider.

OAuth (Google Drive)
POST /oauth/google/start — creates a consent URL and per-flow state HMAC, requiring a valid session token before returning the auth URL.

GET /oauth/google/callback — validates the returned state, exchanges the code for tokens, stores the refresh token via Secrets, and redirects back to the UI.

POST /oauth/google/revoke, GET /oauth/google/status — revoke stored refresh tokens (best-effort) and report connection status; both clear caches when revoking.

Policy, Plans, and Health
GET/POST /policy — load or persist policy settings stored under %LOCALAPPDATA%\BUSCore\config.json.

POST /plans, GET /plans, GET /plans/{plan_id}, POST /plans/{plan_id}/preview, POST /plans/{plan_id}/commit, POST /plans/{plan_id}/export — full plan lifecycle including draft creation, preview stats, guarded commit via require_owner_commit, and JSON export of plan details.

GET /health (protected) — returns version, policy snapshot, and license identifiers with the current run ID.

Plugins, Capabilities, and Automation
GET /plugins, POST /plugins/{service_id}/read, POST /plugins/{pid}/enable — list plugins, invoke plugin read operations (respecting enablement), and toggle plugin state through the loader APIs.

POST /probe — orchestrates service probes, merges reader probe results, and updates the capability registry manifest.

GET /capabilities, POST /execTransform, POST /policy.simulate, POST /nodes.manifest.sync, GET /transparency.report, GET /logs — emit signed capability manifests, execute plugin transforms with policy outcomes, simulate policy decisions, validate manifest signatures, surface transparency reports, and tail recent logs.

Local Filesystem & Control
GET /local/available_drives, GET /local/validate_path, POST /open/local — enumerate OS drives, validate directory paths, and open local items via explorer/xdg-open while enforcing allowed root restrictions.

POST /server/restart — schedules a process exit using a short timer so the launcher can restart the service.

Helpers and Core Utilities
SessionGuard middleware and associated helpers (require_token, require_token_ctx, _require_session, get_session_token) enforce X-Session-Token on every non-public route and attach session data to the request state.

require_writes consults get_writes_enabled so mutating endpoints can honor the writes toggle, with /dev/writes persisting the flag in config.json.

License utilities (_license_path, get_license, feature_enabled) read %LOCALAPPDATA%\BUSCore\license.json (or BUS_ROOT) and normalize tier/feature metadata.

Backup/restore helpers (export_db, import_preview, import_commit) create encrypted archives, validate imports, and guard against path traversal under %LOCALAPPDATA%\BUSCore.

_ensure_transactions_table, journal_mutate, _append_plugin_audit, and the bulk-import helpers normalize rows, write audit trails (bulk_import.jsonl, plugin_audit.jsonl), and capture preview files in data/imports.

Index utilities (compute_local_roots_signature, _index_status_payload, _catalog_background_scan, _run_background_index) manage sync state, derive local root hashes, and can schedule background catalog scans when the index is stale.

Policy helpers (load_policy, save_policy, require_owner_commit) gate plan commits on write enablement and optional owner-only enforcement via BUS_POLICY_ENFORCE.

Plan storage (save_plan, get_plan, list_plans) persists plans in %LOCALAPPDATA%\BUSCore\buscore.db, while preview_plan and commit_local compute action stats and execute filesystem operations under allowed roots.

get_session (SQLAlchemy dependency) yields scoped sessions against the SQLite database resolved via _resolve_db_path.

get_broker initializes the plugin broker singleton with secrets, capability registry, and reader settings loaders.

Secrets manager stores encrypted secrets under %LOCALAPPDATA%\TGC\secrets (or ~/.tgc/secrets) with optional OS keyring integration.

Reader settings utilities (load_settings, save_settings, get_allowed_local_roots, set_allowed_local_roots) keep settings_reader.json synced across requests.

Headers, Files, and Config Conventions
Custom headers: X-Session-Token is set as an HTTP-only cookie on login and expected on all protected requests; middleware adds X-TGC-License and X-TGC-License-URL, and bulk import auditing records X-Plugin-Name.

License file: %LOCALAPPDATA%\BUSCore\license.json (or BUS_ROOT\license.json when BUS_ROOT is set) storing tier, features, and plugins.

Runtime paths: BUS_ROOT, APP_DIR, DATA_DIR, JOURNALS_DIR, IMPORTS_DIR, and DB_PATH derive from %LOCALAPPDATA%\BUSCore\app; directories are created on startup.

Backup artifacts: encrypted exports land under %LOCALAPPDATA%\BUSCore\exports, with journals in data/journals and import previews in data/imports.

Inventory runs append to data/journals/inventory.jsonl, providing an audit trail for quantity changes.

Session token persistence: both the main app and helper utilities write the active token to data/session_token.txt so the launcher can reuse it.

Reader settings stored at %LOCALAPPDATA%\BUSCore\settings_reader.json; policy config at %LOCALAPPDATA%\BUSCore\config.json.

Capability manifests and HMAC key live under %LOCALAPPDATA%\TGC\state, while secrets fall back to %LOCALAPPDATA%\TGC\secrets / ~/.tgc/secrets.

Index state JSON resides at data/index_state.json, updated via the index endpoints.

Naming & Conventions (Best-Use Cheat Sheet)
Domain APIs mount under /app/**, with the router applying Depends(require_token_ctx) so every call must include X-Session-Token.

All other feature routers (protected plus reader/organizer) add the same session-token dependency via require_token_ctx. Mutating endpoints layer require_writes on top, and the /dev/writes toggle updates the persisted flag.

Bulk import flows always log to data/journals/bulk_import.jsonl and plugin_audit.jsonl, capturing the acting plugin via X-Plugin-Name.

Plan workflows follow a Preview → Commit pattern, storing stats in the plan record before execution and invoking commit_local under policy guardrails.

License tiers default to "community" with feature flags expressed as booleans in license.json.

Inventory adjustments are always journaled with timestamps, input/output maps, and delta calculations for traceability.

Index freshness relies on hashing normalized local roots and Google Drive tokens; divergences trigger background scans unless a task is already running.

SoT vs Code – Alignment / Mismatch Notes
Matches
SoT calls out POST /app/rfq/generate as implemented; the server provides the endpoint with token and write guards, generating Markdown/PDF exports as described.

SoT lists POST /app/inventory/run; the implementation adjusts inventory quantities and journals the snapshot.

Encrypted backup and restore endpoints (/app/export, /app/import/preview, /app/import/commit) exist with AES-GCM containers and manifest validation, matching SoT expectations.

Writes gating is present via require_writes and the /dev/writes toggle, aligning with the SoT requirement for a user-controlled write guard.

Vendor and item CRUD APIs are available under /app/vendors and /app/items, fulfilling the SoT baseline for domain CRUD operations.

Missing in code
None observed relative to the supplied SoT.

Not in SoT (yet)
Task and attachment management endpoints (/app/tasks, /app/attachments) extend the domain beyond the SoT’s minimum scope.

Developer diagnostics like /dev/paths and /dev/journal/info provide extra tooling not covered by the SoT narrative.

Plugin, capability, and automation APIs (/plugins, /probe, /execTransform, etc.) are fully implemented even though they are not highlighted in the current SoT summary.

Organizer and reader utility endpoints (/organizer/**, /reader/local/**) exist for filesystem plan generation and path mapping but are absent from the SoT feature list.

Conflicts
The SoT specifies that POST /app/import/preview should remain a community (free-tier) operation, yet the implementation requires require_writes, meaning the write toggle must be enabled before running a preview.

The SoT bans background automation, but _auto_index_if_stale schedules a background indexing task on startup whenever the index is deemed outdated.
