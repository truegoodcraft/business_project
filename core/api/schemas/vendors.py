# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class VendorBase(BaseModel):
    name: Optional[str] = None
    contact: Optional[str] = None
    role: Optional[str] = Field(None, description="vendor|contact")
    is_vendor: Optional[bool] = Field(False, description="If true, appears in vendor dropdowns")
    is_org: Optional[bool] = Field(False, description="If true, treat as company/organization")
    organization_id: Optional[int] = None
    meta: Optional[str] = None


class VendorCreate(VendorBase):
    name: str


class VendorUpdate(VendorBase):
    pass


class VendorOut(VendorBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
