from __future__ import annotations

from fastapi import APIRouter

from core.appdb.engine import debug_db_where

router = APIRouter(prefix="/dev", tags=["dev"])


@router.get("/db/where")
def dev_db_where():
    return debug_db_where()
