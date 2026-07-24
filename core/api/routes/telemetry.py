from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from core.auth.dependencies import require_permission
from core.auth.permissions import PERMISSION_SETTINGS_READ
from core.config.manager import save_config
from core.telemetry import (
    clear_telemetry_queue,
    emit_startup_telemetry,
    telemetry_status,
)
from tgc.security import require_token_ctx

router = APIRouter()


class TelemetryPreference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool


@router.post("/telemetry/preference")
def set_telemetry_preference(
    body: TelemetryPreference,
    _permission=Depends(require_permission(PERMISSION_SETTINGS_READ)),
    _token: None = Depends(require_token_ctx),
) -> dict[str, bool]:
    # Deliberately independent of the business write gate so opt-out always works.
    save_config({
        "telemetry": {
            "enabled": body.enabled,
            "disclosure_acknowledged": True,
        }
    })
    if body.enabled:
        emit_startup_telemetry()
    else:
        clear_telemetry_queue()
    return {"ok": True, "enabled": body.enabled}


@router.get("/telemetry/status")
def get_telemetry_status(
    _permission=Depends(require_permission(PERMISSION_SETTINGS_READ)),
    _token: None = Depends(require_token_ctx),
) -> dict[str, object]:
    return telemetry_status()
