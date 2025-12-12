/* SPDX-License-Identifier: AGPL-3.0-or-later */
// UI-only unit helpers. Server stores base units in metric (mm, mm2, mm3, mg, ea).
// American mode lets users enter in imperial, but we convert to metric before POST.

const METRIC_WEIGHT = { mg: 1, g: 1000, kg: 1_000_000 };
const METRIC_VOLUME = { mm3: 1, cm3: 1_000, m3: 1_000_000_000, ml: 1_000, l: 1_000_000 };

export const METRIC = {
  length: { mm: 1, cm: 10, m: 1000 },
  area:   { mm2: 1, cm2: 100, m2: 1_000_000 },
  volume: METRIC_VOLUME,
  weight: METRIC_WEIGHT,
  mass:   METRIC_WEIGHT,
  count:  { ea: 1_000 },
};

// Imperial factors to METRIC BASE units (NOT exact integers; we keep precision until final rounding)
export const IMPERIAL_TO_METRIC = {
  length: { in: 25.4, ft: 304.8 },                              // -> mm
  area:   { in2: 25.4 ** 2, ft2: 304.8 ** 2 },                  // -> mm2
  mass:   { oz: 28_349.523125, lb: 453_592.37 },                // -> mg
  weight: { oz: 28_349.523125, lb: 453_592.37 },                // -> mg
  volume: { fl_oz: 29_573.5295625, gal: 3_785_411.784 },        // -> mm3 (US)
  count:  { ea: 1 },
};

export const DIM_DEFAULTS_METRIC   = { length: 'm',  area: 'm2', mass: 'g', weight: 'g', volume: 'l',  count: 'ea' };
export const DIM_DEFAULTS_IMPERIAL = { length: 'in', area: 'ft2', mass: 'oz', weight: 'oz', volume: 'fl_oz', count: 'ea' };

// Normalize labels
export function norm(u) { return String(u || '').replace(/[²^2]/g, '2').replace(/[-\s]/g, '_').toLowerCase(); }

function normalizeDimension(dim) {
  if (!dim) return null;
  const d = String(dim).toLowerCase();
  if (d === 'mass') return 'weight';
  return d;
}

// Decide if a unit string is imperial
export function isImperialUnit(dim, unit) {
  const u = norm(unit);
  const d = normalizeDimension(dim);
  return !!IMPERIAL_TO_METRIC[d]?.[u];
}

// Convert (qty, unit_price) from display units to METRIC *base* units (ints for qty; decimals for price/base)
export function toMetricBase({ dimension, qty, qtyUnit, unitPrice, priceUnit }) {
  const dim = normalizeDimension(dimension) || 'count';
  const qU  = norm(qtyUnit || '');
  const pU  = norm(priceUnit || qU || '');

  // If the UI used metric units, we simply fall through and caller may still send qty_unit/price_unit
  const q = Number(qty ?? 0); const p = Number(unitPrice ?? 0);

  const metricTable = METRIC[dim] || {};
  const metricFactorQty = metricTable[qU] || 1;
  const metricFactorPrice = metricTable[pU] || metricFactorQty || 1;
  const metricQtyBase = Number.isFinite(q) ? Math.round(q * metricFactorQty) : null;
  const metricPriceBase = Number.isFinite(p) ? p / metricFactorPrice : null;

  // If imperial, convert to METRIC base units and return with NO *_unit (server assumes base)
  if (isImperialUnit(dim, qU) || isImperialUnit(dim, pU)) {
    // Factor to metric base
    const f = (u) => {
      const key = norm(u);
      if (isImperialUnit(dim, key)) return IMPERIAL_TO_METRIC[dim][key];
      return metricTable[key] || 1;
    };

    const qtyBase = Math.round(q * f(qU));              // integer in base
    const pricePerBase = (p / f(pU));                   // price per base unit
    return { qtyBase, pricePerBase, sendUnits: false, dimension: dim };
  }

  // Metric path: let caller send units as-is (server knows mm/mm2/mg/ml/ea)
  return { qtyBase: metricQtyBase, pricePerBase: metricPriceBase, sendUnits: true, dimension: dim };
}

// --- Added: unit -> dimension index and unit dropdown options ---
export const UNIT_DIM_INDEX = (() => {
  const idx = {};
  for (const [dim, table] of Object.entries(METRIC)) {
    for (const u of Object.keys(table)) idx[norm(u)] = dim;
  }
  for (const [dim, table] of Object.entries(IMPERIAL_TO_METRIC)) {
    for (const u of Object.keys(table)) idx[norm(u)] = normalizeDimension(dim) || dim;
  }
  // common aliases
  idx[norm('m²')] = 'area'; idx[norm('cm²')] = 'area'; idx[norm('mm²')] = 'area';
  idx[norm('fl-oz')] = 'volume'; idx[norm('fl oz')] = 'volume';
  idx[norm('lbs')] = 'weight'; idx[norm('ounces')] = 'weight';
  return idx;
})();

export function dimensionForUnit(unit){
  const u = norm(unit);
  return UNIT_DIM_INDEX[u] || null;
}

// Return [{label:'Area', units:['m2','cm2','mm2', ...]}, ...] for a dropdown
export function unitOptionsList({american=false} = {}){
  const metric = {
    length: ['m','cm','mm'],
    area:   ['m2','cm2','mm2'],
    volume: ['l','ml','m3','cm3','mm3'],
    weight: ['kg','g','mg'],
    count:  ['ea'],
  };
  const imperial = {
    length: ['ft','in'],
    area:   ['ft2','in2'],
    volume: ['gal','fl_oz'],
    weight: ['lb','oz'],
    count:  ['ea'],
  };
  const byDim = american ? imperial : metric;
  const labels = {length:'Length', area:'Area', volume:'Volume', weight:'Weight', count:'Count'};
  return Object.keys(byDim).map(dim => ({ label: labels[dim], dim, units: byDim[dim] }));
}
