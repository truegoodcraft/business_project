from fastapi import APIRouter, Depends, Body
from typing import Dict, Any

from core.config.writes import require_writes
from core.config.manager import load_config, save_config

router = APIRouter()

@router.get("/config")
def get_config() -> Dict[str, Any]:
    return load_config().model_dump()

@router.post("/config")
def update_config(
    payload: Dict[str, Any] = Body(...),
    _writes: None = Depends(require_writes)
) -> Dict[str, Any]:
    save_config(payload)
    return {"ok": True, "restart_required": True}
