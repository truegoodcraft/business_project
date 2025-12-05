# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from core.api.security import writes_enabled
from core.appdb.engine import debug_db_where

router = APIRouter(prefix="/dev", tags=["dev"])


class WritesPayload(BaseModel):
    enabled: bool


@router.get("/writes")
def get_writes(request: Request):
    return {"enabled": writes_enabled(request)}


@router.post("/writes")
def set_writes(payload: WritesPayload, request: Request):
    request.app.state.allow_writes = bool(payload.enabled)
    return {"enabled": request.app.state.allow_writes}


@router.get("/db/where")
def dev_db_where():
    return debug_db_where()
