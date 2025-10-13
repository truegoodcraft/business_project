"""Thin Google Sheets REST client helpers used across the project."""

from __future__ import annotations

import logging
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple, Union
from urllib.parse import quote

from requests import Response, Session

from ..util.google_auth import google_session


logger = logging.getLogger(__name__)

SHEETS_ENDPOINT = "https://sheets.googleapis.com/v4/spreadsheets"

LimitsLike = Union[Mapping[str, Any], object, None]


class SheetsAPIError(RuntimeError):
    """Raised when the Google Sheets API returns an error payload."""


@dataclass
class SheetsRequestContext:
    """Configuration for issuing authorised Sheets API requests."""

    session: Session
    timeout: int = 30


_SESSION: Optional[Session] = None


def _shared_session(client: Optional[Session]) -> Session:
    if client is not None:
        return client
    global _SESSION
    if _SESSION is None:
        _SESSION = google_session()
    return _SESSION


def _limit_value(limits: LimitsLike, key: str) -> Optional[float]:
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
    return numeric


def _perform_get(
    url: str,
    *,
    params: Optional[MutableMapping[str, Any]] = None,
    context: SheetsRequestContext,
) -> Dict[str, Any]:
    try:
        response: Response = context.session.get(
            url,
            params=params,
            timeout=context.timeout,
        )
    except Exception as exc:  # pragma: no cover - network dependent
        raise SheetsAPIError(f"Sheets request failed: {exc}") from exc
    if response.status_code >= 400:
        detail = response.text.strip() or response.reason
        raise SheetsAPIError(f"Sheets API error {response.status_code}: {detail}")
    if not response.content:
        return {}
    try:
        return response.json()
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise SheetsAPIError(f"Invalid JSON from Sheets API: {exc}") from exc


def _ticker(enabled: bool) -> Tuple[callable[[], None], callable[[int, bool], None], callable[[], None]]:
    state = {"last": 0.0}

    def start() -> None:
        if not enabled:
            return
        state["last"] = time.perf_counter()
        sys.stdout.write("\rSheets rows read (0)")
        sys.stdout.flush()

    def tick(rows: int, force: bool = False) -> None:
        if not enabled:
            return
        now = time.perf_counter()
        if not force and (now - state.get("last", 0.0)) < 0.5:
            return
        state["last"] = now
        sys.stdout.write(f"\rSheets rows read ({rows})")
        sys.stdout.flush()

    def stop() -> None:
        if not enabled:
            return
        sys.stdout.write("\n")
        sys.stdout.flush()

    return start, tick, stop


def _normalise_sheet_entry(entry: Mapping[str, Any]) -> Dict[str, Any]:
    properties = entry.get("properties") if isinstance(entry.get("properties"), Mapping) else {}
    grid = properties.get("gridProperties") if isinstance(properties, Mapping) else {}
    if not isinstance(grid, Mapping):
        grid = {}
    return {
        "sheetId": properties.get("sheetId"),
        "title": properties.get("title"),
        "index": properties.get("index"),
        "rowCount": grid.get("rowCount"),
        "columnCount": grid.get("columnCount"),
    }


def get_spreadsheet_metadata(
    spreadsheet_id: str,
    *,
    credentials: Mapping[str, Any],
    timeout: int = 30,
    client: Optional[Session] = None,
) -> Dict[str, Any]:
    """Return the spreadsheet title and sheet list for ``spreadsheet_id``."""

    if not spreadsheet_id:
        raise ValueError("Spreadsheet ID is required")
    _ = credentials  # Legacy compatibility; session auth handled via google_session().
    context = SheetsRequestContext(
        session=_shared_session(client),
        timeout=timeout,
    )
    params = {
        "includeGridData": "false",
        "fields": "spreadsheetId,properties.title,sheets(properties(sheetId,title,index,gridProperties))",
    }
    payload = _perform_get(f"{SHEETS_ENDPOINT}/{spreadsheet_id}", params=params, context=context)
    spreadsheet_id = payload.get("spreadsheetId", spreadsheet_id)
    properties = payload.get("properties") if isinstance(payload.get("properties"), Mapping) else {}
    title = properties.get("title") if isinstance(properties, Mapping) else None
    sheets_payload = payload.get("sheets")
    sheets: List[Dict[str, Any]] = []
    if isinstance(sheets_payload, Sequence):
        for entry in sheets_payload:
            if isinstance(entry, Mapping):
                sheets.append(_normalise_sheet_entry(entry))
    return {
        "spreadsheetId": spreadsheet_id,
        "title": title,
        "sheets": sheets,
    }


def read_range(
    spreadsheet_id: str,
    range_a1: str,
    limits: LimitsLike = None,
    *,
    credentials: Mapping[str, Any],
    timeout: int = 30,
    client: Optional[Session] = None,
) -> Dict[str, Any]:
    """Read ``range_a1`` rows from ``spreadsheet_id`` using the Values API."""

    if not spreadsheet_id:
        raise ValueError("Spreadsheet ID is required")
    if not range_a1:
        raise ValueError("Range (A1 notation) is required")

    _ = credentials  # Legacy compatibility; session auth handled via google_session().
    context = SheetsRequestContext(
        session=_shared_session(client),
        timeout=timeout,
    )

    max_seconds = _limit_value(limits, "max_seconds")
    max_rows = _limit_value(limits, "max_rows")
    if max_rows is not None:
        max_rows = max(int(max_rows), 0)

    start_time = time.monotonic()

    ticker_start, ticker_tick, ticker_stop = _ticker(logger.isEnabledFor(logging.INFO))
    ticker_start()
    try:
        params: Dict[str, Any] = {
            "majorDimension": "ROWS",
            "valueRenderOption": "FORMATTED_VALUE",
        }
        encoded_range = quote(range_a1, safe="!:'(),$&=*-_.~")
        payload = _perform_get(
            f"{SHEETS_ENDPOINT}/{spreadsheet_id}/values/{encoded_range}",
            params=params,
            context=context,
        )
    except Exception:
        ticker_stop()
        raise

    values_raw = payload.get("values")
    values: List[List[str]] = []
    if isinstance(values_raw, Sequence):
        for row in values_raw:
            if isinstance(row, Sequence):
                str_row = ["" if cell is None else str(cell) for cell in row]
            else:  # pragma: no cover - defensive guard
                str_row = [str(row)]
            values.append(str_row)

    total_rows = len(values)
    truncated = False
    if max_rows is not None and total_rows > max_rows:
        values = values[: max_rows]
        truncated = True

    elapsed = time.monotonic() - start_time
    ticker_tick(len(values), force=True)
    ticker_stop()

    if max_seconds is not None and elapsed > max_seconds:
        truncated = True
        reason = "max_seconds"
    elif truncated:
        reason = "max_rows"
    else:
        reason = None

    result = {
        "range": payload.get("range", range_a1),
        "majorDimension": payload.get("majorDimension", "ROWS"),
        "values": values,
        "rows_returned": len(values),
        "total_rows": total_rows,
        "elapsed_seconds": elapsed,
    }
    if truncated:
        result["truncated"] = True
        if reason:
            result["reason"] = reason
    return result

