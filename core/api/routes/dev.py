# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel

from core.api.security import writes_enabled
from core.api.utils.devguard import require_dev
from core.appdb.engine import debug_db_where

# Add require_dev dependency
router = APIRouter(prefix="/dev", tags=["dev"], dependencies=[Depends(require_dev)])


class WritesPayload(BaseModel):
    enabled: bool


@router.get("/writes")
def get_writes(request: Request):
    return {"enabled": writes_enabled(request)}


# Stub out POST /writes
@router.post("/writes")
def set_writes(_payload: WritesPayload, _request: Request):
    raise HTTPException(status_code=404, detail="Not found")


@router.get("/db/where")
def dev_db_where():
    return debug_db_where()
