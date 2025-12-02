from fastapi import APIRouter
import os, sqlite3

router = APIRouter(prefix="/dev", tags=["dev"])


@router.get("/db-info")
def db_info():
    db = os.environ.get("BUS_DB", "data/app.db")
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
