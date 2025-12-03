import math

UOMS = ['ea', 'g', 'mm', 'mm2', 'mm3']


def round_half_away(val: float) -> int:
    sign = -1 if val < 0 else 1
    return int(math.floor(abs(val) + 0.5)) * sign


def to_stored(value: float, uom: str) -> int:
    if uom == 'ea':
        return round_half_away(value)
    return round_half_away(value * 100)


def to_display(qty_stored: int, uom: str) -> float:
    if uom == 'ea':
        return qty_stored
    return qty_stored / 100


def test_roundtrip_measurements():
    samples = [0, 1, 1.25, 1.5, -1.5, 2.01]
    for uom in UOMS:
        for sample in samples:
            stored = to_stored(sample, uom)
            display = to_display(stored, uom)
            if uom == 'ea':
                assert display == round_half_away(sample)
            else:
                assert abs(display - round(sample, 2)) <= 0.01
