# TGC BUS Core (Business Utility System Core)
# Copyright (C) 2025 True Good Craft
#
# This file is part of TGC BUS Core.
#
# TGC BUS Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# TGC BUS Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with TGC BUS Core.  If not, see <https://www.gnu.org/licenses/>.

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from core.appdb.init import connect, init_db, now_iso

router = APIRouter(prefix="/app", tags=["app"])
init_db()


def rows(cur):  # convert sqlite rows -> dicts
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


# ---- Vendors ----
@router.get("/vendors")
def list_vendors() -> List[Dict[str, Any]]:
    con = connect()
    cur = con.execute("SELECT * FROM vendors ORDER BY id DESC")
    out = rows(cur)
    con.close()
    return out


@router.post("/vendors")
def create_vendor(body: Dict[str, Any]) -> Dict[str, Any]:
    if not body.get("name"):
        raise HTTPException(400, "name required")
    con = connect()
    con.execute(
        "INSERT INTO vendors(name,contact,notes,created_at) VALUES (?,?,?,?)",
        (body["name"], body.get("contact"), body.get("notes"), now_iso()),
    )
    vid = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    con.commit()
    con.close()
    return {"id": vid}


@router.put("/vendors/{vid}")
def update_vendor(vid: int, body: Dict[str, Any]) -> Dict[str, Any]:
    con = connect()
    con.execute(
        "UPDATE vendors SET name=?, contact=?, notes=? WHERE id=?",
        (body.get("name"), body.get("contact"), body.get("notes"), vid),
    )
    con.commit()
    con.close()
    return {"ok": True}


@router.delete("/vendors/{vid}")
def delete_vendor(vid: int) -> Dict[str, Any]:
    con = connect()
    con.execute("DELETE FROM vendors WHERE id=?", (vid,))
    con.commit()
    con.close()
    return {"ok": True}


# ---- Items ----
@router.get("/items")
def list_items() -> List[Dict[str, Any]]:
    con = connect()
    cur = con.execute("""SELECT * FROM items ORDER BY id DESC""")
    out = rows(cur)
    con.close()
    return out


@router.post("/items")
def create_item(body: Dict[str, Any]) -> Dict[str, Any]:
    if not body.get("name"):
        raise HTTPException(400, "name required")
    con = connect()
    con.execute(
        """INSERT INTO items(vendor_id,sku,name,qty,unit,price,notes,created_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
        (
            body.get("vendor_id"),
            body.get("sku"),
            body["name"],
            body.get("qty", 0),
            body.get("unit", "ea"),
            body.get("price"),
            body.get("notes"),
            now_iso(),
        ),
    )
    iid = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    con.commit()
    con.close()
    return {"id": iid}


@router.put("/items/{iid}")
def update_item(iid: int, body: Dict[str, Any]) -> Dict[str, Any]:
    con = connect()
    con.execute(
        """UPDATE items SET vendor_id=?, sku=?, name=?, qty=?, unit=?, price=?, notes=? WHERE id=?""",
        (
            body.get("vendor_id"),
            body.get("sku"),
            body.get("name"),
            body.get("qty", 0),
            body.get("unit", "ea"),
            body.get("price"),
            body.get("notes"),
            iid,
        ),
    )
    con.commit()
    con.close()
    return {"ok": True}


@router.delete("/items/{iid}")
def delete_item(iid: int) -> Dict[str, Any]:
    con = connect()
    con.execute("DELETE FROM items WHERE id=?", (iid,))
    con.commit()
    con.close()
    return {"ok": True}


# ---- Tasks ----
@router.get("/tasks")
def list_tasks() -> List[Dict[str, Any]]:
    con = connect()
    cur = con.execute("SELECT * FROM tasks ORDER BY id DESC")
    out = rows(cur)
    con.close()
    return out


@router.post("/tasks")
def create_task(body: Dict[str, Any]) -> Dict[str, Any]:
    if not body.get("title"):
        raise HTTPException(400, "title required")
    con = connect()
    con.execute(
        """INSERT INTO tasks(item_id,title,status,due,notes,created_at)
                   VALUES (?,?,?,?,?,?)""",
        (
            body.get("item_id"),
            body["title"],
            body.get("status", "todo"),
            body.get("due"),
            body.get("notes"),
            now_iso(),
        ),
    )
    tid = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    con.commit()
    con.close()
    return {"id": tid}


@router.put("/tasks/{tid}")
def update_task(tid: int, body: Dict[str, Any]) -> Dict[str, Any]:
    con = connect()
    con.execute(
        """UPDATE tasks SET item_id=?, title=?, status=?, due=?, notes=? WHERE id=?""",
        (
            body.get("item_id"),
            body.get("title"),
            body.get("status", "todo"),
            body.get("due"),
            body.get("notes"),
            tid,
        ),
    )
    con.commit()
    con.close()
    return {"ok": True}


@router.delete("/tasks/{tid}")
def delete_task(tid: int) -> Dict[str, Any]:
    con = connect()
    con.execute("DELETE FROM tasks WHERE id=?", (tid,))
    con.commit()
    con.close()
    return {"ok": True}


# ---- Attachments ----
@router.get("/attachments/{etype}/{eid}")
def list_attachments(etype: str, eid: int) -> List[Dict[str, Any]]:
    con = connect()
    cur = con.execute(
        "SELECT * FROM attachments WHERE entity_type=? AND entity_id=? ORDER BY id DESC",
        (etype, eid),
    )
    out = rows(cur)
    con.close()
    return out


@router.post("/attachments/{etype}/{eid}")
def add_attachment(etype: str, eid: int, body: Dict[str, Any]) -> Dict[str, Any]:
    rid = body.get("reader_id")
    if not rid:
        raise HTTPException(400, "reader_id required")
    con = connect()
    con.execute(
        """INSERT INTO attachments(entity_type,entity_id,reader_id,label,created_at)
                   VALUES (?,?,?,?,?)""",
        (etype, eid, rid, body.get("label"), now_iso()),
    )
    aid = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    con.commit()
    con.close()
    return {"id": aid}


@router.delete("/attachments/{aid}")
def delete_attachment(aid: int) -> Dict[str, Any]:
    con = connect()
    con.execute("DELETE FROM attachments WHERE id=?", (aid,))
    con.commit()
    con.close()
    return {"ok": True}
