// core/ui/js/utils/measurement.js
// "Iron Core" integer measurement helpers — metric base units ×100, half-away-from-zero rounding

export const ROUNDING = "half-away-from-zero"; // explicit, searchable, future-proof

function roundHalfAwayFromZero(x) {
  // Works for +/- numbers; avoids IEEE ties-to-even behavior
  const s = x < 0 ? -1 : 1;
  const ax = Math.abs(x);
  return Math.trunc(ax + 0.5) * s;
}

const UOMS = new Set(["ea", "g", "mm", "mm2", "mm3"]);

// Basic metric conversions to base units used internally
const toBase = {
  // Length → mm
  lengthToMM(value, unit) {
    const u = unit.toLowerCase();
    if (u === "mm") return value;
    if (u === "cm") return value * 10;
    if (u === "m") return value * 1000;
    if (u === "in" || u === "inch" || u === "inches") return value * 25.4;
    if (u === "ft" || u === "foot" || u === "feet") return value * 304.8;
    throw new Error(`Unsupported length unit: ${unit}`);
  },
  // Area → mm2
  areaToMM2(value, unit) {
    const u = unit.toLowerCase();
    if (u === "mm2" || u === "mm^2") return value;
    if (u === "cm2" || u === "cm^2") return value * 100;
    if (u === "m2" || u === "m^2" || u === "sqm") return value * 1_000_000;
    if (u === "in2" || u === "in^2" || u === "sqin") return value * (25.4 ** 2);
    if (u === "ft2" || u === "ft^2" || u === "sqft") return value * (304.8 ** 2);
    throw new Error(`Unsupported area unit: ${unit}`);
  },
  // Volume → mm3
  volumeToMM3(value, unit) {
    const u = unit.toLowerCase();
    if (u === "mm3" || u === "mm^3") return value;
    if (u === "cm3" || u === "cm^3") return value * 1_000; // 1 cm3 = 1000 mm3
    if (u === "m3" || u === "m^3" || u === "cubicmeter") return value * 1_000_000_000;
    if (u === "l" || u === "liter" || u === "litre") return value * 1_000_000; // 1 L = 1e6 mm3
    if (u === "ml") return value * 1_000; // 1 mL = 1000 mm3
    if (u === "floz" || u === "fl_oz") return value * 29.5735 * 1_000; // fl oz → mL → mm3
    throw new Error(`Unsupported volume unit: ${unit}`);
  },
  // Mass → g
  massToG(value, unit) {
    const u = unit.toLowerCase();
    if (u === "g") return value;
    if (u === "kg") return value * 1000;
    if (u === "oz") return value * 28.349523125;
    if (u === "lb" || u === "lbs") return value * 453.59237;
    throw new Error(`Unsupported mass unit: ${unit}`);
  },
};

export function toStored(value, uom) {
  if (typeof value !== "number" || Number.isNaN(value)) throw new Error("value must be a number");
  if (!UOMS.has(uom)) throw new Error(`Unsupported uom: ${uom}`);
  if (uom === "ea") return roundHalfAwayFromZero(value); // counts are plain ints
  const scaled = value * 100; // ×100 rule
  return roundHalfAwayFromZero(scaled);
}

export function toDisplay(qty_stored, uom) {
  if (!Number.isInteger(qty_stored)) throw new Error("qty_stored must be integer");
  if (!UOMS.has(uom)) throw new Error(`Unsupported uom: ${uom}`);
  if (uom === "ea") return qty_stored; // counts are plain ints
  return qty_stored / 100; // inverse of ×100
}

// Parses user input like "12.5 cm", "3 ft", "2 lb" according to the target uom family
export function parseQuantity(input, uom) {
  if (!UOMS.has(uom)) throw new Error(`Unsupported uom: ${uom}`);
  if (typeof input === "number") return toStored(input, uom); // assume already in target family
  const s = String(input).trim();
  // number + optional unit token
  const m = s.match(/^([+-]?[0-9]*\.?[0-9]+)\s*([a-zA-Z0-9_^]+)?$/);
  if (!m) throw new Error(`Cannot parse quantity: ${input}`);
  const val = parseFloat(m[1]);
  const unit = (m[2] || uom).toLowerCase();

  if (uom === "ea") {
    return toStored(val, "ea");
  }
  if (uom === "mm") {
    const mm = toBase.lengthToMM(val, unit);
    return toStored(mm, "mm");
  }
  if (uom === "mm2") {
    const mm2 = toBase.areaToMM2(val, unit);
    return toStored(mm2, "mm2");
  }
  if (uom === "mm3") {
    const mm3 = toBase.volumeToMM3(val, unit);
    return toStored(mm3, "mm3");
  }
  if (uom === "g") {
    const g = toBase.massToG(val, unit);
    return toStored(g, "g");
  }
  throw new Error(`Unsupported uom: ${uom}`);
}
