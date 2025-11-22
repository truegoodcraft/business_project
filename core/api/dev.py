from __future__ import annotations
from fastapi import APIRouter
from core.appdb.engine import db_debug_info

router = APIRouter()


@router.get("/dev/db/where")
def dev_db_where():
    return db_debug_info()
