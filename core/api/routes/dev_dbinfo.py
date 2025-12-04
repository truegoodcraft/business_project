# SPDX-License-Identifier: AGPL-3.0-or-later
from fastapi import APIRouter
import sqlite3

from core.appdb.paths import resolve_db_path

"""Development helper endpoints for inspecting the active SQLite DB."""

router = APIRouter(prefix="/dev", tags=["dev"])


@router.get("/db-info")
def db_info():
    db = resolve_db_path()
    con = sqlite3.connect(db); cur = con.cursor()
    try:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        cols = {}
        for t in tables:
            cur.execute(f"PRAGMA table_info({t})")
            cols[t] = [r[1] for r in cur.fetchall()]
        return {"db_path": db, "tables": tables, "columns": cols}
    finally:
        con.close()
