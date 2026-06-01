# BUS Core Job Tracking Research and Implementation Plan

## 1. Executive Recommendation
Job Tracking in BUS Core should be implemented as the **Connective Tissue** between customer demand and production execution. It should not be a complex project management tool, but rather an **Operator’s Command Center** that answers "What needs to be built, for whom, and by when?" 

The recommendation is to introduce a lightweight `Job` entity that groups items, recipes, and manufacturing runs under a single customer-facing or internal goal. This moves BUS Core from a reactive inventory logger to a proactive production brain.

## 2. Current Codebase Findings
- **Identity:** `Vendor` table already handles "Contacts" and "Organizations" (via `role` and `is_vendor` flags). This is the natural home for "Customers."
- **Production:** `ManufacturingRun` exists but is currently an atomic "point-in-time" event. It lacks a "pending" or "scheduled" state.
- **Finance:** `CashEvent` tracks "sales" and "expenses," but they are detached from the production process. A sale happens when stock is moved out; there is no concept of a "deposit" or "pre-payment" linked to a future production task.
- **Inventory:** `Item` has an `is_product` flag. Stock movements are well-defined via `ItemMovement` and `fifo_consume`.
- **Authority:** All mutations pass through service-layer authorities (e.g., `perform_stock_in_base`).

## 3. External Research Findings
- **Work Order vs. Job:** Industry leaders (Odoo, ERPNext) separate the "Plan" (Work Order) from the "Execution" (Job). For BUS Core's scale, these should be collapsed into a single **Job** concept to reduce overhead.
- **Patterns:** 
    - **Makers/Small Batch:** Need COGS accuracy (Craftybase style).
    - **Job Shops:** Need status visibility (CNC/Laser/3D Print style).
- **Key Takeaway:** Avoid "Shop Floor" clock-in/clock-out granularity. Focus on **Status Transitions** (e.g., "Ready to Ship").

## 4. Product Interpretation: What Job Tracking Means for BUS Core
"Job Tracking" in BUS Core is the bridge between a **Customer’s Request** and the **Physical Result**.

**A Job is a local-first work commitment that groups customer/contact context, requested outputs, operator status, and linked execution/finance events without becoming the authority for inventory, manufacturing, or accounting.**

- **Job:** A commitment to produce or deliver something.
- **Connective Tissue:** It links a Contact (Customer) + Item/Recipe (Requirement) + ManufacturingRun (Execution) + CashEvent (Financial Impact).
- **Simplicity:** A Job is essentially a "Status-Aware Folder" for related production and financial events. It groups and references existing truth rather than becoming a parallel authority.

## 5. Recommended Core Concept Model
- **Canonical Term:** **Job**. (Avoids the industrial baggage of "Work Order").
- **Job Line:** A line item within a job. These represent products, services, fees, repairs, custom work, or notes.
- **Integration:** 
    - 1 Job -> 0..N `ManufacturingRun` (Execution).
    - 1 Job -> 0..N `CashEvent` (Deposits, Final Payments).
    - 1 Job -> 0..N `ItemMovement` (Final delivery).
- **Non-Authority Rule:** Job status changes MUST NOT silently mutate stock, finance, or manufacturing state. Mutations remain explicit and auditable through canonical services.

## 6. Proposed Data Model
### `jobs` table
- `id`: Integer (Primary Key)
- `contact_id`: ForeignKey(`vendors.id`, nullable=True) - The Customer.
- `title`: String (Required) - e.g., "Order #1024 - Wedding Sign".
- `status`: String (Required) - `draft`, `active`, `blocked`, `ready`, `done`, `cancelled`.
- `priority`: Integer (Default 0) - For dashboard sorting.
- `due_date`: DateTime (Nullable) - The deadline.
- `notes`: Text (Nullable).
- `created_at`: DateTime (Auto).
- `updated_at`: DateTime (Auto).
- `closed_at`: DateTime (Nullable).

### `job_lines` table
- `id`: Integer (PK)
- `job_id`: ForeignKey(`jobs.id`)
- `item_id`: ForeignKey(`items.id`, nullable=True)
- `recipe_id`: ForeignKey(`recipes.id`, nullable=True) - Link to a build plan.
- `line_type`: String (Required) - `product`, `service`, `fee`, `note`.
- `description`: Text (Required).
- `qty_base`: Integer (Nullable) - Normalized base quantity.
- `display_uom`: String (Nullable) - UOM for UI presentation.
- `unit_price_cents`: Integer (Nullable) - Quoted price.
- `status`: String - e.g., `pending`, `produced`, `delivered`.
- `sort_order`: Integer (Default 0).
- `created_at`: DateTime (Auto).
- `updated_at`: DateTime (Auto).

### `job_events` table
- `id`: Integer (PK)
- `job_id`: ForeignKey(`jobs.id`)
- `event_type`: String (Required).
- `message`: Text (Required).
- `source_kind`: String (Nullable) - e.g., `manufacturing_run`, `cash_event`.
- `source_id`: String (Nullable).
- `meta`: Text (Nullable) - JSON metadata.
- `created_at`: DateTime (Auto).

## 7. Proposed API Surface
- `GET    /app/jobs`: List jobs with basic filters (status, customer).
- `POST   /app/jobs`: Create a new job.
- `GET    /app/jobs/{job_id}`: Full detail including line items and linked runs/events.
- `PATCH  /app/jobs/{job_id}`: Update status or header details.
- `POST   /app/jobs/{job_id}/lines`: Add line items.
- `PATCH  /app/jobs/{job_id}/lines/{line_id}`: Update line items.
- `DELETE /app/jobs/{job_id}/lines/{line_id}`: Remove line items.
- `POST   /app/jobs/{job_id}/events`: Add manual job notes/events.
- `POST   /app/jobs/{job_id}/status`: Explicit status transition.

**Future Endpoints (Deferred):**
- `POST /app/jobs/{job_id}/lines/{line_id}/manufacture`
- `POST /app/jobs/{job_id}/lines/{line_id}/deliver`
- `POST /app/jobs/{job_id}/payments`

## 8. Proposed UI Flow
- **Job List Card:** Simple vertical list. Badges for `Status` and `Due Date`. Search by Customer.
- **Job Detail Drawer:** (Consistent with Inventory/Recipe detail).
    - **Header:** Title, Customer, Status toggles.
    - **Line Items:** List of what to build or deliver.
    - **History:** Linked runs, payments, and events in a unified timeline.
- **Next Action Button:** Proactive button based on status (e.g., "Ready for Delivery" or "Check Stock").

## 9. Home Dashboard Impact (The Pressure Board)
The Dashboard becomes a "Pressure Board" answering four questions:
- **What needs attention?**: Jobs due soon or overdue.
- **What is blocked?**: Jobs with identified shortages (read-only warning).
- **What is ready to finish/get paid?**: Jobs in `ready` state.
- **What money is sitting in active work?**: Total value of `active` jobs.

**Recommended Signals:**
- Jobs due soon.
- Blocked jobs (shortage warnings).
- Ready jobs.
- Active job value.
- Recent job events.

## 10. Stock / Manufacturing / Finance Integration
- **Stock:** No stock reservations in v1. Jobs may show read-only shortage/blocker warnings by using existing manufacturing validation logic.
- **Manufacturing:** Links to canonical `ManufacturingRun` records via `source_kind/source_id`.
- **Finance:** Links to canonical `CashEvent` records via `source_kind/source_id`.
- **Draft Jobs:** Support capture of demand without affecting stock, revenue, or manufacturing.

## 11. Security / Permissions / Local-First Concerns
- **Local-First:** SQLite handles the new tables easily. No external dependencies.
- **Permissions:** `jobs.read`, `jobs.write`. Simple and consistent with the existing model.
- **Offline:** Fully offline-capable by design.
- **Quantity Authority:** Respects BUS Core’s base-unit model. API accepts human quantity, backend normalizes immediately and stores `qty_base` integers. No floats or UI-side multipliers.

## 12. Risks and Bloat Traps
- **Trap:** Full CRM. **Mitigation:** Only use existing `Vendor` table.
- **Trap:** Staff Scheduling. **Mitigation:** Stick to `due_date` at the Job level only.
- **Trap:** Gantt Charts. **Mitigation:** Use a simple list with priority sorting.
- **Risk:** Parallel Authority. **Fix:** Job status change MUST NOT silently mutate stock/cash/manufacturing. All inventory-affecting actions must call canonical services.

## 13. Phased Implementation Plan
- **Phase 0:** Revise plan and draft proposed SOT delta only (Current).
- **Phase 1 (Backend):** Schema migrations for `jobs`, `job_lines`, and `job_events`. CRUD API.
- **Phase 2 (UI & Dashboard):** Jobs UI (List/Detail) + Home dashboard job signals.
- **Phase 3 (Integration - Production):** Link manufacturing runs to job lines.
- **Phase 4 (Integration - Finance):** Link payments/deposits/final payments to jobs.
- **Phase 5 (Execution):** Explicit delivery/stock-out actions from the Job UI.
- **Phase 6 (Future):** Advanced work: reservations, Pro automation, richer quoting/invoicing.

## 14. Required Tests and Guardrails
- **No Silent Mutation:** Job status change does not mutate stock, cash, or manufacturing.
- **Draft Isolation:** Draft jobs do not affect stock, cash, manufacturing, or availability.
- **Quantity Normalization:** Job line quantities normalize through canonical backend quantity conversion.
- **Durable Authority:** No durable `qty_decimal` authority for operational quantities; store `qty_base`.
- **Event Integrity:** Job events link to source truth but do not replace it.
- **State Guard:** Cancelled jobs cannot trigger manufacture/delivery actions.
- **Service Compliance:** All manufacturing/delivery/finance actions must call canonical services.
- **Dashboard Read-Only:** Home dashboard job signals are read-only summaries.

## 15. Open Questions for Owner
- Do we need a "Quote" entity specifically, or is "Draft Job" sufficient? (Recommend: Draft Job for v1).
- Should Jobs be allowed to span multiple customers, or always exactly one? (Recommend: One customer per Job for v1).

## 16. Proposed SOT Delta — NOT APPLIED
```markdown
## Job Tracking Authority

* **Canonical Term:** **Job**.
* **Definition:** A Job is a demand/work-commitment authority only. It does not own inventory, manufacturing, or finance truth.
* **Relationship:** Jobs link to canonical execution and finance records using source_kind/source_id or explicit relationships.
* **Mutation Guard:** Job status changes MUST NOT silently mutate stock, cash, or manufacturing state.
* **Execution Guard:** All inventory-affecting job actions MUST call canonical stock/manufacturing services.
* **Draft Policy:** Draft jobs MUST have no stock, cash, or manufacturing effect.
* **Reservation Policy:** Stock reservations are out of scope for v1.
* **Quantity Policy:** Job line operational quantities MUST follow canonical base-unit storage rules (qty_base integers).
```

## 17. Final Recommendation
Build Job Tracking next, but only as a lightweight demand/control layer first. The v1 win is not "project management"; it is providing a "Pressure Board" for the operator. BUS Core should open and immediately tell the operator what work matters next, what is blocked, what is ready, and what money is tied to active work.
