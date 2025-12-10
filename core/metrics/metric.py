from decimal import Decimal, ROUND_HALF_UP

DIMENSIONS = {"length", "area", "volume", "weight", "count"}

UNIT_MULTIPLIER = {
    "length": {"mm": 1, "cm": 10, "m": 1000},
    "area": {"mm2": 1, "cm2": 100, "m2": 1_000_000},
    "volume": {"mm3": 1, "cm3": 1_000, "m3": 1_000_000_000, "ml": 1_000},
    "weight": {"mg": 1, "g": 1_000, "kg": 1_000_000},
    "count": {"unit": 1_000, "ea": 1_000},
}

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
    "count": "milli-units",
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
    "default_unit_for",
    "from_base",
    "to_base",
    "UNIT_MULTIPLIER",
]
