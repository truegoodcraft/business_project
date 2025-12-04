# Licensing (Community Tier)

- **Gated endpoints (must be rejected under community):**
  - `POST /app/rfq/generate`
  - `POST /app/inventory/run`
  - `POST /app/import/commit`
- **Free endpoints (allowed under community):**
  - `POST /app/import/preview`
  - `PUT /app/items/{id}` (one-off quantity adjustment)

All `/app/**` routes already require an `X-Session-Token`, and existing `require_writes` checks remain as implemented.
