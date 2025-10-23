"""Organizer API endpoints for generating file operation plans."""

from __future__ import annotations

import os
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.organizer.duplicates import find_duplicates, pick_keeper
from core.organizer.rename import normalize_filename
from core.plans.model import Action, ActionKind, Plan
from core.plans.store import save_plan
from core.reader.ids import to_rid
from core.settings.reader_state import get_allowed_local_roots

router = APIRouter(prefix="/organizer", tags=["organizer"])


class DupBody(BaseModel):
    start_path: str
    quarantine_dir: Optional[str] = None


class RenameBody(BaseModel):
    start_path: str


def _allowed(path: str, roots: Optional[List[str]] = None) -> bool:
    abs_path = os.path.normcase(os.path.abspath(path))
    for root in roots or get_allowed_local_roots():
        abs_root = os.path.normcase(os.path.abspath(root))
        try:
            if os.path.commonpath([abs_path, abs_root]) == abs_root:
                return True
        except ValueError:
            # Different drive letters on Windows raise ValueError.
            continue
    return False


def _maybe_to_rid(path: str, roots: List[str]) -> Optional[str]:
    try:
        return to_rid(path, roots)
    except Exception:
        return None


@router.post("/duplicates/plan")
def duplicates_plan(body: DupBody):
    start = os.path.normpath(body.start_path)
    if not os.path.exists(start):
        raise HTTPException(status_code=404, detail="start_path does not exist")
    if not os.path.isdir(start):
        raise HTTPException(status_code=400, detail="start_path must be a directory")
    roots = get_allowed_local_roots()
    if not _allowed(start, roots):
        raise HTTPException(status_code=400, detail="start_path not under allowed local roots")
    quarantine_dir = body.quarantine_dir or os.path.join(
        os.path.expanduser("~"), "Documents", "Quarantine", "Duplicates"
    )
    if not _allowed(quarantine_dir, roots):
        raise HTTPException(status_code=400, detail="quarantine_dir not under allowed local roots")
    os.makedirs(quarantine_dir, exist_ok=True)

    duplicates = find_duplicates(start)
    actions: List[Action] = []
    for digest, group in duplicates.items():
        keeper = pick_keeper(group)
        counter = 1
        for path in group:
            if path == keeper:
                continue
            name = os.path.basename(path)
            destination = os.path.join(quarantine_dir, name)
            base, ext = os.path.splitext(name)
            suffix = 1
            while os.path.exists(destination):
                destination = os.path.join(quarantine_dir, f"{base}-dup{suffix}{ext}")
                suffix += 1
            action = Action(
                id=f"dup-{digest[:8]}-{counter}",
                kind=ActionKind.MOVE,
                src_id=_maybe_to_rid(path, roots),
                dst_parent_id=_maybe_to_rid(os.path.dirname(destination), roots),
                dst_name=os.path.basename(destination),
                meta={
                    "src_path": path,
                    "dst_path": destination,
                    "dst_parent_path": os.path.dirname(destination),
                    "dst_name": os.path.basename(destination),
                },
            )
            actions.append(action)
            counter += 1

    plan = Plan(
        id=f"org-dup-{int(datetime.utcnow().timestamp())}",
        source="organizer",
        title=f"Organizer: Duplicates from {start}",
        note=f"Move duplicates to {quarantine_dir}",
        actions=actions,
    )
    save_plan(plan)
    return {"plan_id": plan.id, "actions": len(actions)}


@router.post("/rename/plan")
def rename_plan(body: RenameBody):
    start = os.path.normpath(body.start_path)
    if not os.path.exists(start):
        raise HTTPException(status_code=404, detail="start_path does not exist")
    if not os.path.isdir(start):
        raise HTTPException(status_code=400, detail="start_path must be a directory")
    roots = get_allowed_local_roots()
    if not _allowed(start, roots):
        raise HTTPException(status_code=400, detail="start_path not under allowed local roots")
    actions: List[Action] = []
    counter = 1
    for dirpath, _, filenames in os.walk(start):
        for filename in filenames:
            current_path = os.path.join(dirpath, filename)
            normalized_name = normalize_filename(filename)
            if normalized_name == filename:
                continue
            destination_path = os.path.join(dirpath, normalized_name)
            # Skip if another file already occupies the destination name.
            if os.path.exists(destination_path) and os.path.normcase(destination_path) != os.path.normcase(
                current_path
            ):
                continue
            action = Action(
                id=f"rn-{counter}",
                kind=ActionKind.RENAME,
                src_id=_maybe_to_rid(current_path, roots),
                dst_parent_id=_maybe_to_rid(dirpath, roots),
                dst_name=normalized_name,
                meta={
                    "src_path": current_path,
                    "dst_path": destination_path,
                    "dst_parent_path": dirpath,
                    "dst_name": normalized_name,
                },
            )
            actions.append(action)
            counter += 1

    plan = Plan(
        id=f"org-rn-{int(datetime.utcnow().timestamp())}",
        source="organizer",
        title=f"Organizer: Rename normalize under {start}",
        note="Conservative normalization of filenames",
        actions=actions,
    )
    save_plan(plan)
    return {"plan_id": plan.id, "actions": len(actions)}
