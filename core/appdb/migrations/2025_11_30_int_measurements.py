# core/appdb/migrations/2025_11_30_int_measurements.py
from datetime import datetime
from contextlib import contextmanager
import sqlite3
import os

DB_PATH = os.environ.get('BUS_DB', 'data/app.db')

@contextmanager
def conn():
  con = sqlite3.connect(DB_PATH)
  try:
    yield con
  finally:
    con.commit()
    con.close()

def column_exists(cur, table, col):
  cur.execute(f"PRAGMA table_info({table})")
  return any(r[1] == col for r in cur.fetchall())


def round_half_away(val: float) -> int:
  sign = -1 if val < 0 else 1
  return int((abs(val) + 0.5) // 1) * sign


def apply():
  with conn() as con:
    cur = con.cursor()
    # items: add uom, qty_stored
    if not column_exists(cur, 'items', 'uom'):
      cur.execute("ALTER TABLE items ADD COLUMN uom TEXT NOT NULL DEFAULT 'ea'")
    if not column_exists(cur, 'items', 'qty_stored'):
      cur.execute("ALTER TABLE items ADD COLUMN qty_stored INTEGER NOT NULL DEFAULT 0")

    # backfill from legacy qty/unit if present
    try:
      cur.execute("SELECT id, qty, unit FROM items")
      rows = cur.fetchall()
      for _id, qty, unit in rows:
        if qty is None:
          continue
        # default legacy semantics: counts in 'ea' if unit missing
        uom = (unit or 'ea')
        if uom not in ('ea','g','mm','mm2','mm3'):
          uom = 'ea'
        if uom == 'ea':
          stored = round_half_away(qty)
        else:
          stored = round_half_away(qty * 100)
        cur.execute("UPDATE items SET uom=?, qty_stored=? WHERE id=?", (uom, stored, _id))
    except sqlite3.OperationalError:
      # items table may lack legacy columns; ignore
      pass

    # recipes
    cur.execute("CREATE TABLE IF NOT EXISTS recipes (id INTEGER PRIMARY KEY, name TEXT NOT NULL, notes TEXT)")
    cur.execute(
        "CREATE TABLE IF NOT EXISTS recipe_items ("
        "id INTEGER PRIMARY KEY, recipe_id INTEGER NOT NULL, item_id INTEGER NOT NULL, role TEXT NOT NULL, qty_stored INTEGER NOT NULL,"
        "FOREIGN KEY(recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,"
        "FOREIGN KEY(item_id) REFERENCES items(id))"
    )

if __name__ == '__main__':
  apply()
  print("Migration 2025_11_30_int_measurements applied")
