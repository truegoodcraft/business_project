# Contacts schema patch notes

This release adds an idempotent, SQLite-safe patch that aligns the `vendors` table with the Contacts feature set. On startup, the app now ensures the following columns exist and have sensible defaults:

- `is_vendor` (INTEGER, NOT NULL, DEFAULT 0)
- `is_org` (INTEGER, NOT NULL, DEFAULT 0)
- `role` (TEXT, DEFAULT `contact`)
- `contact` (TEXT)
- `organization_id` (INTEGER)
- `meta` (TEXT)

It also backfills legacy values (e.g., `role`/`kind`) into the new flags and creates helpful indexes on `is_vendor` and `is_org`. The patch is safe to run repeatedly and will no-op when the schema is already up to date.
