# Recipes: Unit-aware input lines (UI only)

Each recipe input now captures **Qty + Unit** together, infers the **dimension**, and previews the base quantity that will be saved. All conversions happen on the client; the server contract stays the same.

## Behavior
- Default unit is the selected item's `uom` (display unit). If missing, a per-dimension default is used (Imperial defaults when American mode is ON).
- The **Qty** field is paired with a **Unit** select; changing either updates the inferred dimension.
- For **area** items, a **Length × Width** helper can fill the quantity and switch the unit to the matching area unit (cm², m², in², ft²).
- A **preview** shows the base-unit quantity that will be sent, plus an estimated line cost when FIFO cost data exists.
- On save, each line's quantity is converted to **base units** before submitting the recipe payload (no unit fields are sent to the API).

## Defaults
- Metric: length = m, area = m², weight = g, volume = L, count = ea
- American mode: length = in, area = ft², weight = oz, volume = fl oz, count = ea

## Manual QA
1) Create/edit a recipe; pick an item and enter Qty + Unit. Preview shows base quantity.
2) Switch American mode on in Settings. New lines default to imperial units; preview still shows metric/base.
3) For an area item, use the L×W helper (e.g., 7.75 in × 6.45 in). Qty fills with the computed area and unit switches to in²; preview shows converted base units.
