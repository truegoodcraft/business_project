# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from fastapi import APIRouter, Request
from pathlib import Path
import json
from pydantic import BaseModel

from core.api.security import writes_enabled
from core.appdata.paths import license_path, buscore_root

router = APIRouter(prefix="/dev", tags=["dev"])


class WritesPayload(BaseModel):
    enabled: bool


@router.get("/writes")
def get_writes(request: Request):
    return {"enabled": writes_enabled(request)}


@router.post("/writes")
def set_writes(payload: WritesPayload, request: Request):
    request.app.state.allow_writes = bool(payload.enabled)
    return {"enabled": request.app.state.allow_writes}


@router.get("/license")
def dev_license():
    """
    STUB with SoT path awareness:
    - If %LOCALAPPDATA%\BUSCore\license.json exists, return its JSON.
    - Otherwise, return a labeled stub with the expected path and root.
    """

    path: Path = license_path()
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        # Fallback to stub on any read/parse error
        pass
    return {
        "stub": True,
        "status": "dev",
        "license_path": str(path),
        "root": str(buscore_root()),
    }
