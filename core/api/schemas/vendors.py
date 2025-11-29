# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Optional

from pydantic import BaseModel, Field


class VendorBase(BaseModel):
    name: Optional[str] = None
    contact: Optional[str] = None
    role: Optional[str] = Field(None, description="vendor|contact|both")
    kind: Optional[str] = Field(None, description="org|person")
    organization_id: Optional[int] = None
    meta: Optional[str] = None


class VendorCreate(VendorBase):
    name: str


class VendorUpdate(VendorBase):
    pass


class VendorOut(VendorBase):
    id: int
    created_at: str

    class Config:
        from_attributes = True
