from __future__ import annotations

from typing import Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .ids import rid_to_path, to_rid
from .roots import get_allowed_local_roots

router = APIRouter(prefix="/reader/local", tags=["reader-local"])


class PathsBody(BaseModel):
    paths: List[str]


class IdsBody(BaseModel):
    ids: List[str]


@router.post("/resolve_ids")
def resolve_ids(body: PathsBody) -> Dict[str, str]:
    roots = get_allowed_local_roots()
    out: Dict[str, str] = {}
    for path in body.paths:
        try:
            out[path] = to_rid(path, roots)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    return out


@router.post("/resolve_paths")
def resolve_paths(body: IdsBody) -> Dict[str, str | None]:
    roots = get_allowed_local_roots()
    out: Dict[str, str | None] = {}
    for rid in body.ids:
        try:
            out[rid] = rid_to_path(rid, roots)
        except Exception:
            out[rid] = None
    return out
