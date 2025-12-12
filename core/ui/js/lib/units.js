/* SPDX-License-Identifier: AGPL-3.0-or-later */
// UI-only unit helpers. Server stores base units in metric (mm, mm2, mg, mL, ea).
// American mode lets users enter in imperial, but we convert to metric before POST.

export const METRIC = {
  length: { mm: 1, cm: 10, m: 1000 },
  area:   { mm2: 1, cm2: 100, m2: 1_000_000 },
  mass:   { mg: 1, g: 1000, kg: 1_000_000 },
  volume: { ml: 1, l: 1000 },
  count:  { ea: 1 }
};

// Imperial factors to METRIC BASE units (NOT exact integers; we keep precision until final rounding)
export const IMPERIAL_TO_METRIC = {
  length: { in: 25.4, ft: 304.8 },                              // -> mm
  area:   { in2: 25.4 ** 2, ft2: 304.8 ** 2 },                  // -> mm2
  mass:   { oz: 28349.523125, lb: 453592.37 },                  // -> mg
  volume: { fl_oz: 29.5735295625, gal: 3785.411784 },           // -> mL (US)
  count:  { ea: 1 }                                             // -> ea
};

export const DIM_DEFAULTS_METRIC   = { length: 'm',  area: 'm2', mass: 'g',  volume: 'l',  count: 'ea' };
export const DIM_DEFAULTS_IMPERIAL = { length: 'in', area: 'ft2', mass: 'oz', volume: 'fl_oz', count: 'ea' };

// Normalize labels
export function norm(u) { return String(u || '').replace(/[²^2]/g, '2').toLowerCase(); }

// Decide if a unit string is imperial
export function isImperialUnit(dim, unit) {
  const u = norm(unit);
  return !!IMPERIAL_TO_METRIC[dim]?.[u];
}

// Convert (qty, unit_price) from display units to METRIC *base* units (ints for qty; decimals for price/base)
export function toMetricBase({ dimension, qty, qtyUnit, unitPrice, priceUnit }) {
  const dim = dimension;
  const qU  = norm(qtyUnit || '');
  const pU  = norm(priceUnit || qU || '');

  // If the UI used metric units, we simply fall through and caller may still send qty_unit/price_unit
  const q = Number(qty ?? 0); const p = Number(unitPrice ?? 0);

  // If imperial, convert to METRIC base units and return with NO *_unit (server assumes base)
  if (isImperialUnit(dim, qU) || isImperialUnit(dim, pU)) {
    // Factor to metric base
    const f = (u) => isImperialUnit(dim, u) ? IMPERIAL_TO_METRIC[dim][norm(u)] : METRIC[dim][norm(u)] || 1;

    const qtyBase = Math.round(q * f(qU));              // integer in base
    const pricePerBase = (p / f(pU));                   // price per base unit
    return { qtyBase, pricePerBase, sendUnits: false };
  }

  // Metric path: let caller send units as-is (server knows mm/mm2/mg/ml/ea)
  return { qtyBase: null, pricePerBase: null, sendUnits: true };
}
