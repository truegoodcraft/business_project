# BUS Core – Ledger & Batches (Backend)

## One-time
1. Ensure DB path: `BUS_DB=data/app.db`. Create folders: `data/`, `data/journals/`.
2. Apply migration:
   - `python core/appdb/migrations/2025_12_01_ledger_batches.py`
3. Bootstrap legacy batches:
   - `curl -X POST http://localhost:8765/app/ledger/bootstrap`
4. Health check:
   - `curl http://localhost:8765/app/ledger/health`

## Harvester (optional, non-invasive)
- Run once: `scripts/run_harvester.ps1` or `scripts/run_harvester.sh`
- Add to Task Scheduler / cron for periodic ingestion.

## Accounting Sync Boundary

BUS Core does not include QuickBooks/Wave sync as part of Core. Keep ledger work focused on local inventory, batch, cash-event, and manufacturing truth. Any accounting-package integration remains outside this Core polish pass and requires owner review before it can become a supported release surface.

