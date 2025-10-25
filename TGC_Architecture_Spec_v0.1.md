# True Good Craft (TGC) — Architecture Spec v0.1  
Version: 0.1 • Date: 2025-10-25  
Stage: Post-v0.4 (RFQ + Inventory Ops Complete)  

## 1. System Overview
TGC is a local-only business operations system for small manufacturers.  
Core provides a stable API for CRUD, RFQ generation, inventory management, and secure plugin access.  
The UI (dashboard) consumes these endpoints through a localhost interface.  
SQLite serves as the data layer.  
Everything runs offline; optional encrypted export/import handles sync between machines.  

## 2. Module Layout
```text
BUSCore/
│
├── core/
│   ├── api/
│   │   ├── http.py           # Primary REST endpoints
│   │   ├── app_router.py     # CRUD and business routes
│   │   └── auth.py           # Token generation, write toggles
│   │
│   ├── models.py             # SQLAlchemy tables (Vendors, Items, Tasks, Attachments)
│   ├── utils/
│   │   ├── export.py         # v0.5 encrypted export/import
│   │   └── journal.py        # JSONL logging helpers
│   │
│   ├── templates/
│   │   └── rfq_template.jinja
│   │
│   └── __init__.py
│
├── core/ui/
│   ├── shell.html            # Base dashboard
│   ├── js/
│   │   ├── token.js          # Session, writes toggle
│   │   ├── api.js            # Fetch helpers
│   │   ├── cards/
│   │   │   ├── vendor.js
│   │   │   ├── items.js
│   │   │   ├── tasks.js
│   │   │   ├── rfq.js
│   │   │   └── inventory.js
│   │   └── buscore.js        # Event bus, token-ready signals
│   └── css/
│
├── scripts/
│   └── launch_buscore.ps1    # Startup launcher
│
└── app.db                    # SQLite data store
```

## 3. Internal API Map

### 3.1 Authentication
- `GET /session/token` → `{token}`
- `POST /dev/writes` `{enabled:true|false}` — toggles write permissions.
- Header required on all stateful requests: `X-Session-Token`.

### 3.2 CRUD Core
- `/app/vendors`, `/app/items`, `/app/tasks`, `/app/attachments`
  - Methods: GET, POST, PUT, DELETE
  - Returns JSON objects validated with Pydantic.

### 3.3 RFQ and Inventory (v0.4)
- `POST /app/rfq/generate`
  - Inputs: `{items[], vendors[], fmt:'md'|'pdf'|'txt'}`
  - Output: streamed file; saved copy under `%LOCALAPPDATA%\BUSCore\exports`
- `POST /app/inventory/run`
  - Inputs: `{inputs:{id:qty}, outputs:{id:qty}, note?}`
  - Output: `{ok:true, deltas:{}, snapshot_version}`
  - Appends JSONL entry to `data/journals/inventory.jsonl`
- `GET /dev/journal/info`
  - Returns directory paths and last journal lines.

### 3.4 Export / Import (v0.5)
- `POST /app/export`
  - Inputs: `{password}`
  - Process:
    - Dump SQLite DB + manifest → ZIP → AES-256-GCM encrypt with Argon2id key.
    - Output: `.tgc` file saved under `/exports`.
- `POST /app/import`
  - Inputs: `{file, password, dry_run?:true}`
  - Process:
    - Decrypt, verify schema/version.
    - Dry-run preview if requested.
    - Replace DB only after user confirmation.
- Security: Exported file is unreadable without password. Import never overwrites without explicit confirmation.

## 4. Data Flow
Path:
`SQLite ↔ Core (FastAPI/SQLAlchemy) ↔ Local API (localhost) ↔ Dashboard (HTML/JS) ↔ User`

1. User interacts with dashboard cards.
2. Each card calls `api.js → /app/...` using stored token header.
3. Core validates token and writes toggle before altering DB.
4. Any mutation triggers:
   - SQLAlchemy commit,
   - JSONL append to journal,
   - optional export/log action.
5. Dashboard reloads updated data via GET endpoints.

Writes Disabled Mode:
If `writes=false`, Core returns `403 {"error":"writes_disabled"}` to all mutating routes.

## 5. Plugin Sandbox Contract

### 5.1 Execution Model
- Plugins run as short-lived isolated processes.
- Communication via local HTTP to Core endpoints only.
- No direct DB or file access.

### 5.2 Allowed Calls
- `GET /app/*` (read)
- `POST /app/tasks` (create task)
- `POST /app/rfq/generate` (if licensed)
- `POST /app/inventory/run` (if licensed)
- Plugins may request `GET /dev/journal/info` for read-only diagnostics.

### 5.3 Restrictions
- No network access by default.
- No write access outside Core API.
- All calls logged to `plugin_audit.jsonl` with: plugin_name, endpoint, payload hash, timestamp.
- Each plugin must include a signed manifest:
```json
{
  "name": "plugin_name",
  "version": "1.0",
  "author": "Dev",
  "hash": "sha256sum",
  "permissions": ["read_inventory", "run_rfq"]
}
```

### 5.4 Licensing Hooks
- Core checks license before enabling restricted endpoints.
- License key stored locally, hashed.
- UI shows “Feature locked” when license absent.
- Licenses never prevent DB read/export.

## 6. Database Schema (SQLite)
| Table        | Fields                                                                 | Notes                               |
|--------------|------------------------------------------------------------------------|-------------------------------------|
| vendors      | id, name, contact, material_type, last_price, lead_time, status        | linked to items                     |
| items        | id, vendor_id, sku, name, qty, unit, price                             | FKs to vendors                      |
| tasks        | id, description, priority, due_date, status                            |                                     |
| attachments  | id, item_id, path, type, created_at                                    |                                     |
| journals     | jsonl external                                                         | append-only, not table              |

Schema auto-creates via SQLAlchemy on boot.

## 7. Export / Import Design
File: `TGC_EXPORT_<timestamp>.tgc`

Container:
```json
{
  "version": "v0.5",
  "kdf": "argon2id",
  "salt": "<hex>",
  "nonce": "<hex>",
  "ciphertext": "<hex>"
}
```

Workflow:
1. User clicks Export in dashboard.
2. Prompt → password → encryption → file saved to `/exports`.
3. Import reverses process, validates checksum, warns if schema mismatch.

Encryption: AES-256-GCM  
Key derivation: Argon2id (time=2, mem=64MB, parallelism=1)

## 8. Folder Permissions / Security Model
- Local only: binds to `127.0.0.1`.
- No remote API.
- Audit logs:
  - `/app/data/journals/inventory.jsonl`
  - `/app/data/plugin_audit.jsonl`
- Sensitive paths locked to `%LOCALAPPDATA%\BUSCore`.
- Token lifetime: ephemeral; refresh via `/session/token`.
- Writes toggle: must be true to mutate DB.

## 9. UI Interaction Map
| Card       | Backend Endpoint              | Action                                  |
|------------|-------------------------------|-----------------------------------------|
| Vendors    | `/app/vendors`                | List/add/edit/delete                    |
| Items      | `/app/items`                  | List/add/edit/delete                    |
| Tasks      | `/app/tasks`                  | List/add/edit/close                     |
| RFQ        | `/app/rfq/generate`           | Build + download RFQ                    |
| Inventory  | `/app/inventory/run`          | Adjust quantities                       |
| Export     | `/app/export`                 | Generate encrypted backup               |

All JS cards listen for `bus:token-ready` and call `apiGet/apiPost`.

## 10. Version Control and Release
- Branch convention: `feat/vX.Y-feature`
- Merge → Tag → ZIP build.
- Tag examples:
  - `v0.4.0` (current)
  - `v0.5.0` (after export/import is implemented)

## 11. Future Extension Hooks
- v2+
  - Plugin marketplace (signed manifests)
  - Drive/Notion/email read-only connectors
  - Scheduler
  - Multi-user (local LAN only)
  - Cloud backup (opt-in encrypted)

Core: closed-source • Plugin SDK: open-source • Data: always user-owned
