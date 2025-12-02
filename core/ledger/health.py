# core/ledger/health.py
import sqlite3, os
DB_PATH = os.environ.get("BUS_DB", "data/app.db")

def health_summary():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    # Detect items.qty or qty_stored
    cur.execute("PRAGMA table_info(items)")
    cols = {r[1] for r in cur.fetchall()}
    if "qty" in cols:
        qty_expr = "qty"
        scale = 1.0
    elif "qty_stored" in cols:
        qty_expr = "(qty_stored / 100.0)"
        scale = 1.0
    else:
        return {"desync": True, "problems": [{"reason": "No qty column in items"}]}
    cur.execute(
        f"""
        SELECT i.id, i.name, {qty_expr} AS onhand,
               IFNULL((SELECT SUM(qty_remaining) FROM item_batches b WHERE b.item_id=i.id), 0.0) AS valued_qty
        FROM items i
        """
    )
    problems = []
    for iid, name, onhand, valued in cur.fetchall():
        if round(float(onhand or 0), 4) != round(float(valued or 0), 4):
            problems.append({"item_id": iid, "name": name, "items_qty": onhand, "batch_sum": valued})
    return {"desync": len(problems) > 0, "problems": problems}

