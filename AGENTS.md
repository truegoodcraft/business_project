# AGENTS.md — TGC Alpha Core

## Always-Read
**Every agent must read and obey this file before any change.**

---

## Global Constraints
- **No schema changes** — `app.db` tables fixed.
- **ESM only** — `/ui/js/cards/*.js` use `import { apiGet, ... } from '../api.js'`.
- **FREE tier only** — No `feature_enabled()` checks in this SPEC.
- **Dark theme** — Background `#1e1f22`, text `#e6e6e6`, inputs `#2a2c30`.
- **Rounded UI** — `border-radius: 10px` on inputs, buttons, modals.
- **Writes require `X-Session-Token`** — All `apiPost/Put/Delete` must wait for `ensureToken()`.

---

## API Contract (Existing – Do Not Modify)
| Method | Endpoint | Body | Notes |
|-------|----------|------|-------|
| GET | `/app/items` | — | Returns array of items |
| POST | `/app/items` | `{name, sku?, qty, unit, vendor_id?, price?, location?}` | Create |
| PUT | `/app/items/{id}` | same | Update |
| DELETE | `/app/items/{id}` | — | Delete |
| POST | `/app/inventory/adjust` | `{item_id, delta, reason}` | Journaled |
| GET | `/app/vendors` | — | `[{id, name}]` (fallback: `/app/vendors/list`) |

---

## Roadmap
- **SPEC-1** (Current): Inventory Viewer + Manual CRUD + UX Polish  
- **SPEC-2**: Bulk Import (Pro) — **DO NOT IMPLEMENT HERE**  
- **SPEC-3**: Low-stock RFQ (Pro) — preview only  

---

## UX Rules (SPEC-1)
- **Modal**: Dark, centered, `box-shadow`, `460px` width.
- **Table**: Rounded container, hover row (`#23262b`), header `#2b2d31`.
- **Unit selector**: Two-step  
  - Step 1: `ea`, `metric`, `imperial`  
  - Step 2: Populates from `UNIT_SETS`, disabled for `ea`
- **Price**: Currency dropdown **UI-only** — `localStorage.setItem('priceCurrency', ...)` — **do not send to backend**
- **Vendor**: Dropdown only if `/app/vendors` returns data. Else hide field.
- **Hide token chip**: `.token-badge, #token-badge { display: none !important; }`
- **No duplicate tabs** — Only one `Inventory` entry in sidebar.

---

## Done Definition
- Manual test plan passes:
  1. Table loads  
  2. Add item (all fields) → appears  
  3. Edit → saves  
  4. Adjust qty → updates + journals  
  5. Delete → gone  
- No new globals, no legacy `<script>` loaders.
- All mutations work with **Writes ON**. Reads work with **Writes OFF**.
- No 422 errors on valid input.

---

**End of AGENTS.md**
