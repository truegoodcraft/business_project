# BUS Core Transparency Report

BUS Core is local-first software. This document summarizes runtime data flow and points operators to the current evidence authorities. `SOT.md` governs behavior; `OPERATIONS.md` governs side-effect-aware diagnosis.

## Identity and runtime

- Public version comes from `core/version.py::VERSION` and is returned by public `GET /health`.
- `/health` proves process reachability and public version only. Every HTTP call is request-logged.
- Policy loads from `config/policy.json`.
- Each runtime launch creates a run identifier and a per-run log under the configured AppData runtime root.
- Native Windows launch authority is `launcher.py`; container authority is the same FastAPI factory through the governed container command.

Starting BUS Core is an operational action, not a passive diagnostic. Startup can acquire locks, initialize or migrate storage, index data, write logs, queue startup telemetry, and start a telemetry flush.

## Local state and audit

Canonical Windows state is rooted under `%LOCALAPPDATA%\BUSCore`. Key classes include:

- SQLite business databases under `app\`;
- runtime config at `config.json`;
- domain journals and per-run logs under `app\data\journals` and `app\logs`;
- encrypted exports under `exports\`;
- encrypted secret fallback and keys under `secrets\`;
- capability and telemetry state under `state\`;
- verified update cache/state under `updates\`.

See `03_DATA_CONFIG_AND_STATE_MODEL.md` and `docs/DATA_LIFECYCLE.md` for the exact authority and retention model. Some repo-local mutable plugin/index files remain documented drift.

## External integrations

Normal local operation does not require Lighthouse, Google, Managed BUS, or any other hosted service.

- Google OAuth/Drive calls occur only for that configured integration.
- Update discovery fetches the configured manifest host. The default is Lighthouse.
- Guarded manual staging re-fetches trusted manifest metadata and downloads the declared artifact.
- Optional product telemetry uses the fixed Lighthouse schema-1.0 endpoint only after disclosure is acknowledged and telemetry remains enabled.

Update-route analytics and product-event telemetry are separate evidence streams. Core's three generated update parameters and the strict product-event payload contain no business content or persistent installation identifier. However, the update client does not prohibit/sanitize operator-configured URL userinfo and preserves unrelated query parameters, so that URL data is trust-sensitive and is not covered by the Core-generated-field privacy guarantee. Neither stream is a count of people, authenticated clients, unique installations, engagement, or retention.

## Product telemetry controls and evidence

- Effective delivery requires both `telemetry.enabled` and `telemetry.disclosure_acknowledged`.
- Payload construction is strict and allowlisted.
- Pending and dead-letter retention are bounded to 100 records each.
- Delivery requires a 2xx response acknowledging the exact event ID.
- Retry is trigger-driven, limited to three attempts, and has no shutdown flush guarantee.
- Disabling blocks new emits/new flush starts and best-effort replaces pending/dead-letter file contents with empty arrays. It does not cancel a sender request already in flight. Cumulative state counters and acknowledged milestone keys remain.
- Product telemetry failure never blocks normal local work.

The accurate runtime snapshot is protected `GET /app/telemetry/status` on an already-running authorized instance. It does not flush or contact Lighthouse, but the request is logged and claimed auth may update session activity.

Current Home telemetry text and the telemetry value in `/transparency.report` are hardcoded off and are not telemetry authorities. `/transparency.report` remains useful for policy, plugin/capability, and path transparency only.

## Operator checklist

1. Read root `AGENTS.md`, `SOT.md`, and `OPERATIONS.md`.
2. Establish the exact branch/commit and requested evidence window.
3. Use checked-in evidence first.
4. Read selected AppData files only when local-state access is explicitly in scope; validate raw JSON before interpretation.
5. Use `/app/telemetry/status` only if BUS Core is already running and loopback/authenticated access is authorized.
6. Never call `/app/update/check`, save a telemetry preference, flush events, stage an update, or launch BUS Core merely to create diagnostic evidence.
7. Report inaccessible evidence as `ACCESS_BLOCKED` using the format in `OPERATIONS.md`.

This document and `/transparency.report` are disclosure aids, not substitutes for the SOT, the operations runbook, raw approved local evidence, or receiver-owned Lighthouse evidence.
