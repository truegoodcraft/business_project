"""Shared helpers for integration configuration messaging."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from core.conn_broker import resolve_service_account_path

from .modules.google_drive import DriveModuleConfig

_DEFAULT_SERVICE_ACCOUNT_PLACEHOLDER = "service-account@example.com"


def load_drive_module_config(path: Path) -> DriveModuleConfig:
    """Load the Drive module config from ``path`` if it exists."""

    resolved = path.expanduser()
    if resolved.exists():
        try:
            data = json.loads(resolved.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    else:
        data = {}
    return DriveModuleConfig.from_dict(data)


def service_account_email(module_config: DriveModuleConfig) -> Optional[str]:
    """Return the stored service-account email, if available."""

    value = module_config.credentials.get("client_email")
    if isinstance(value, str):
        trimmed = value.strip()
        if trimmed:
            return trimmed
    return None


def _read_service_account_email(creds_path: Path) -> Optional[str]:
    try:
        data = json.loads(creds_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    email = data.get("client_email")
    if isinstance(email, str):
        trimmed = email.strip()
        if trimmed:
            return trimmed
    return None


def _resolved_service_account_email() -> Optional[str]:
    creds_path = resolve_service_account_path()
    if not creds_path.is_file():
        return None
    return _read_service_account_email(creds_path)


def format_sheets_missing_env_message(email: Optional[str]) -> str:
    """Return a consistent warning about missing Sheets configuration."""

    share_target = email or _resolved_service_account_email() or _DEFAULT_SERVICE_ACCOUNT_PLACEHOLDER
    return (
        "Sheets is not configured. Set SHEET_INVENTORY_ID in .env (File → Share with: "
        f"{share_target})."
    )


def sheets_share_hint(email: Optional[str]) -> str:
    """Return guidance for sharing the spreadsheet with the service account."""

    share_target = email or _resolved_service_account_email() or _DEFAULT_SERVICE_ACCOUNT_PLACEHOLDER
    return (
        f"Share the sheet with {share_target} as Viewer. Set SHEET_INVENTORY_ID in .env."
    )


def format_drive_share_message(root_id: str, email: Optional[str]) -> str:
    """Return a consistent instruction to share a Drive root with the service account."""

    share_target = email or _resolved_service_account_email() or _DEFAULT_SERVICE_ACCOUNT_PLACEHOLDER
    return f"Share {root_id} with {share_target} and retry."


def is_drive_permission_error(exc: Exception) -> bool:
    """Return True if ``exc`` represents a 403/404 Drive permission error."""

    status_candidates = [
        getattr(getattr(exc, "resp", None), "status", None),
        getattr(exc, "status", None),
        getattr(exc, "status_code", None),
    ]
    for candidate in status_candidates:
        try:
            if int(candidate) in {403, 404}:  # type: ignore[arg-type]
                return True
        except (TypeError, ValueError):
            continue
    text = str(exc)
    if "HttpError" in exc.__class__.__name__:
        if " 403" in text or " 404" in text or text.startswith("<HttpError 403") or text.startswith(
            "<HttpError 404"
        ):
            return True
    return False
