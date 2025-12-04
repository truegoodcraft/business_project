# Contributing

## Change acceptance workflow

1. Start from a fresh unzip/clone.
2. Run the **Window A** server flow from the README (uvicorn).
3. Run the **Window B** smoke harness from the README.

All of the following must be **true** for a change to be accepted:

- Vendors/items baseline CRUD: every allowed operation returns HTTP 200.
- Items one-off `PUT /app/items/{id}` returns HTTP 200.
- Gated endpoints `POST /app/rfq/generate`, `POST /app/inventory/run`, and `POST /app/import/commit` **must not** return HTTP 200 under the community tier.
- Public `GET /health` returns HTTP 200 with `{"ok": true}`.
- Protected `GET /health` (with token) returns HTTP 200 and includes `version`, `policy`, `license`, and `run-id`.
- `GET /ui/shell.html` returns HTTP 200 with a non-empty body.

Docs and the `buscore-smoke.ps1` harness are the source of truth for the developer workflow.




DOC IS OUTDATED
