from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

from fastapi import APIRouter, Query

router = APIRouter(prefix="/app", tags=["logs"])
public_router = APIRouter(prefix="/app", tags=["logs"])


def _journals_dir() -> Path:
    root = os.environ.get("LOCALAPPDATA")
    if not root:
        # Linux/macOS fallback
        root = os.path.expanduser("~/.local/share")
    d = Path(root) / "BUSCore" / "app" / "data" / "journals"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _read_jsonl(path: Path, source: str) -> Iterator[dict]:
    if not path.exists():
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            obj["_source"] = source
            yield obj


def _parse_ts(s: str) -> datetime | None:
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _normalize(entry: dict) -> dict | None:
    ts = _parse_ts(str(entry.get("timestamp") or ""))
    if ts is None:
        return None
    e = {"ts": ts.isoformat(), "kind": entry.get("type") or entry.get("_source")}
    if e["kind"] in ("purchase", "consume", "adjustment"):
        e["domain"] = "inventory"
        e["item_id"] = entry.get("item_id")
        e["qty_change"] = entry.get("qty_change")
        e["unit_cost_cents"] = entry.get("unit_cost_cents")
        e["source_kind"] = entry.get("source_kind")
        e["source_id"] = entry.get("source_id")
    elif e["kind"] in ("run", "manufacturing.run", "manufacturing_run"):
        e["domain"] = "manufacturing"
        e["recipe_id"] = entry.get("recipe_id")
        e["recipe_name"] = entry.get("recipe_name")
        e["output_item_id"] = entry.get("output_item_id")
        e["output_qty"] = entry.get("output_qty")
    elif e["kind"] in ("recipe.create", "recipe.update", "recipe.delete"):
        e["domain"] = "recipes"
        e["recipe_id"] = entry.get("recipe_id")
        e["recipe_name"] = entry.get("recipe_name")
    else:
        e["domain"] = entry.get("_source") or "other"
    return e


def _load_events(days: int, cursor: str | None, limit: int):
    jd = _journals_dir()
    files = [
        (jd / "inventory.jsonl", "inventory"),
        (jd / "manufacturing.jsonl", "manufacturing"),
        (jd / "recipes.jsonl", "recipes"),
    ]
    cutoff = datetime.now(timezone.utc) - timedelta(days=int(days))

    all_events = []
    for p, src in files:
        for obj in _read_jsonl(p, src):
            e = _normalize(obj)
            if not e:
                continue
            dt = _parse_ts(e["ts"])
            if dt is None:
                continue
            if dt < cutoff:
                continue
            all_events.append(e)

    all_events.sort(key=lambda x: x["ts"], reverse=True)

    start = len(all_events) if cursor else 0
    if cursor:
        for i, ev in enumerate(all_events):
            if ev["ts"] < cursor:
                start = i
                break

    batch = all_events[start : start + limit]
    next_cursor = batch[-1]["ts"] if len(batch) == limit else None
    return batch, next_cursor


@router.get("/logs")
@public_router.get("/logs")
def list_logs(
    days: int = Query(90, ge=1, le=365), cursor: str | None = None, limit: int = Query(200, ge=10, le=1000)
):
    items, next_cursor = _load_events(days, cursor, limit)
    return {"events": items, "next_cursor": next_cursor}
