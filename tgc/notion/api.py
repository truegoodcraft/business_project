# SPDX-License-Identifier: AGPL-3.0-or-later
"""Minimal Notion API client used by the controller."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Optional

from requests import HTTPError, RequestException, Response

from tgc.util.http import default_client as http


logger = logging.getLogger(__name__)


class NotionAPIError(Exception):
    """Exception raised when the Notion API responds with an error."""

    def __init__(self, status: int, code: Optional[str], message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message

    def to_dict(self) -> Dict[str, Any]:
        return {"status": self.status, "code": self.code, "message": self.message}


class NotionAPIClient:
    """Very small HTTP client covering the controller's needs."""

    API_BASE = "https://api.notion.com/v1"
    DEFAULT_VERSION = "2022-06-28"

    def __init__(
        self,
        token: str,
        *,
        timeout: int = 30,
        rate_limit_qps: float = 3.0,
        notion_version: str = DEFAULT_VERSION,
    ) -> None:
        if not token:
            raise ValueError("A Notion integration token is required.")
        self.token = token
        self.timeout = timeout
        self.notion_version = notion_version
        self._min_interval = 1.0 / rate_limit_qps if rate_limit_qps and rate_limit_qps > 0 else 0.0
        self._last_request = 0.0

    # ------------------------------------------------------------------
    # Public endpoints used by the module and adapter

    def users_me(self) -> Dict[str, Any]:
        return self._request("GET", "/users/me")

    def databases_retrieve(self, database_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/databases/{database_id}")

    def databases_query(
        self,
        database_id: str,
        *,
        page_size: Optional[int] = None,
        start_cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        if page_size is not None:
            payload["page_size"] = page_size
        if start_cursor is not None:
            payload["start_cursor"] = start_cursor
        return self._request("POST", f"/databases/{database_id}/query", body=payload)

    def pages_retrieve(self, page_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/pages/{page_id}")

    def pages_create(self, *, parent: Dict[str, Any], properties: Dict[str, Any]) -> Dict[str, Any]:
        body = {"parent": parent, "properties": properties}
        return self._request("POST", "/pages", body=body)

    def pages_update(self, page_id: str, *, properties: Dict[str, Any]) -> Dict[str, Any]:
        body = {"properties": properties}
        return self._request("PATCH", f"/pages/{page_id}", body=body)

    def blocks_children_list(
        self,
        block_id: str,
        *,
        page_size: Optional[int] = None,
        start_cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if page_size is not None:
            params["page_size"] = str(page_size)
        if start_cursor is not None:
            params["start_cursor"] = start_cursor
        return self._request("GET", f"/blocks/{block_id}/children", params=params)

    # ------------------------------------------------------------------
    # Internal helpers

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.API_BASE}{path}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": self.notion_version,
        }
        request_kwargs: Dict[str, Any] = {"headers": headers}
        if params:
            request_kwargs["params"] = {k: v for k, v in params.items() if v is not None}
        if body is not None:
            request_kwargs["json"] = body
        self._throttle()
        start = time.perf_counter()
        logger.debug("→ Notion %s %s", method, path)
        try:
            response = http.request(method, url, timeout=self.timeout, **request_kwargs)
            response.raise_for_status()
        except HTTPError as exc:  # pragma: no cover - network dependent
            elapsed_ms = (time.perf_counter() - start) * 1000
            error = self._convert_http_error(exc.response)
            logger.debug(
                "← Notion %s %s failed [%s] in %.0f ms: %s",
                method,
                path,
                error.status,
                elapsed_ms,
                error.message,
            )
            self._last_request = time.monotonic()
            raise error
        except RequestException as exc:  # pragma: no cover - network dependent
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.debug(
                "← Notion %s %s failed [network] in %.0f ms: %s",
                method,
                path,
                elapsed_ms,
                exc,
            )
            self._last_request = time.monotonic()
            raise NotionAPIError(status=0, code="network_error", message=str(exc)) from None
        else:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.debug(
                "← Notion %s %s succeeded [%s] in %.0f ms",
                method,
                path,
                response.status_code,
                elapsed_ms,
            )
            self._last_request = time.monotonic()
            if not response.content:
                return {}
            try:
                return response.json()
            except ValueError:
                return {"raw": response.text}

    def _convert_http_error(self, response: Optional[Response]) -> NotionAPIError:
        status = response.status_code if response is not None else 0
        reason = response.reason if response is not None else None
        message = reason or "HTTP error"
        code: Optional[str] = None
        body = None
        if response is not None:
            try:
                body = response.json()
            except ValueError:
                body = None
        if isinstance(body, dict):
            code = body.get("code") or code
            message = body.get("message") or message
        elif response is not None and not body:
            text = response.text
            if text:
                message = text
        return NotionAPIError(status=status, code=code, message=message)

    def _throttle(self) -> None:
        if self._min_interval <= 0:
            return
        now = time.monotonic()
        elapsed = now - self._last_request
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
