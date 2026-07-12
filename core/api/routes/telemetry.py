from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from core.auth.dependencies import require_permission
from core.auth.permissions import PERMISSION_SETTINGS_READ
from core.config.manager import save_config
from core.telemetry import MODULE_EVENT_NAMES, clear_telemetry_queue, emit_telemetry
from tgc.security import require_token_ctx

router = APIRouter()


class ModuleTelemetryEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_name: str


class TelemetryPreference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool


@router.post("/telemetry/event")
def record_module_event(
    body: ModuleTelemetryEvent,
    _permission=Depends(require_permission(PERMISSION_SETTINGS_READ)),
    _token: None = Depends(require_token_ctx),
) -> dict[str, bool]:
    accepted = body.event_name in MODULE_EVENT_NAMES and emit_telemetry(body.event_name, deduplicate=False)
    return {"ok": True, "queued": accepted}


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
        emit_telemetry("installation_first_launch")
    else:
        clear_telemetry_queue()
    return {"ok": True, "enabled": body.enabled}
