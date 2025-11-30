# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _ContactBase(BaseModel):
    name: Optional[str] = None
    # NOTE: backend still stores contact as a single string; UI splits email/phone
    contact: Optional[str] = None
    role: Optional[str] = Field(default="contact")
    is_vendor: Optional[bool] = False
    is_org: Optional[bool] = None
    organization_id: Optional[int] = None
    meta: Optional[Dict[str, Any]] = None

    @field_validator("contact", mode="before")
    @classmethod
    def _coerce_contact(cls, v: Union[str, Dict[str, Any], None]):
        if isinstance(v, dict):
            email = (v.get("email") or "").strip()
            phone = (v.get("phone") or "").strip()
            joined = " | ".join([x for x in (email, phone) if x])
            return joined or None
        return v

    @field_validator("meta", mode="before")
    @classmethod
    def _coerce_meta(cls, v: Optional[Union[str, Dict[str, Any]]]):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return None
        return v


class VendorCreate(_ContactBase):
    # creation still requires a name
    name: str


class VendorUpdate(_ContactBase):
    # all optional for PATCH-style PUT
    pass


class VendorOut(_ContactBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
