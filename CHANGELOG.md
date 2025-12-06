# Changelog

## v0.8.3
- Journals append only after database commits; restore archives and recreates journals.
- Password-based AES-GCM exports to `%LOCALAPPDATA%/BUSCore/exports` with preview/commit restore flow.
- Admin UI card for export/restore plus smoke coverage for reversible restores.

## v0.8.2
- Single-run POST contract for manufacturing runs.
- Fail-fast manufacturing (shortages=400, no writes).
- Atomic commit on success.
- Output costing rule (round-half-up).
- Manufacturing never oversells.
- Adjustments aligned to FIFO semantics.

## v0.8.1
- Core is tierless; removed all licensing logic and Pro gating.
- `/health` is tier-blind: returns only `{ ok, version }`.
- Deleted `/dev/license` and license.json handling.
- Removed Pro-only features (RFQ, batch automation, scheduled runs).
- **UI:** Removed license/tier badge and all “Pro/Upgrade” wording.
