"""System health checks for external integrations and configuration."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from .config import AppConfig
from .notion.api import NotionAPIClient, NotionAPIError
from .integration_support import (
    format_drive_share_message,
    format_sheets_missing_env_message,
    is_drive_permission_error,
    load_drive_module_config,
    service_account_email,
)
from .modules.google_drive import DriveModuleConfig, ServiceAccountCredentials, build

SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"
DRIVE_FIELDS = (
    "id, name, mimeType, driveId, capabilities(canListChildren, canEdit), "
    "shortcutDetails(targetId, targetMimeType), permissions(emailAddress, role)"
)


def system_health() -> Tuple[List[Dict[str, str]], bool]:
    """Run system health checks and return detailed results."""

    config = AppConfig.load()
    drive_config_path = config.drive.module_config_path.expanduser()
    drive_module_config = load_drive_module_config(drive_config_path)

    checks: List[Dict[str, str]] = []
    results: List[Tuple[str, str, str]] = []

    env_result = _check_environment(config, drive_config_path)
    results.append(env_result)

    notion_result = _check_notion(config)
    results.append(notion_result)

    drive_result = _check_drive(config, drive_module_config)
    results.append(drive_result)

    sheets_result = _check_sheets(config, drive_module_config)
    if sheets_result is not None:
        results.append(sheets_result)

    overall_ok = True
    for name, status, detail in results:
        checks.append({"name": name, "status": status, "details": detail})
        if status != "ready":
            overall_ok = False

    return checks, overall_ok


def format_health_table(
    checks: Iterable[Dict[str, str]], *, include_environment: bool = False
) -> str:
    """Return a compact, single-line summary for CLI output."""

    entries: List[str] = []
    for check in checks:
        name = check.get("name", "")
        if not include_environment and name == "Environment":
            continue
        label = _display_label(name)
        status = check.get("status", "unknown").upper()
        detail = check.get("details", "")
        info = _compact_detail(detail, status)
        entry_parts = [f"{label} {status}"]
        if info:
            entry_parts.append(info)
        entries.append(" ".join(entry_parts).strip())
    return " ".join(entries)


def format_health_banner(checks: Iterable[Dict[str, str]]) -> str:
    """Return a banner string describing key connector readiness."""

    parts: List[str] = []
    for check in checks:
        label = _banner_label(check.get("name", ""))
        if not label:
            continue
        status = check.get("status", "unknown").upper()
        parts.append(f"[{label}:{status}]")
    if not parts:
        return ""
    return "Status: " + " ".join(parts)


def _check_environment(config: AppConfig, drive_config_path: Path) -> Tuple[str, str, str]:
    start = time.perf_counter()
    env_path = Path(".env")
    keys = [
        "NOTION_TOKEN",
        "NOTION_DB_INVENTORY_ID",
        "DRIVE_ROOT_FOLDER_ID",
        "SHEET_INVENTORY_ID",
    ]
    present = [key for key in keys if os.getenv(key)]
    missing = [key for key in keys if key not in present]

    env_source: List[str] = []
    if env_path.exists():
        env_source.append(f".env present at {env_path.resolve()}")
    else:
        env_source.append(".env file not found; relying on process environment")
    if drive_config_path.exists():
        env_source.append(f"Drive module config at {drive_config_path}")

    message = ", ".join(env_source)
    detail_parts = [message]
    detail_parts.append(f"Present: {', '.join(present) if present else 'none'}")
    detail_parts.append(f"Missing: {', '.join(missing) if missing else 'none'}")
    fix: Optional[str] = None
    status = "ready"
    if missing:
        status = "missing"
        fix = "Add the missing keys to .env or export them before running the app."
    detail = _format_detail("; ".join(detail_parts), start, fix)
    return "Environment", status, detail


def _check_notion(config: AppConfig) -> Tuple[str, str, str]:
    start = time.perf_counter()
    notion_config = config.notion
    if not notion_config.token:
        detail = _format_detail(
            "Notion token is not configured.",
            start,
            "Set NOTION_TOKEN or NOTION_API_KEY in the environment.",
        )
        return "Notion", "missing", detail
    database_id = notion_config.inventory_database_id
    if not database_id:
        detail = _format_detail(
            "Notion inventory database ID is missing.",
            start,
            "Set NOTION_DB_INVENTORY_ID to the target database identifier.",
        )
        return "Notion", "missing", detail
    try:
        client = NotionAPIClient(
            notion_config.token,
            timeout=notion_config.timeout_seconds,
            rate_limit_qps=notion_config.rate_limit_qps,
        )
    except Exception as exc:  # pragma: no cover - defensive guard
        detail = _format_detail(
            f"Unable to initialise Notion client: {exc}",
            start,
            "Verify the integration token and retry.",
        )
        return "Notion", "error", detail
    try:
        database = client.databases_retrieve(database_id)
    except NotionAPIError as exc:  # pragma: no cover - network dependent
        detail = _format_detail(
            f"Notion API error: {exc.message}",
            start,
            "Confirm the database ID and that the integration has access.",
        )
        return "Notion", "error", detail
    title = _join_rich_text(database.get("title", [])) or "(untitled)"
    properties = database.get("properties", {})
    property_count = len(properties) if isinstance(properties, dict) else 0
    detail = _format_detail(
        f"Retrieved Notion database '{title}' ({database_id}) with {property_count} properties.",
        start,
    )
    return "Notion", "ready", detail


def _check_drive(config: AppConfig, module_config: DriveModuleConfig) -> Tuple[str, str, str]:
    start = time.perf_counter()
    root_id = config.drive.fallback_root_id or (module_config.root_ids[0] if module_config.root_ids else None)
    if not root_id:
        detail = _format_detail(
            "DRIVE_ROOT_FOLDER_ID is not configured.",
            start,
            "Set DRIVE_ROOT_FOLDER_ID or configure a Drive module root.",
        )
        return "Google Drive", "missing", detail
    if ServiceAccountCredentials is None or build is None:
        detail = _format_detail(
            "Google API client libraries are not installed.",
            start,
            "Install google-api-python-client and google-auth to enable Drive checks.",
        )
        return "Google Drive", "missing", detail
    if not module_config.enabled:
        detail = _format_detail(
            "Drive module is disabled in configuration.",
            start,
            "Enable the Drive module and store service account credentials.",
        )
        return "Google Drive", "missing", detail
    if not module_config.has_credentials():
        detail = _format_detail(
            "Drive service account credentials are missing.",
            start,
            "Import a service account JSON via the Drive module setup.",
        )
        return "Google Drive", "missing", detail
    try:
        credentials = ServiceAccountCredentials.from_service_account_info(
            module_config.credentials,
            scopes=module_config.scopes(),
        )
        drive_service = build("drive", "v3", credentials=credentials, cache_discovery=False)
    except Exception as exc:  # pragma: no cover - dependency guard
        detail = _format_detail(
            f"Unable to initialise Drive client: {exc}",
            start,
            "Validate stored credentials or re-run Drive module configuration.",
        )
        return "Google Drive", "error", detail
    try:
        metadata, shortcut_chain = _validate_drive_root(drive_service, root_id)
    except Exception as exc:  # pragma: no cover - network dependent
        if is_drive_permission_error(exc):
            fix = format_drive_share_message(root_id, service_account_email(module_config))
        else:
            fix = "Confirm the folder exists and is shared with the service account."
        detail = _format_detail(
            f"Drive validation failed for {root_id}: {exc}",
            start,
            fix,
        )
        return "Google Drive", "error", detail
    name = metadata.get("name") or "(untitled)"
    drive_id = metadata.get("driveId")
    capability = metadata.get("capabilities", {})
    can_list = capability.get("canListChildren", False)
    can_edit = capability.get("canEdit", False)
    detail_parts = [f"Drive root '{name}' ({metadata.get('id', root_id)})"]
    if drive_id:
        detail_parts.append(f"driveId={drive_id}")
    if shortcut_chain:
        detail_parts.append(f"resolved via shortcut: {' → '.join(shortcut_chain)}")
    detail_parts.append(f"list_access={'yes' if can_list else 'no'}")
    detail_parts.append(f"edit_access={'yes' if can_edit else 'no'}")
    status = "ready" if can_list else "error"
    fix: Optional[str] = None
    if status != "ready":
        fix = "Grant the service account at least viewer access to the Drive folder."
    detail = _format_detail("; ".join(detail_parts), start, fix)
    return "Google Drive", status, detail


def _check_sheets(
    config: AppConfig, module_config: DriveModuleConfig
) -> Optional[Tuple[str, str, str]]:
    sheet_id = config.sheets.inventory_sheet_id
    if not sheet_id:
        start = time.perf_counter()
        message = format_sheets_missing_env_message(service_account_email(module_config))
        detail = _format_detail(message, start)
        return "Google Sheets", "missing", detail
    start = time.perf_counter()
    if ServiceAccountCredentials is None or build is None:
        detail = _format_detail(
            "Google API client libraries are not installed.",
            start,
            "Install google-api-python-client and google-auth to reach Sheets.",
        )
        return "Google Sheets", "missing", detail
    if not module_config.has_credentials():
        detail = _format_detail(
            "Drive service account credentials missing; cannot reach Sheets.",
            start,
            "Import a service account JSON via the Drive module setup.",
        )
        return "Google Sheets", "missing", detail
    try:
        credentials = ServiceAccountCredentials.from_service_account_info(
            module_config.credentials,
            scopes=[SHEETS_SCOPE],
        )
        sheets_service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
        response = (
            sheets_service.spreadsheets()
            .get(spreadsheetId=sheet_id, fields="spreadsheetId,properties(title)")
            .execute()
        )
    except Exception as exc:  # pragma: no cover - network dependent
        detail = _format_detail(
            f"Sheets API error: {exc}",
            start,
            "Confirm the sheet ID and share it with the service account.",
        )
        return "Google Sheets", "error", detail
    properties = response.get("properties", {}) if isinstance(response, dict) else {}
    title = properties.get("title") or "(untitled)"
    detail = _format_detail(
        f"Spreadsheet '{title}' ({response.get('spreadsheetId', sheet_id)}) reachable.",
        start,
    )
    return "Google Sheets", "ready", detail

def _validate_drive_root(service: object, root_id: str) -> Tuple[Dict[str, object], List[str]]:
    shortcuts: List[str] = []
    current_id = root_id
    visited: set[str] = set()
    while True:
        request = service.files().get(
            fileId=current_id,
            fields=DRIVE_FIELDS,
            supportsAllDrives=True,
        )
        metadata = request.execute()
        if not isinstance(metadata, dict):
            raise RuntimeError("Unexpected Drive API response")
        mime_type = metadata.get("mimeType")
        if mime_type != "application/vnd.google-apps.shortcut":
            return metadata, shortcuts
        shortcut = metadata.get("shortcutDetails", {})
        target_id = shortcut.get("targetId") if isinstance(shortcut, dict) else None
        if not target_id:
            raise RuntimeError("Shortcut is missing target information")
        if target_id in visited:
            raise RuntimeError("Detected shortcut cycle while resolving Drive root")
        visited.add(target_id)
        shortcuts.append(f"{metadata.get('id')}→{target_id}")
        current_id = target_id


def _join_rich_text(blocks: object) -> str:
    if not isinstance(blocks, list):
        return ""
    parts: List[str] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        text = block.get("plain_text") or block.get("plainText")
        if text:
            parts.append(str(text))
    return "".join(parts)


def _format_detail(message: str, start: float, fix: Optional[str] = None) -> str:
    elapsed_ms = (time.perf_counter() - start) * 1000
    parts = [message]
    if fix:
        parts.append(f"Fix: {fix}")
    parts.append(f"elapsed {elapsed_ms:.0f} ms")
    return "; ".join(parts)


def _display_label(name: str) -> str:
    mapping = {
        "Notion": "NOTION",
        "Google Drive": "DRIVE",
        "Google Sheets": "SHEETS",
        "Environment": "ENV",
    }
    return mapping.get(name, name.upper())


def _banner_label(name: str) -> str:
    mapping = {
        "Notion": "NOTION",
        "Google Drive": "DRIVE",
        "Google Sheets": "SHEETS",
    }
    return mapping.get(name, "")


def _compact_detail(detail: str, status: str) -> str:
    if not detail:
        return ""
    segments = [segment.strip() for segment in detail.split(";") if segment.strip()]
    summary: Optional[str] = None
    fix: Optional[str] = None
    elapsed: Optional[str] = None
    for segment in segments:
        lowered = segment.lower()
        if lowered.startswith("fix:"):
            fix = segment.split(":", 1)[1].strip() if ":" in segment else segment[4:].strip()
            continue
        if lowered.startswith("elapsed"):
            elapsed = segment.split(" ", 1)[1].strip() if " " in segment else segment
            continue
        if summary is None:
            summary = segment
    detail_text = fix if status != "READY" and fix else summary
    parts: List[str] = []
    if detail_text:
        parts.append(f"({detail_text})")
    if elapsed:
        parts.append(elapsed)
    return " ".join(parts).strip()

