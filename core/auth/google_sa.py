from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_creds_path() -> Path:
    envp = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if envp:
        p = Path(os.path.expandvars(os.path.expanduser(envp)))
        if not p.is_absolute():
            p = (_project_root() / p).resolve()
        return p
    return (_project_root() / "credentials" / "service-account.json").resolve()


def validate_google_service_account() -> Tuple[bool, Dict[str, Any]]:
    """
    Validate presence & basic structure of service-account JSON.
    Returns (ready, meta) where meta has no secrets.
    """

    p = _resolve_creds_path()
    meta: Dict[str, Any] = {"path_exists": p.exists(), "path": str(p)}
    if not p.exists():
        return False, {
            **meta,
            "detail": "missing_credentials",
            "hint": "Place service-account.json under credentials/ or set GOOGLE_APPLICATION_CREDENTIALS",
        }
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
        if obj.get("type") != "service_account":
            return False, {**meta, "detail": "not_service_account"}
        meta.update({
            "project_id": obj.get("project_id"),
            "client_email": obj.get("client_email"),
        })
        return True, meta
    except Exception as e:  # pragma: no cover - defensive
        return False, {**meta, "detail": "invalid_json", "error": str(e)}


__all__ = ["validate_google_service_account"]
