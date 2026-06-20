# BUS Core LazoralltheCore Community Polish Patch

Status: implementation pass notes, no public version bump.

## Summary

This patch closes the first-look friction from the Laser Everything walkthrough while keeping BUS Core focused on local-first shop infrastructure. It is a Core polish pass, not a feature-expansion release.

## What Changed Since Laser Everything

- Recipe screens now explain Product, Recipe, and Output Product in the same workflow language used by Inventory and Manufacturing.
- Stock-out sales now prefill from the selected product price while the sale price is untouched.
- Stock-out sales show the usual product price and warn when a sale price is below it.
- Negative Stock-out sale unit prices are rejected at the API boundary.
- Manufacturing and stock-out shortages are written for operators: item name, needed quantity, available quantity, and missing quantity.
- Manufacturing history shows run labels such as `Run #6`.
- Finance has date presets for Last 30 days, this month, last month, this quarter, last quarter, and this year.
- Start Fresh copy now reminds operators that demo data is separate and points them to Settings -> Administration -> Backup Export before resetting real-shop data.
- Getting Started docs now follow the first material -> product -> recipe -> manufacture -> stock-out -> finance workflow.

## Still Not Included

BUS Core still does not include:

- Full POS
- Full accounting
- QuickBooks/Wave sync
- Automatic reorder
- Full job scheduling
- Cloud accounts
- Cloud sync
- Telemetry
- Payment links
- Customer portals
- Recurring billing

## Boundary

No schema expansion, route auth/write-gate changes, backup/restore trust changes, update/release/signing authority changes, telemetry, cloud sync, Pro automation, or public `VERSION` bump are part of this patch.

## Manual Smoke Checklist

1. Start from demo or a fresh shop.
2. Add a vendor.
3. Add a raw material with opening stock.
4. Add a product with a usual sale price.
5. Create a recipe that outputs that product.
6. Run a manufacturing shortage case and confirm the shortage message is readable.
7. Run a successful manufacturing case and confirm current stock values appear in the projection table.
8. Stock out a sold product and confirm the sale price prefills from the product price.
9. Enter a sale price below the usual product price and confirm the warning is non-blocking.
10. Open Finance and verify COGS/profit are visible for the sale.
11. Try each Finance date preset.
12. Check backup/settings/update/help/support links without changing release/update or backup trust behavior.
