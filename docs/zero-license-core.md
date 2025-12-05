# Zero-License Core (v0.8.1)

This document summarizes the three-step removal of licensing, tiering, and Pro-only surfaces from BUS Core.

## What changed
- Removed all license file handling and `/dev/license` debug surface. Core no longer reads or writes `license.json`.
- Deleted entitlement/tier checks and made `/health` tier-blind; the endpoint now returns only `{ "ok": true, "version": "<semver or git SHA>" }`.
- Removed Pro-only features (RFQ generation, automated/scheduled runs, batch automation scaffolding) from backend and UI.
- Simplified UI messaging to avoid tier/upgrade language.

## Current health contract
```
GET /health
{
  "ok": true,
  "version": "<semver or git SHA>"
}
```
A detailed health payload remains available only under the dev flag and excludes any license or tier metadata.

## Scope notes
- Core runs entirely in a tierless mode; no feature gating hooks remain in shipped code.
- Historical notes about licensing may remain in docs for provenance, but runtime paths and UI copy are tier-free.
- RFQ templates, routes, and UI cards were removed; manufacturing runs continue to operate manually.

