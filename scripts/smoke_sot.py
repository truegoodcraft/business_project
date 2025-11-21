#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Deprecated — use buscore-smoke.ps1
"""SoT-aligned smoke tests for BUS Core licensing and baseline CRUD."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from core.config.paths import DB_PATH

BASE_URL = os.environ.get("BUSCORE_BASE_URL", "http://127.0.0.1:8765")


def _fmt_bool(value: bool) -> str:
    return "T" if value else "F"


def _req(
    method: str,
    url: str,
    token: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 10,
):
    h = {"Accept": "application/json"}
    if headers:
        h.update(headers)
    if token:
        h["X-Session-Token"] = token
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.getcode(), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except urllib.error.URLError as e:
        return 0, str(e).encode("utf-8")


def _snip(b: Optional[bytes]) -> str:
    try:
        return (b or b"")[:200].decode("utf-8", "replace")
    except Exception:
        return repr(b)[:200]


def _request(
    method: str,
    path: str,
    *,
    token: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    status, body = _req(method, f"{BASE_URL}{path}", token=token, data=payload)
    parsed: Optional[Any]
    try:
        parsed = json.loads(body.decode("utf-8"))
    except Exception:
        parsed = None
    return {"status": status, "body": body, "json": parsed}


def _expect_token() -> str:
    status, body = _req("GET", f"{BASE_URL}/session/token")
    if status != 200:
        raise SystemExit(
            f"Failed to fetch session token: status {status}, body={_snip(body)}"
        )
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        payload = None
    if isinstance(payload, dict) and "token" in payload:
        token_value = payload.get("token")
        return "" if token_value is None else str(token_value)
    raise SystemExit("Session token missing from /session/token response")


def _ensure_writes(token: str) -> None:
    _request("POST", "/dev/writes", token=token, payload={"enabled": True})


def _sync_launcher_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def main() -> None:
    token = _expect_token()
    _ensure_writes(token)

    health_public = _request("GET", "/health")
    health_public_json = health_public.get("json")
    public_ok = bool(
        health_public.get("status") == 200
        and isinstance(health_public_json, dict)
        and health_public_json.get("ok") is True
    )

    health_protected = _request("GET", "/health", token=token)
    hp_json = health_protected.get("json")
    hp_keys = [
        isinstance(hp_json, dict) and "version" in hp_json,
        isinstance(hp_json, dict) and "policy" in hp_json,
        isinstance(hp_json, dict) and "license" in hp_json,
        isinstance(hp_json, dict) and "run-id" in hp_json,
    ]

    ui_shell = _request("GET", "/ui/shell.html")
    ui_non_empty = bool(ui_shell.get("body"))

    vendor_name = f"SmokeVendor-{int(time.time())}"
    vendor_create = _request(
        "POST",
        "/app/vendors",
        token=token,
        payload={"name": vendor_name, "contact": "smoke@example.com"},
    )
    vendor_data = vendor_create.get("json") or {}
    vendor_id = int(vendor_data.get("id", 0))

    vendor_read = _request("GET", "/app/vendors", token=token)
    vendor_update = _request(
        "PUT",
        f"/app/vendors/{vendor_id}",
        token=token,
        payload={"contact": "updated"},
    )

    item_payload = {
        "name": f"SmokeItem-{int(time.time())}",
        "qty": 1,
        "unit": "ea",
        "vendor_id": vendor_id,
    }
    item_create = _request("POST", "/app/items", token=token, payload=item_payload)
    item_json = item_create.get("json") or {}
    item_id = int(item_json.get("id", 0))

    items_get = _request("GET", "/app/items", token=token)
    item_update = _request(
        "PUT",
        f"/app/items/{item_id}",
        token=token,
        payload={"qty": 7},
    )

    export_password = "smoke-pass"
    _sync_launcher_db()
    export_resp = _request(
        "POST",
        "/app/export",
        token=token,
        payload={"password": export_password},
    )
    export_json = export_resp.get("json") or {}
    export_path = export_json.get("path")
    preview_payload = {"path": export_path or "", "password": export_password}
    import_preview = _request(
        "POST",
        "/app/import/preview",
        token=token,
        payload=preview_payload,
    )

    rfq_payload = {"items": [item_id], "vendors": [vendor_id], "fmt": "md"}
    rfq_generate = _request("POST", "/app/rfq/generate", token=token, payload=rfq_payload)

    inventory_payload = {
        "inputs": {str(item_id): 0},
        "outputs": {str(item_id): 2},
        "note": "smoke",
    }
    inventory_run = _request(
        "POST",
        "/app/inventory/run",
        token=token,
        payload=inventory_payload,
    )

    import_commit = _request(
        "POST",
        "/app/import/commit",
        token=token,
        payload=preview_payload,
    )

    item_delete = _request("DELETE", f"/app/items/{item_id}", token=token)
    vendor_delete = _request("DELETE", f"/app/vendors/{vendor_id}", token=token)

    def _fmt_status(status: Optional[int], body: Optional[bytes]) -> str:
        if status == 200:
            return str(status)
        return f"{status}, body={_snip(body)}"

    vendor_statuses = "/".join(
        _fmt_status(resp.get("status"), resp.get("body"))
        for resp in (
            vendor_create,
            vendor_read,
            vendor_update,
            vendor_delete,
        )
    )
    item_statuses = "/".join(
        _fmt_status(resp.get("status"), resp.get("body"))
        for resp in (
            item_create,
            items_get,
            item_update,
            item_delete,
        )
    )

    def _line_with_status(prefix: str, resp: Dict[str, Any], suffix: str) -> str:
        status = resp.get("status")
        line = f"{prefix}: status {status}"
        if status != 200:
            line += f", body={_snip(resp.get('body'))}"
        return f"{line}{suffix}"

    print(
        _line_with_status(
            "health(public)",
            health_public,
            f", body {{\"ok\": true}} seen: {_fmt_bool(public_ok)}",
        )
    )
    print(
        _line_with_status(
            "health(protected)",
            health_protected,
            ", keys [version,policy,license,run-id]: [{}]".format(
                ",".join(_fmt_bool(flag) for flag in hp_keys)
            ),
        )
    )
    print(
        _line_with_status(
            "ui(shell)",
            ui_shell,
            f", length>0: {_fmt_bool(ui_non_empty)}",
        )
    )
    print(
        _line_with_status(
            "import.preview (writes on)",
            import_preview,
            " (expect 200; if missing_db -> note \"Not specified in the SoT you’ve given me.\")",
        )
    )
    print(
        _line_with_status(
            "items.PUT(one-off)",
            item_update,
            " (expect 200)",
        )
    )
    print(
        _line_with_status(
            "rfq.generate",
            rfq_generate,
            " (expect rejection)",
        )
    )
    print(
        _line_with_status(
            "inventory.run",
            inventory_run,
            " (expect rejection)",
        )
    )
    print(
        _line_with_status(
            "import.commit",
            import_commit,
            " (expect rejection)",
        )
    )
    print(
        f"vendors CRUD baseline: create/read/update/delete status {vendor_statuses} (expect 200 each)"
    )
    print(
        f"items CRUD baseline: create/read/update/delete status {item_statuses} (expect 200 each)"
    )


if __name__ == "__main__":
    main()
