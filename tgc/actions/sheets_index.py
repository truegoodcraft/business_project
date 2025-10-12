"""Helpers for building a spreadsheet index sourced from Google Drive."""

from __future__ import annotations

import sys
import time
from collections import deque
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence

from ..adapters import drive_adapter, sheets_adapter

_SPREADSHEET_MIME = "application/vnd.google-apps.spreadsheet"
_FOLDER_MIME = "application/vnd.google-apps.folder"


def _config_get(config: object, *path: str) -> Any:
    """Return a nested value from ``config`` supporting dict/attribute access."""

    current: Any = config
    for key in path:
        if current is None:
            return None
        if isinstance(current, Mapping):
            if key in current:
                current = current[key]
            else:
                return None
        else:
            current = getattr(current, key, None)
    return current


def _sanitize_segment(text: str) -> str:
    cleaned = (text or "").strip()
    cleaned = cleaned.replace("/", "／").replace("|", "¦")
    return cleaned or "(untitled)"


def _limit_float(limits: object, key: str) -> Optional[float]:
    value: Any
    if limits is None:
        return None
    if isinstance(limits, Mapping):
        value = limits.get(key)
    else:
        value = getattr(limits, key, None)
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric < 0:
        return None
    return numeric


def _limit_int(limits: object, key: str) -> Optional[int]:
    numeric = _limit_float(limits, key)
    if numeric is None:
        return None
    return int(numeric)


class _Ticker:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled
        self.last = 0.0

    def start(self) -> None:
        if not self.enabled:
            return
        self.last = time.perf_counter()
        sys.stdout.write("\rSheets: files(0) • tabs(0) • requests(0)")
        sys.stdout.flush()

    def update(self, files: int, tabs: int, requests: int, *, force: bool = False) -> None:
        if not self.enabled:
            return
        now = time.perf_counter()
        if not force and (now - self.last) < 0.25:
            return
        self.last = now
        sys.stdout.write(
            f"\rSheets: files({files}) • tabs({tabs}) • requests({requests})"
        )
        sys.stdout.flush()

    def stop(self) -> None:
        if not self.enabled:
            return
        sys.stdout.write("\n")
        sys.stdout.flush()


def _drive_settings(config: object) -> MutableMapping[str, Any]:
    drive_settings = _config_get(config, "drive_config")
    if drive_settings is None:
        drive_settings = _config_get(config, "drive")
    settings: Dict[str, Any] = {}
    if isinstance(drive_settings, Mapping):
        settings.update({k: v for k, v in drive_settings.items() if v is not None})
    elif drive_settings is not None:
        for key in (
            "access_token",
            "token",
            "drive_id",
            "driveId",
            "timeout",
            "timeout_seconds",
            "fallback_root_id",
            "DRIVE_ROOT_FOLDER_ID",
        ):
            value = getattr(drive_settings, key, None)
            if value is not None:
                settings[key] = value

    for key in (
        "access_token",
        "token",
        "drive_id",
        "driveId",
        "timeout",
        "timeout_seconds",
        "fallback_root_id",
        "DRIVE_ROOT_FOLDER_ID",
    ):
        value = _config_get(config, key)
        if value is not None and key not in settings:
            settings[key] = value
    return settings


def _sheets_credentials(config: object) -> Mapping[str, Any]:
    credentials = _config_get(config, "sheets_credentials")
    if credentials is None:
        credentials = _config_get(config, "sheets", "credentials")
    if credentials is None:
        credentials = _config_get(config, "credentials")
    if credentials is None:
        credentials = _config_get(config, "drive", "credentials")
    if not isinstance(credentials, Mapping):
        raise ValueError("Sheets credentials are required to fetch spreadsheet metadata")
    return credentials


def _sheets_timeout(config: object) -> int:
    timeout_candidates: Iterable[Any] = (
        _config_get(config, "sheets_timeout"),
        _config_get(config, "sheets", "timeout"),
        _config_get(config, "sheets", "timeout_seconds"),
        _config_get(config, "drive", "timeout_seconds"),
    )
    for candidate in timeout_candidates:
        if candidate is None:
            continue
        try:
            return int(candidate)
        except (TypeError, ValueError):
            continue
    return 30


def _is_quiet(config: object) -> bool:
    for value in (
        _config_get(config, "quiet"),
        _config_get(config, "options", "quiet"),
    ):
        if value is None:
            continue
        return bool(value)
    return False


def build_sheets_index(
    limits: Optional[object],
    drive_root_id: str,
    config: object,
) -> List[Dict[str, Any]]:
    """Collect spreadsheet + sheet metadata for Drive ``drive_root_id``."""

    if not drive_root_id:
        raise ValueError("drive_root_id is required")

    drive_config = _drive_settings(config)
    credentials = _sheets_credentials(config)
    sheets_timeout = _sheets_timeout(config)

    max_seconds = _limit_float(limits, "max_seconds")
    max_items = _limit_int(limits, "max_items")
    max_requests = _limit_int(limits, "max_requests")

    quiet = _is_quiet(config)
    ticker = _Ticker(not quiet)

    start_time = time.perf_counter()

    def time_exceeded() -> bool:
        if max_seconds is None:
            return False
        return (time.perf_counter() - start_time) >= max_seconds

    if time_exceeded():
        return []

    rows: List[Dict[str, Any]] = []
    processed_spreadsheets: set[str] = set()
    folder_paths: Dict[str, List[str]] = {drive_root_id: []}
    queue: deque[str] = deque([drive_root_id])
    visited_folders: set[str] = set()

    files_count = 0
    tabs_count = 0
    requests_count = 0

    ticker.start()

    try:
        while queue:
            if time_exceeded():
                break
            if max_items is not None and files_count >= max_items:
                break
            folder_id = queue.popleft()
            if not folder_id or folder_id in visited_folders:
                continue
            visited_folders.add(folder_id)

            if max_requests is not None and requests_count >= max_requests:
                break

            call_limits: Dict[str, Any] = {}
            if max_seconds is not None:
                remaining = max_seconds - (time.perf_counter() - start_time)
                if remaining <= 0:
                    break
                call_limits["max_seconds"] = remaining
            if max_requests is not None:
                remaining_requests = max_requests - requests_count
                if remaining_requests <= 0:
                    break
                call_limits["max_requests"] = remaining_requests

            children = drive_adapter.list_drive_files(
                [folder_id],
                limits=call_limits or None,
                config=drive_config,
            )
            requests_count += 1
            ticker.update(files_count, tabs_count, requests_count, force=True)

            parent_segments = list(folder_paths.get(folder_id, []))

            for child in children:
                if time_exceeded():
                    queue.clear()
                    break
                child_id = child.get("id")
                if not child_id:
                    continue
                mime_type = child.get("mimeType")
                name = _sanitize_segment(str(child.get("name", "")))
                if mime_type == _FOLDER_MIME:
                    if child_id in visited_folders:
                        continue
                    folder_paths[child_id] = parent_segments + [name]
                    queue.append(child_id)
                    continue
                if mime_type != _SPREADSHEET_MIME:
                    continue
                if child_id in processed_spreadsheets:
                    continue
                if max_items is not None and files_count >= max_items:
                    queue.clear()
                    break
                if max_requests is not None and requests_count >= max_requests:
                    queue.clear()
                    break
                if time_exceeded():
                    queue.clear()
                    break

                metadata = sheets_adapter.get_spreadsheet_metadata(
                    child_id,
                    credentials=credentials,
                    timeout=sheets_timeout,
                )
                requests_count += 1
                files_count += 1
                processed_spreadsheets.add(child_id)

                spreadsheet_id = metadata.get("spreadsheetId", child_id)
                spreadsheet_title = metadata.get("title") or ""
                sheet_entries: Sequence[Mapping[str, Any]] = metadata.get("sheets") or []
                parent_path = "/" + "/".join(parent_segments) if parent_segments else "/"

                sheet_rows_added = 0
                if not sheet_entries:
                    rows.append(
                        {
                            "spreadsheetId": str(spreadsheet_id),
                            "spreadsheetTitle": spreadsheet_title,
                            "url": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
                            "sheetId": 0,
                            "sheetTitle": "",
                            "sheetIndex": 0,
                            "rows": 0,
                            "cols": 0,
                            "parentPath": parent_path,
                            "modifiedTime": child.get("modifiedTime", ""),
                        }
                    )
                else:
                    for sheet in sheet_entries:
                        sheet_id = sheet.get("sheetId")
                        sheet_index = sheet.get("index")
                        row_count = sheet.get("rowCount")
                        col_count = sheet.get("columnCount")
                        rows.append(
                            {
                                "spreadsheetId": str(spreadsheet_id),
                                "spreadsheetTitle": spreadsheet_title,
                                "url": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
                                "sheetId": int(sheet_id) if sheet_id is not None else 0,
                                "sheetTitle": sheet.get("title") or "",
                                "sheetIndex": int(sheet_index) if sheet_index is not None else 0,
                                "rows": int(row_count) if row_count is not None else 0,
                                "cols": int(col_count) if col_count is not None else 0,
                                "parentPath": parent_path,
                                "modifiedTime": child.get("modifiedTime", ""),
                            }
                        )
                        sheet_rows_added += 1

                tabs_count += sheet_rows_added
                ticker.update(files_count, tabs_count, requests_count, force=True)

                if max_items is not None and files_count >= max_items:
                    queue.clear()
                    break
                if max_requests is not None and requests_count >= max_requests:
                    queue.clear()
                    break
                if time_exceeded():
                    queue.clear()
                    break
    finally:
        ticker.stop()

    return rows
