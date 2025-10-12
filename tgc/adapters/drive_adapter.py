"""Helpers for listing Google Drive files via the REST API."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Union

from requests import Response

from tgc.util.http import default_client

logger = logging.getLogger(__name__)

_DRIVE_FILES_ENDPOINT = "https://www.googleapis.com/drive/v3/files"
_LIST_FIELDS = (
    "nextPageToken, files(id, name, mimeType, size, md5Checksum, modifiedTime, parents, "
    "shortcutDetails, driveId)"
)
_GET_FIELDS = "id, name, mimeType, size, modifiedTime, parents, driveId"
_SHORTCUT_MIME = "application/vnd.google-apps.shortcut"


ConfigLike = Union[Mapping[str, Any], object, None]
LimitsLike = Union[Mapping[str, Any], object, None]


class _StopTraversal(Exception):
    """Internal sentinel exception used to break out of nested loops."""


def _config_value(config: ConfigLike, key: str, default: Any = None) -> Any:
    if config is None:
        return default
    if isinstance(config, Mapping):
        return config.get(key, default)
    return getattr(config, key, default)


def _limit_value(limits: LimitsLike, key: str) -> Any:
    if limits is None:
        return None
    if isinstance(limits, Mapping):
        return limits.get(key)
    return getattr(limits, key, None)


def list_drive_files(
    root_ids: Iterable[str],
    limits: LimitsLike = None,
    config: ConfigLike = None,
) -> List[Dict[str, Any]]:
    """List files for the provided Drive roots using the REST API."""

    access_token = _config_value(config, "access_token") or _config_value(config, "token")
    if not access_token:
        raise ValueError("Google Drive access token is required")

    drive_id = _config_value(config, "drive_id") or _config_value(config, "driveId")
    timeout = _config_value(config, "timeout") or _config_value(config, "timeout_seconds") or 30
    fallback_root = _config_value(config, "fallback_root_id") or _config_value(
        config, "DRIVE_ROOT_FOLDER_ID"
    )

    roots: List[Optional[str]] = [value for value in root_ids if value]
    if not roots:
        if fallback_root:
            roots = [str(fallback_root)]
        else:
            roots = [None]

    headers = {"Authorization": f"Bearer {access_token}"}
    max_seconds = _limit_value(limits, "max_seconds")
    max_requests = _limit_value(limits, "max_requests")
    max_items = _limit_value(limits, "max_items")

    start_time = time.monotonic()
    stats: Dict[str, int] = {"files": 0, "requests": 0}

    def _check_time() -> None:
        if max_seconds is not None and (time.monotonic() - start_time) >= float(max_seconds):
            raise _StopTraversal

    def _check_requests_before() -> None:
        if max_requests is not None and stats["requests"] >= int(max_requests):
            raise _StopTraversal

    def _check_requests_after() -> None:
        if max_requests is not None and stats["requests"] >= int(max_requests):
            raise _StopTraversal

    def _check_items() -> None:
        if max_items is not None and stats["files"] >= int(max_items):
            raise _StopTraversal

    def _perform_request(url: str, params: MutableMapping[str, Any]) -> Dict[str, Any]:
        _check_time()
        _check_requests_before()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("drive.request", extra={"url": url, "params": dict(params)})
        response: Response = default_client.get(url, headers=headers, params=params, timeout=timeout)
        stats["requests"] += 1
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "drive.response",
                extra={"url": url, "status": response.status_code, "remaining": max_requests},
            )
        response.raise_for_status()
        _check_time()
        _check_requests_after()
        return response.json() if response.content else {}

    def _normalise_item(raw: Mapping[str, Any], *, name_override: Optional[str] = None, shortcut: bool = False) -> Dict[str, Any]:
        result = {
            "id": raw.get("id"),
            "name": name_override if name_override is not None else raw.get("name"),
            "mimeType": raw.get("mimeType"),
            "size": raw.get("size"),
            "modifiedTime": raw.get("modifiedTime"),
            "parents": list(raw.get("parents", []) or []),
            "isShortcut": shortcut,
            "driveId": raw.get("driveId"),
        }
        return result

    def _resolve_shortcut(original: Mapping[str, Any]) -> Dict[str, Any]:
        shortcut_details = original.get("shortcutDetails")
        target_id = None
        if isinstance(shortcut_details, Mapping):
            target_id = shortcut_details.get("targetId")
        if not target_id:
            return _normalise_item(original, shortcut=True)
        _check_time()
        _check_requests_before()
        params: Dict[str, Any] = {
            "supportsAllDrives": "true",
            "fields": _GET_FIELDS,
        }
        if drive_id:
            params["driveId"] = drive_id
        url = f"{_DRIVE_FILES_ENDPOINT}/{target_id}"
        try:
            payload = _perform_request(url, params)
        except _StopTraversal:
            raise
        except Exception:
            payload = {}
        if not payload:
            payload = {"id": target_id}
        name_override = original.get("name")
        result = _normalise_item(payload, name_override=name_override, shortcut=True)
        if not result.get("id"):
            result["id"] = target_id
        return result

    corpora = "drive" if drive_id else "allDrives"
    results: List[Dict[str, Any]] = []

    try:
        for root in roots:
            page_token: Optional[str] = None
            seen_tokens: set[str] = set()
            while True:
                _check_items()
                query = "trashed = false"
                if root:
                    query = f"trashed = false and '{root}' in parents"
                params: Dict[str, Any] = {
                    "supportsAllDrives": "true",
                    "includeItemsFromAllDrives": "true",
                    "corpora": corpora,
                    "pageSize": 1000,
                    "fields": _LIST_FIELDS,
                    "q": query,
                }
                if drive_id:
                    params["driveId"] = drive_id
                if page_token:
                    params["pageToken"] = page_token
                payload = _perform_request(_DRIVE_FILES_ENDPOINT, params)
                files: Iterable[Mapping[str, Any]] = payload.get("files", [])  # type: ignore[assignment]
                for item in files:
                    _check_items()
                    if item.get("mimeType") == _SHORTCUT_MIME:
                        record = _resolve_shortcut(item)
                    else:
                        record = _normalise_item(item)
                    results.append(record)
                    stats["files"] += 1
                    _check_items()
                page_token = payload.get("nextPageToken")
                if not page_token:
                    break
                if page_token in seen_tokens:
                    break
                seen_tokens.add(page_token)
    except _StopTraversal:
        pass

    return results
