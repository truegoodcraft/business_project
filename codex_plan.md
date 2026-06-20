# BUS Core LazoralltheCore Implementation Brief

## Mode

Implement the scoped Pass 1 polish patch only.

This is the BUS Core `LazoralltheCore` / Laser Everything Community Polish Patch.

This is not a feature expansion release.

## Product Boundary

BUS Core is feature-frozen from the owner’s perspective.

Allowed Core work:

* bug fixes
* UX cleanup
* tester workflow blockers
* release/update reliability
* security/trust preservation
* data safety
* documentation/release clarity

Do not implement:

* full POS
* full accounting
* QuickBooks/Wave integration
* automatic reorder automation
* cloud sync
* telemetry
* full job scheduling
* Pro features inside Core
* schema expansion unless owner review approves it
* route auth/write-gate changes
* backup/restore trust changes
* update/release/signing authority changes
* public `VERSION` bump

Stop and ask owner before any of the above.

## Required Pass 1 Work

### 1. Recipe/Product/Output clarity

Improve Recipe UI clarity so a new user understands:

* Product = the inventory item you build or sell.
* Recipe = the list of materials/components needed to make that product.
* Output Item = the product this recipe adds to stock.

Improve labels/helper text around output item selection.

Make it clear that if the product does not exist yet, the user should create it in Inventory first.

Do not implement the “Create output product” shortcut in this pass unless owner separately approves Pass 2.

Prefer current app language:

* Inventory
* Product
* Recipe
* Manufacturing

Avoid old “Blueprint” wording unless required for legacy compatibility.

### 2. Stock-out sale price polish

When the selected stock-out item changes:

* prefill sale price from the selected item/product price
* do this unless the user has manually edited the sale price field
* show usual/product price near the sale price field
* warn if sale price is below usual/product price
* warning must be non-blocking

Do not implement below-cost warning in this pass.

### 3. Human-readable shortages

Improve manufacturing and stock-out shortage/error messages.

Target copy style:

“Not enough Leatherette Patch: need 150 each, have 100 each, missing 50 each.”

Avoid raw-only item IDs in normal user-facing shortage errors.

Use item names and display units where current data supports it.

### 4. Manufacturing run label polish

Display runs as:

`Run #<id>`

not:

`Run <id>`

Do not implement run notes/names in this pass.

### 5. Finance date presets

Add UI-only date preset controls if existing finance date-range logic supports it.

Presets:

* Last 30 days
* This month
* Last month
* This quarter
* Last quarter
* This year

Do not add tax logic, fiscal calendars, accounting compliance language, or new export profiles.

### 6. Start Fresh / demo safety copy

Improve confirmation copy before `/app/system/start-fresh`.

Make clear:

* demo data is separate
* this creates/resets a real-shop database
* export/backup first if needed

Prefer UI copy changes only. Do not change backend behavior unless necessary.

### 7. Docs and release polish

Update relevant docs/release surfaces in the repo.

Required docs/release sections:

“What changed since Laser Everything”

* clearer Product/Recipe/Output language
* better stock-out sale price guidance
* readable shortage messages
* `Run #N` labels
* finance date presets
* cleaner first-workflow/release clarity

“Still not included”

* full POS
* full accounting
* QuickBooks/Wave sync
* automatic reorder
* full job scheduling
* cloud accounts
* cloud sync
* telemetry
* payment links
* customer portals
* recurring billing

Keep BUS Core framed as:

* local-first
* open-source
* no forced cloud
* no telemetry
* serious infrastructure for small shops

Do not overclaim signing/update behavior.

## Verify Already-Fixed Stream Pain Points

Confirm these still work:

* adding vendor/contact from item form preserves item form progress
* manufacturing stock columns show real current on-hand values
* shortage errors are human-readable after this patch
* stock-out sale price prefill works
* below-usual-price warning works
* finance presets update date ranges correctly

## Manual Smoke Path

Verify:

first launch/demo or fresh shop
→ vendor
→ raw material
→ product with price
→ recipe
→ shortage path
→ manufacture
→ stock-out sale
→ finance/COGS/profit
→ finance presets
→ backup/settings/update/help/support

## Governance

If code/control surfaces change, follow repo governance for `CHANGELOG.md` and `core/version.py`.

Do not bump public `VERSION`.

Only bump `INTERNAL_VERSION` if existing project governance requires it.

Update `SOT.md` or governance docs only if behavior/contracts/authority changed.

## Validation

Run focused tests where available for:

* recipes
* manufacturing
* inventory/ledger
* finance
* route guards
* update policy only if touched
* governance checks

If tests cannot run, state why.

## Output Required

Return:

1. Files changed
2. Summary by patch area
3. Tests run and results
4. Manual smoke result
5. Deferred items
6. Any risks or owner-review items
