# 01_SYSTEM_MAP

- Document purpose: Fast skeletal map of BUS Core runtime, canonical authority owners, trust boundaries, and the main drift paths that threaten stability.
- Primary authority basis: `core/api/http.py`, `launcher.py`, `core/ui/app.js`, `core/appdb/*`, `core/appdata/paths.py`, `core/runtime/core_alpha.py`, `core/runtime/manifest_trust.py`, `core/runtime/manifest_keys.py`.
- Best use: First read when locating canonical runtime surfaces or deciding where deeper truth lives.
- Refresh triggers: Entrypoint changes, router remounting, new mutable-state authority, startup-flow changes, new external service dependencies.
- Highest-risk drift areas: Split authority, session/auth drift, invoice payment/inventory authority drift, version/update drift, and repo-local mutable state outside AppData.
- Key dependent files / modules: `core/api/http.py`, `launcher.py`, `core/ui/app.js`, `core/config/manager.py`, `core/config/paths.py`, `core/appdb/engine.py`, `core/appdb/models_invoices.py`, `core/api/routes/invoices.py`, `core/runtime/core_alpha.py`, `core/runtime/manifest_trust.py`, `core/runtime/manifest_keys.py`.

## Project identity

- BUS Core is the sovereign local-first business utility runtime with a FastAPI backend and a static SPA frontend.
- Repository evidence shows active domains for inventory, ledger/stock, recipes, manufacturing, contacts/vendors, invoices, finance, backups/imports, plugin-backed file/Drive cataloging, and default-on / opt-out update checks.
- Native runtime is Windows-first (`launcher.py`, `BUS-Core.spec`); container runtime also exists (`Dockerfile`, `docker-compose.yml`) and defaults to host-loopback publishing.
- Current stabilization priority is preserving one canonical surface per concern and preventing parallel truths from reappearing through alternate entrypoints, duplicated state authority, or update/version ambiguity.

## System Authority Map

| Concern | Status | Authority location | Notes |
| --- | --- | --- | --- |
| Runtime HTTP surface | Canonical | `core/api/http.py::create_app()` and mounted routers | Referenced by `Dockerfile`, `docker-compose.yml`, `launcher.py`, and dev/smoke helper `scripts/launch.ps1`. |
| Native app entry | Canonical | `launcher.py` | Only supported native entry; starts BUS Core locally, opens `/ui/shell.html`, and manages tray lifecycle. |
| DB/app ownership | Canonical | `launcher.py` preflight plus app-level lock | Prevents two live BUS Core owners of the same DB/app root; verified next-start version handoff is evaluated only after this lock. |
| Container entry | Canonical | `Dockerfile` command `uvicorn core.api.http:create_app --factory`; `docker-compose.yml` publishes `127.0.0.1:8765:8765` by default | Only supported container entry; same HTTP surface as native runtime. Container-internal `0.0.0.0` bind is acceptable, but default host exposure is loopback-only. |
| Dev/smoke HTTP launcher | Secondary | `scripts/launch.ps1` | Scripted helper for smoke/dev automation against `core.api.http:create_app`; not a supported native runtime entry. |
| UI routing / boot | Canonical | `core/ui/app.js`, `core/ui/shell.html` | Hash routes, onboarding redirects, version badge, startup update check. |
| API contract | Canonical | Mounted routes in `core/api/http.py` and `core/api/routes/*` | Detailed in `02_API_AND_UI_CONTRACT_MAP.md`. |
| Persistence schema | Canonical | `core/appdb/models.py`, `core/appdb/models_recipes.py`, `core/api/http.py::startup_migrations()` | SQL files in `migrations/` are supplementary, not the only authority. |
| Invoice truth | Canonical | `core/appdb/models_invoices.py`, `core/services/invoices.py`, `core/api/routes/invoices.py` | Local invoice headers/lines/statuses are Core-owned. Invoice lines are billing records only, and paid invoices create one invoice-linked sale `CashEvent`; email, payment links, portals, sync, recurring billing, reminders, and automation remain outside Core. |
| UI theme variants | Presentation-only | `core/ui/js/theme.js`, `core/ui/js/cards/settings.js`, `core/ui/css/app.css` | The existing Settings theme dropdown is the only selector. Variant choice lives in browser `localStorage` as `bus.ui.themeVariant` and must not become backend config or business authority. |
| Durable settings config | Canonical | `%LOCALAPPDATA%\BUSCore\config.json` via `core/config/manager.py` | Root config is the single app-runtime settings authority; `%LOCALAPPDATA%\BUSCore\app\config.json` is legacy compatibility input only. |
| Session/auth authority | Claimed/unclaimed global gate implemented | `core/api/http.py::session_guard`, `core.api.http.require_token_ctx`, `GET /session/token`, `core/api/routes/auth.py`, `core/auth/*`, and `auth_*` tables | `core.api.http` owns the global gate. Zero users preserves legacy local `bus_session` behavior. One or more users requires valid DB-backed `bus_auth_session` for protected routes; legacy `bus_session` no longer grants `/app/*` access. `/session/token` is unclaimed compatibility only and returns `login_required` once claimed. See `04_SECURITY_TRUST_AND_OPERATIONS.md`. |
| Update check behavior | Canonical | `core/api/routes/update.py`, `core/services/update.py`, `core/config/manager.py` | Exact GET is public non-staging discovery. It preserves unsigned-manifest compatibility but performs an outbound request and changes local/remote evidence when executed. UI contract lives in `core/ui/js/update-check.js`. |
| Product telemetry | Canonical transport/state boundary with event-set drift | `core/telemetry/client.py`, `core/api/routes/telemetry.py` | Consent-gated schema-1.0 events use a bounded local queue and exact Lighthouse acknowledgement, independently of update-route analytics. Four repeatable restore/import outcomes exceed the current SOT-authorized signal set; see `OPERATIONS.md`. |
| Manifest authenticity, staging, and handoff | Canonical manual path | `core/runtime/manifest_trust.py`, `core/runtime/manifest_keys.py`, `core/services/update_stage.py`, `core/services/update_artifact.py`, `core/services/update_extract.py`, `core/services/update_exe_trust.py`, `core/services/update_promote.py`, `launcher.py`, `.github/workflows/release-mirror.yml` | Release publication signs manifests. Guarded manual staging verifies manifest, ZIP, extraction, EXE trust, and ready-state consistency; launcher policy may select a verified newer version on next start after DB lock. |
| Release version | Canonical | `core/version.py` | `VERSION` is the strict SemVer release authority; `INTERNAL_VERSION` is the working revision. |
| Repository governance and docs | Canonical hierarchy | `AGENTS.md`, `SOT.md`, `CHANGELOG.md`, `OPERATIONS.md`, then contract/maps/README/secondary docs | SOT defines intended behavior; code/tests must conform. Any conflict stops work and is reported rather than silently resolved. |

Stability in the current phase comes from keeping these authority lines singular and explicit. The main operational risks are split runtime authority, mutable-state drift outside canonical storage, auth drift between middleware and route-local enforcement, and release/update drift between code, docs, and published metadata.

## Top-level Repository Skeleton

| Path | Main ownership |
| --- | --- |
| `core/` | Product code: backend, frontend, DB schema, services, runtime, plugins, adapters. |
| `tgc/` | App state, tokens, settings, logging, compatibility shims. |
| `config/` | Repository-shipped policy/plugin config. |
| `data/` | Repo-local mutable state used by some subsystems (`index_state.json`, `settings_plugins.json`). |
| `migrations/` | Supplemental SQL migration snippets. |
| `plugins/`, `plugins_user/` | Plugin discovery roots. |
| `scripts/` | Build, smoke, launch, release, seed helpers. |
| `docs/` | Secondary docs; not primary authority over code. |
| `.github/` | CI/publish workflows and build/release agent instructions. |
| `license/` | Runtime-served EULA/license assets. |

## Runtime Components

| Component | Status | Owner / entry | Talks to |
| --- | --- | --- | --- |
| FastAPI app | Canonical | `core/api/http.py` | SQLite, journals, secrets, broker, UI static assets, update manifest host. |
| Native launcher | Canonical | `launcher.py` | FastAPI app, browser, tray icon, local port. |
| SPA shell | Canonical | `core/ui/shell.html`, `core/ui/app.js` | `/session/token`, `/app/*`, `/openapi.json`, `/license/EULA.md`. |
| SQLite persistence | Canonical | `core/appdb/engine.py`, `core/appdb/models*.py` | AppData DB files or `BUS_DB` override. |
| Journals / logs | Canonical | `core/journal/*`, `core/api/http.py`, `tgc/logging_setup.py` | `%LOCALAPPDATA%\BUSCore\app\data\journals`, runtime log files. |
| Broker / providers | Canonical | `core/domain/bootstrap.py`, `core/adapters/*`, plugin loader | Local FS, Google Drive, plugin services. |
| Background indexer | Canonical | `core/api/http.py` | `data/index_state.json`, broker catalog surfaces. |
| Update check path | Canonical | `core/services/update.py` | Hosted manifest URL from config; supports backward-compatible signed manifest shapes. |
| Product telemetry path | Canonical transport with event-set drift | `core/telemetry/client.py` | Fixed Lighthouse HTTPS endpoint, code-level allowlist, local queue/state/dead letter, and exact acknowledgement. The implemented allowlist includes four repeatable restore/import outcomes not authorized by the current SOT. |
| Removed legacy entry surfaces | Resolved | `app.py`, `tgc/http.py`, `core/main.py`, `tgc_controller.spec` | Deleted to prevent parallel runtime/package authority. |

## Startup and Request Skeleton

### Startup path

1. Native path: `launcher.py` prepares runtime dirs, acquires DB/app ownership, evaluates eligible verified-ready versions according to launch policy, then either hands off or calls `build_app()`, starts Uvicorn on `127.0.0.1:<port>`, and opens `/ui/shell.html`.
2. App build: `build_app()` creates `CoreAlpha`, sets `RUN_ID`, writes `session_token.txt`, sets `LOG_FILE`, and logs the trust banner.
3. App init: `create_app()` attaches `AppState`, mounts domain routers, and exposes static assets.
4. Lifespan: `startup_migrations()`, `_buscore_writeflag_startup()`, `ensure_core_initialized()`, `_auto_index_if_stale()`, `_start_indexer_event()`.
5. DB startup: demo DB may be seeded via `scripts/dev_seed.py`; declared tables and additive schema patches are ensured.

### Request path

1. `session_guard` allows public/bootstrap paths and the exact public `GET /app/update/check` exception without a cookie-backed session. For protected routes, zero auth users preserves legacy `bus_session`; one or more auth users requires a valid DB-backed `bus_auth_session` and attaches auth user/session context to `request.state`.
2. Correlation and maintenance middleware run before handlers.
3. Route handlers resolve DB sessions, services, and broker/providers as needed.
4. Domain mutations may write DB rows, journal entries, audit records, and runtime logs.
5. Exception handlers normalize error envelopes; request logging appends `[request]` lines.

### UI boot path

1. `DOMContentLoaded` binds update controls and invokes the one public startup update-check owner; the backend enforces saved startup policy and per-launch deduplication without an `/app/config` pre-read.
2. UI refreshes `/auth/state`; claimed mode without a current session shows login before normal protected app mounting.
3. Normal app mounting obtains mode-appropriate session state and reads `/openapi.json` for version display.
4. Initial route redirect checks `/app/system/state` once protected app access is available.
5. Demo mode plus missing local onboarding flag redirects to `#/welcome`; first-run disclosure governs product telemetry independently of the update-route GET.

## Component Interaction Edges

| Component | Direct dependencies | Owning files |
| --- | --- | --- |
| UI shell | Session bootstrap, system state, config, update check, domain APIs | `core/ui/app.js`, `core/ui/js/cards/*` |
| Inventory UI | Items, stock mutation, finance refund, vendor/contact lookup | `core/ui/js/cards/inventory.js`, `core/ui/js/api/canonical.js` |
| Manufacturing UI | Recipes, manufacture, ledger history | `core/ui/js/cards/manufacturing.js` |
| Invoices UI | Invoice list/detail, draft lines, issue, paid, void, print | `core/ui/js/cards/invoices.js` |
| Settings/Admin UI | Config, update check, DB export/import | `core/ui/js/cards/settings.js`, `core/ui/js/cards/admin.js` |
| HTTP app | DB engine, journals, secrets, broker, capability registry | `core/api/http.py` |
| `CoreAlpha` | Policy engine, journal manager, broker, plugin discovery, capability registry | `core/runtime/core_alpha.py` |
| Broker/providers | Local FS roots, Google credentials/tokens, plugin registry | `core/adapters/fs/provider.py`, `core/adapters/drive/provider.py`, `core/plugins/loader.py` |

## Trust Boundaries

| Boundary | Status | What crosses it |
| --- | --- | --- |
| Browser UI <-> local FastAPI | Canonical | Session cookie, same-origin SPA API calls, static assets. Default CORS is limited to explicit loopback origins only for local/dev browser-origin access. |
| FastAPI <-> local DB/files | Canonical | DB writes, exports/imports, journals, logs, secrets, config. |
| FastAPI <-> OS actions | Canonical | Tray/browser launch, Explorer open, process exit/restart, local path validation. |
| FastAPI <-> external network | Canonical | Configured update-manifest and declared artifact fetches, fixed Lighthouse product telemetry, Google OAuth/token exchange, and Google Drive API calls. All remain optional to normal local operation. |
| Docker host publish <-> local network | Canonical default | Compose publishes BUS Core to `127.0.0.1` only. LAN/public exposure is unsafe by default and requires explicit advanced operator action plus stronger access controls. |
| Runtime authority | Canonical | `launcher.py` (native), `core/api/http.py::create_app()` (HTTP surface), and Docker `uvicorn core.api.http:create_app --factory` are the only supported runtime paths. |

## Coupling Hotspots

| Hotspot | Status | Why it matters | Own in |
| --- | --- | --- | --- |
| Config authority (`config.json` vs `app\\config.json`) | Resolved | `%LOCALAPPDATA%\BUSCore\config.json` is canonical; `%LOCALAPPDATA%\BUSCore\app\config.json` is legacy compatibility input only. | `03_DATA_CONFIG_AND_STATE_MODEL.md` |
| Session/token split | Claimed-mode gate implemented | `core.api.http` is the canonical validator authority, `AppState.tokens` is the legacy unclaimed token source, `tgc.security.require_token_ctx` is a compatibility wrapper, and DB-backed `auth_sessions` are claimed-mode authority. `/session/token` remains unclaimed compatibility only and returns `login_required` once claimed. | `04_SECURITY_TRUST_AND_OPERATIONS.md` |
| Version/update authority drift | Narrowed drift | `core/version.py` is the public release/update source, release publication signs manifests, guarded staging verifies artifacts/EXE trust, and next-start handoff is live. Remaining limits include unsigned compatibility for discovery checks, stable-only manifest publication, release-history dependence on GitHub assets, and separate Docker release governance. | `05_RELEASE_UPDATE_AND_DEPLOYMENT_FLOW.md` |
| Invoice authority drift | Canonical boundary added | Core now owns local invoice truth, but invoice lines must remain billing-only records and invoice payment truth must remain one invoice-linked sale `CashEvent`; sending, payment processing, portals, sync, recurring billing, reminders, and automation are outside Core. | `02_API_AND_UI_CONTRACT_MAP.md`, `03_DATA_CONFIG_AND_STATE_MODEL.md` |
| Repo-local mutable state | Drifted | Some live state is stored in repo `data/` instead of AppData. | `03_DATA_CONFIG_AND_STATE_MODEL.md` |
| Placeholder/stale UI surfaces | Drifted | `#/runs`, `#/import`, backup UI, and stub transaction widgets can mislead contract assumptions. | `02_API_AND_UI_CONTRACT_MAP.md` |
| Runtime authority | Canonical | Legacy alternate entry surfaces were removed; `scripts/launch.ps1` remains dev/smoke-only around the canonical factory. | This file |

In practice, the main stability failures to guard against are split authority, mutable-state drift, auth drift, and release/update drift. The architecture shape does not need expansion here; it needs clearer authority boundaries and fewer competing truths.

## Freeze Notes

- Refresh on: entrypoint changes, router remounting, new runtime services, trust-boundary changes, or path-authority changes.
- Fastest invalidators: switching the canonical entrypoint, consolidating config/session authority, changing mounted route roots, or replacing the SPA shell.
- Check alongside: `02_API_AND_UI_CONTRACT_MAP.md` for route truth, `03_DATA_CONFIG_AND_STATE_MODEL.md` for storage authority, `04_SECURITY_TRUST_AND_OPERATIONS.md` for auth/trust splits, `05_RELEASE_UPDATE_AND_DEPLOYMENT_FLOW.md` for version/update authority.
