# core/wave/mapping.py
import sqlite3
from core.appdb.paths import resolve_db_path
DB_PATH = resolve_db_path()

def ensure_table():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS wave_item_map (wave_product_id TEXT PRIMARY KEY, item_id INTEGER NOT NULL REFERENCES items(id))")
    con.commit(); con.close()

def get_item_id(wave_product_id: str):
    ensure_table()
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT item_id FROM wave_item_map WHERE wave_product_id=?", (wave_product_id,))
    row = cur.fetchone(); con.close()
    return None if not row else int(row[0])

def upsert(wave_product_id: str, item_id: int):
    ensure_table()
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("INSERT INTO wave_item_map (wave_product_id, item_id) VALUES (?, ?) ON CONFLICT(wave_product_id) DO UPDATE SET item_id=excluded.item_id", (wave_product_id, item_id))
    con.commit(); con.close()

