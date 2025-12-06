# SPDX-License-Identifier: AGPL-3.0-or-later
"""Money-related helpers."""

from decimal import Decimal, ROUND_HALF_UP


def round_half_up_cents(value: float) -> int:
    """Round a currency amount to cents using half-up semantics."""
    quantized = Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(quantized)


__all__ = ["round_half_up_cents"]
