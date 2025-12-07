# Copyright (C) 2025 BUS Core Authors
# SPDX-License-Identifier: AGPL-3.0-or-later

# core/api/schemas_measure.py
from pydantic import BaseModel, Field
from typing import Literal

UOM = Literal['ea', 'g', 'mm', 'mm2', 'mm3']

class QuantityStored(BaseModel):
    uom: UOM
    qty_stored: int = Field(..., description='Canonical stored quantity (metric ×100 for g/mm/mm2/mm3, plain int for ea)')
