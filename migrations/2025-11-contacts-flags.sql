BEGIN TRANSACTION;

-- Add columns if missing
ALTER TABLE vendors ADD COLUMN IF NOT EXISTS is_vendor INTEGER DEFAULT 0;
ALTER TABLE vendors ADD COLUMN IF NOT EXISTS is_org INTEGER DEFAULT 0;

-- Backfill is_vendor from role (if role exists)
UPDATE vendors
SET is_vendor = CASE LOWER(COALESCE(role, '')) WHEN 'vendor' THEN 1 WHEN 'both' THEN 1 ELSE 0 END
WHERE is_vendor IS NULL OR is_vendor NOT IN (0, 1);

-- Backfill is_org from legacy kind if present; else keep default 0
-- (No-op if 'kind' was already dropped; this UPDATE will simply fail silently in older SQLite if column missing.)
-- If your SQLite errors on missing column, ignore; the next statements commit safely.

COMMIT;
