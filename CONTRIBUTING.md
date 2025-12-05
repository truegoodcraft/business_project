# Contributing

## Change acceptance workflow

1. Start from a fresh unzip/clone.
2. Run the **Window A** server flow from the README (uvicorn).
3. Run the **Window B** smoke harness from the README.

All of the following must be **true** for a change to be accepted:

- Vendors/items baseline CRUD: every allowed operation returns HTTP 200.
- Items one-off `PUT /app/items/{id}` returns HTTP 200.
- Inventory runs (`POST /app/inventory/run` and `/app/manufacturing/run`) succeed when inputs are valid and stock is sufficient.
- Public `GET /health` returns HTTP 200 with `{"ok": true, "version": "..."}`.
- `GET /ui/shell.html` returns HTTP 200 with a non-empty body.

Docs and the `buscore-smoke.ps1` harness are the source of truth for the developer workflow.




DOC IS OUTDATED
