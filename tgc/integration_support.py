"""Shared helpers for integration configuration messaging."""

from __future__ import annotations

import os, json
from pathlib import Path
from typing import Optional

from .modules.google_drive import DriveModuleConfig

_DEFAULT_SERVICE_ACCOUNT_PLACEHOLDER = "service-account@example.com"


def _project_root() -> Path:
    # tgc/ -> project root
    return Path(__file__).resolve().parents[1]


def _service_account_credentials_path() -> str:
    """
    Resolve GOOGLE_APPLICATION_CREDENTIALS robustly on Windows/macOS/Linux:
    - expand %VARS% and ~
    - if relative, resolve against project root
    - default to credentials/service-account.json
    """

    envp = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if envp:
        expanded = os.path.expandvars(os.path.expanduser(str(envp)))
        p = Path(expanded)
        if not p.is_absolute():
            p = (_project_root() / p).resolve()
        return str(p)
    return str((_project_root() / "credentials" / "service-account.json").resolve())


def resolved_service_account_email() -> Optional[str]:
    """Return service account client_email if credentials JSON exists, else None."""

    try:
        path = Path(_service_account_credentials_path())
        if not path.exists():
            return None
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj.get("client_email")
    except Exception:
        return None


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


def format_sheets_missing_env_message(email: Optional[str]) -> str:
    """Return a consistent warning about missing Sheets configuration."""

    share_target = email or resolved_service_account_email() or _DEFAULT_SERVICE_ACCOUNT_PLACEHOLDER
    return (
        "Sheets is not configured. Set SHEET_INVENTORY_ID in .env (File → Share with: "
        f"{share_target})."
    )


def sheets_share_hint(email: Optional[str]) -> str:
    """Return guidance for sharing the spreadsheet with the service account."""

    share_target = email or resolved_service_account_email() or _DEFAULT_SERVICE_ACCOUNT_PLACEHOLDER
    return (
        f"Share the sheet with {share_target} as Viewer. Set SHEET_INVENTORY_ID in .env."
    )


def format_drive_share_message(root_id: str, email: Optional[str]) -> str:
    """Return a consistent instruction to share a Drive root with the service account."""

    share_target = email or resolved_service_account_email() or _DEFAULT_SERVICE_ACCOUNT_PLACEHOLDER
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
