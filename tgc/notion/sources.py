"""Helpers for synchronising the Notion data sources registry."""

from __future__ import annotations

from datetime import UTC, datetime
import logging
import os
import time
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

from .api import NotionAPIClient, NotionAPIError

logger = logging.getLogger(__name__)

_THROTTLE_SECONDS = 0.25


def sync_data_sources_registry(
    sources_db_id: str,
    drive_rows: Optional[Iterable[Mapping[str, Any]]],
    sheets_rows: Optional[Iterable[Mapping[str, Any]]],
    notion_rows: Optional[Iterable[Mapping[str, Any]]],
) -> Dict[str, int]:
    """Synchronise the Sources registry in Notion.

    Parameters
    ----------
    sources_db_id:
        Target Notion database identifier.
    drive_rows / sheets_rows / notion_rows:
        Iterable collections describing the Drive, Sheets, and Notion assets
        discovered by the master index traversal.

    Returns
    -------
    Dict[str, int]
        A mapping containing ``created``, ``updated``, and ``skipped`` counts.
    """

    if not sources_db_id:
        raise ValueError("sources_db_id is required")

    client = _build_client()

    records: Dict[str, Dict[str, Any]] = {}
    skipped = 0

    for entry in _drive_entries(drive_rows or []):
        if not entry["key"] or not entry["name"]:
            skipped += 1
            continue
        records.setdefault(entry["key"], entry)

    for entry in _sheets_entries(sheets_rows or []):
        if not entry["key"] or not entry["name"]:
            skipped += 1
            continue
        records.setdefault(entry["key"], entry)

    for entry in _notion_entries(notion_rows or []):
        if not entry["key"] or not entry["name"]:
            skipped += 1
            continue
        records.setdefault(entry["key"], entry)

    if not records:
        return {"created": 0, "updated": 0, "skipped": skipped}

    existing = _load_existing_sources(client, sources_db_id)

    created = 0
    updated = 0
    timestamp = _current_timestamp()

    for key, entry in records.items():
        payload = _build_properties(entry, status="Ready", timestamp=timestamp)
        existing_page = existing.get(key)
        note: Optional[str] = None
        try:
            if existing_page is None:
                logger.debug("Creating sources registry entry for key=%s", key)
                _throttle()
                client.pages_create(parent={"database_id": sources_db_id}, properties=payload)
                created += 1
            else:
                page_id = existing_page.get("id")
                if not page_id:
                    raise ValueError(f"Existing page for key {key} missing id")
                logger.debug("Updating sources registry entry for key=%s", key)
                _throttle()
                client.pages_update(page_id, properties=payload)
                updated += 1
        except Exception as exc:  # pragma: no cover - defensive fallback
            note = _trim_note(str(exc))
            logger.error("Failed to upsert sources entry %s: %s", key, exc)
            if existing_page and existing_page.get("id"):
                error_payload = _build_properties(entry, status="Error", timestamp=timestamp, note=note)
                try:
                    _throttle()
                    client.pages_update(existing_page["id"], properties=error_payload)
                    updated += 1
                except Exception as update_exc:  # pragma: no cover - defensive fallback
                    logger.error(
                        "Unable to flag sources entry %s as error: %s", key, update_exc
                    )
                    skipped += 1
            else:
                skipped += 1

    return {"created": created, "updated": updated, "skipped": skipped}


def _build_client() -> NotionAPIClient:
    token, rate_limit, timeout = _resolve_client_settings()
    if not token:
        raise RuntimeError("Notion token is required to sync the sources registry")
    kwargs: Dict[str, Any] = {}
    if timeout is not None:
        kwargs["timeout"] = timeout
    if rate_limit is not None:
        kwargs["rate_limit_qps"] = rate_limit
    return NotionAPIClient(token, **kwargs)


def _resolve_client_settings() -> Tuple[str, Optional[float], Optional[int]]:
    token = os.getenv("NOTION_TOKEN") or os.getenv("NOTION_API_KEY") or ""
    rate_limit: Optional[float] = None
    timeout: Optional[int] = None

    def _float_env(key: str) -> Optional[float]:
        value = os.getenv(key)
        if value is None:
            return None
        try:
            return float(value)
        except ValueError:
            return None

    def _int_env(key: str) -> Optional[int]:
        value = os.getenv(key)
        if value is None:
            return None
        try:
            return int(float(value))
        except ValueError:
            return None

    rate_limit = _float_env("NOTION_RATE_LIMIT_QPS")
    timeout = _int_env("NOTION_TIMEOUT_SECONDS")

    if token:
        return token, rate_limit, timeout

    try:
        from tgc.config import AppConfig

        config = AppConfig.load()
    except Exception:  # pragma: no cover - defensive fallback when config load fails
        return token, rate_limit, timeout

    notion_config = getattr(config, "notion", None)
    if notion_config is not None:
        token = getattr(notion_config, "token", token) or token
        rate_limit = rate_limit if rate_limit is not None else getattr(notion_config, "rate_limit_qps", None)
        timeout = timeout if timeout is not None else getattr(notion_config, "timeout_seconds", None)
    return token, rate_limit, timeout


def _load_existing_sources(client: NotionAPIClient, database_id: str) -> Dict[str, Dict[str, Any]]:
    pages: Dict[str, Dict[str, Any]] = {}
    start_cursor: Optional[str] = None
    seen: set[str] = set()
    while True:
        try:
            _throttle()
            response = client.databases_query(
                database_id,
                page_size=100,
                start_cursor=start_cursor,
            )
        except NotionAPIError as exc:
            logger.error("Failed to query sources registry %s: %s", database_id, exc.message)
            break
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.error("Unexpected error querying sources registry %s: %s", database_id, exc)
            break
        results = response.get("results", []) if isinstance(response, Mapping) else []
        for page in results:
            if not isinstance(page, Mapping):
                continue
            key_property = _get_property(page.get("properties"), "Key")
            key = _extract_plain_text(key_property)
            if key:
                pages[str(key)] = dict(page)
        next_cursor = response.get("next_cursor") if isinstance(response, Mapping) else None
        has_more = bool(response.get("has_more")) if isinstance(response, Mapping) else False
        if not has_more or not next_cursor or next_cursor in seen:
            break
        seen.add(next_cursor)
        start_cursor = next_cursor
    return pages


def _drive_entries(rows: Iterable[Mapping[str, Any]]) -> Iterable[Dict[str, Any]]:
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        file_id = _stringify(
            row.get("file_id")
            or row.get("fileId")
            or row.get("id")
            or row.get("Id")
        )
        name = _stringify(row.get("name") or row.get("Name") or row.get("title"))
        if not file_id:
            yield {"key": "", "name": ""}
            continue
        url = _stringify(
            row.get("url")
            or row.get("webViewLink")
            or row.get("link")
        )
        if not url:
            url = f"https://drive.google.com/file/d/{file_id}/view"
        parent_path = _stringify(
            row.get("parentPath")
            or row.get("parent_path")
            or row.get("path")
            or row.get("Path")
        )
        if not parent_path:
            candidate = _stringify(row.get("path_or_link") or row.get("pathOrLink"))
            if candidate:
                candidate = candidate.split("→", 1)[0].strip()
                segments = [segment for segment in candidate.split("/") if segment]
                if len(segments) > 1:
                    parent_path = "/" + "/".join(segments[:-1])
                else:
                    parent_path = "/"
        parent_path = parent_path or "/"
        title = name or file_id
        yield {
            "type": "Drive",
            "key": f"drive:{file_id}",
            "name": title,
            "title": title,
            "url": url,
            "path": parent_path,
        }


def _sheets_entries(rows: Iterable[Mapping[str, Any]]) -> Iterable[Dict[str, Any]]:
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        spreadsheet_id = _stringify(row.get("spreadsheetId") or row.get("spreadsheet_id"))
        sheet_id_value = row.get("sheetId") or row.get("sheet_id") or 0
        sheet_id = _stringify(sheet_id_value)
        spreadsheet_title = _stringify(row.get("spreadsheetTitle") or row.get("title"))
        sheet_title = _stringify(row.get("sheetTitle") or row.get("name"))
        if not spreadsheet_id:
            yield {"key": "", "name": ""}
            continue
        url = _stringify(row.get("url"))
        if not url:
            gid = sheet_id or "0"
            url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid={gid}"
        parent_path = _stringify(row.get("parentPath") or row.get("parent_path")) or "/"
        display = spreadsheet_title
        if sheet_title:
            display = f"{spreadsheet_title} / {sheet_title}" if spreadsheet_title else sheet_title
        key = f"sheets:{spreadsheet_id}#{sheet_id or '0'}"
        yield {
            "type": "Sheets",
            "key": key,
            "name": display or key,
            "title": display or key,
            "url": url,
            "path": parent_path,
        }


def _notion_entries(rows: Iterable[Mapping[str, Any]]) -> Iterable[Dict[str, Any]]:
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        page_id = _stringify(row.get("page_id") or row.get("id"))
        title = _stringify(row.get("title") or row.get("Name"))
        if not page_id:
            yield {"key": "", "name": ""}
            continue
        url = _stringify(row.get("url"))
        parent = _stringify(row.get("parent") or row.get("Parent")) or "/"
        yield {
            "type": "Notion",
            "key": f"notion:{page_id}",
            "name": title or page_id,
            "title": title or page_id,
            "url": url,
            "path": parent,
        }


def _build_properties(
    entry: Mapping[str, Any],
    *,
    status: str,
    timestamp: str,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    name = _stringify(entry.get("name")) or entry.get("key") or "Untitled"
    title = _stringify(entry.get("title")) or name
    url = _stringify(entry.get("url"))
    path = _stringify(entry.get("path"))
    key = _stringify(entry.get("key"))
    extra = note or ""
    return {
        "Name": {"title": _rich_text_parts(name)},
        "Type": {"select": {"name": _stringify(entry.get("type")) or "Unknown"}},
        "Key": {"rich_text": _rich_text_parts(key)},
        "Title": {"rich_text": _rich_text_parts(title)},
        "URL": {"url": url or None},
        "Path": {"rich_text": _rich_text_parts(path)},
        "Status": {"status": {"name": status}},
        "Last Indexed": {"date": {"start": timestamp}},
        "Extra": {"rich_text": _rich_text_parts(extra)},
    }


def _rich_text_parts(value: str) -> list[Dict[str, Any]]:
    text = value.strip() if isinstance(value, str) else ""
    if not text:
        return []
    return [{"type": "text", "text": {"content": text}}]


def _current_timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _get_property(properties: Any, name: str) -> Any:
    if isinstance(properties, Mapping):
        return properties.get(name)
    return None


def _extract_plain_text(property_value: Any) -> str:
    if isinstance(property_value, Mapping):
        if "plain_text" in property_value:
            return _stringify(property_value.get("plain_text"))
        if "rich_text" in property_value:
            return "".join(
                _stringify(part.get("plain_text")) for part in property_value.get("rich_text", []) if isinstance(part, Mapping)
            )
        if "title" in property_value:
            return "".join(
                _stringify(part.get("plain_text")) for part in property_value.get("title", []) if isinstance(part, Mapping)
            )
        if "url" in property_value:
            return _stringify(property_value.get("url"))
    if isinstance(property_value, list):
        return "".join(
            _stringify(part.get("plain_text")) if isinstance(part, Mapping) else _stringify(part)
            for part in property_value
        )
    return _stringify(property_value)


def _trim_note(note: str, *, limit: int = 180) -> str:
    cleaned = note.strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def _throttle() -> None:
    time.sleep(_THROTTLE_SECONDS)
