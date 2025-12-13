from decimal import Decimal, ROUND_HALF_UP

DIMENSIONS = {"length", "area", "volume", "weight", "count"}

UNIT_MULTIPLIER = {
    "length": {"mm": 1, "cm": 10, "m": 1000},
    # IMPORTANT: area multipliers are the SQUARE of length multipliers
    "area": {"mm2": 1, "cm2": 100, "m2": 1_000_000},
    "volume": {"mm3": 1, "cm3": 1_000, "m3": 1_000_000_000, "ml": 1_000},
    "weight": {"mg": 1, "g": 1_000, "kg": 1_000_000},
    # Count items are base-1
    "count": {"unit": 1, "ea": 1},
}


def _norm_unit(u: str) -> str:
    """Normalize unit strings such as m² / m^2 / m2 to the multiplier key."""

    return (u or "").lower().replace("²", "2").replace("^2", "2")


def uom_multiplier(dimension: str, unit: str) -> int:
    """Safe accessor for UNIT_MULTIPLIER with unit normalization and fallbacks."""

    dim = (dimension or "count").lower()
    units = UNIT_MULTIPLIER.get(dim, {})
    mult = units.get(_norm_unit(unit))
    return mult if mult is not None else 1


def to_base_qty(dimension: str, unit: str, qty_decimal: Decimal) -> int:
    """Convert a decimal quantity in the given UOM to base integer units."""

    mult = uom_multiplier(dimension, unit)
    return int((Decimal(qty_decimal) * Decimal(mult)).to_integral_value(rounding=ROUND_HALF_UP))


def from_base_qty(dimension: str, unit: str, qty_base: int) -> Decimal:
    mult = uom_multiplier(dimension, unit)
    if mult == 0:
        return Decimal(0)
    return (Decimal(qty_base) / Decimal(mult)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)

DEFAULT_UNIT_FOR = {
    "length": "mm",
    "area": "mm2",
    "volume": "mm3",
    "weight": "mg",
    "count": "ea",
}

BASE_UNIT_LABEL = {
    "length": "mm",
    "area": "mm²",
    "volume": "mm³",
    "weight": "mg",
    "count": "ea",
}


def default_unit_for(dimension: str) -> str:
    return DEFAULT_UNIT_FOR.get(dimension, "ea")


def to_base(value_decimal: str | float | Decimal, unit: str, dimension: str) -> int:
    if dimension not in DIMENSIONS:
        raise ValueError(f"Unknown dimension: {dimension}")
    units = UNIT_MULTIPLIER.get(dimension, {})
    if unit not in units:
        raise ValueError(f"Unit {unit} not valid for {dimension}")
    d = Decimal(str(value_decimal))
    mult = Decimal(units[unit])
    return int((d * mult).to_integral_value(rounding=ROUND_HALF_UP))


def from_base(value_int: int, unit: str, dimension: str) -> Decimal:
    if dimension not in DIMENSIONS:
        raise ValueError(f"Unknown dimension: {dimension}")
    units = UNIT_MULTIPLIER.get(dimension, {})
    if unit not in units:
        raise ValueError(f"Unit {unit} not valid for {dimension}")
    mult = Decimal(units[unit])
    return (Decimal(value_int) / mult).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def allowed_units_for(dimension: str) -> list[str]:
    if dimension not in DIMENSIONS:
        raise ValueError(f"Unknown dimension: {dimension}")
    return list(UNIT_MULTIPLIER[dimension].keys())

__all__ = [
    "allowed_units_for",
    "BASE_UNIT_LABEL",
    "DEFAULT_UNIT_FOR",
    "DIMENSIONS",
    "_norm_unit",
    "default_unit_for",
    "from_base",
    "from_base_qty",
    "to_base",
    "to_base_qty",
    "uom_multiplier",
    "UNIT_MULTIPLIER",
]
