#!/usr/bin/env python3
"""SoT-aligned smoke tests for BUS Core licensing and baseline CRUD."""

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, Optional
from urllib import error, request

BASE_URL = os.environ.get("BUSCORE_BASE_URL", "http://127.0.0.1:8765")


def _fmt_bool(value: bool) -> str:
    return "true" if value else "false"


def _request(
    method: str,
    path: str,
    *,
    token: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    timeout: float = 10.0,
) -> Dict[str, Any]:
    url = f"{BASE_URL}{path}"
    headers: Dict[str, str] = {}
    data = None
    if token:
        headers["X-Session-Token"] = token
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
            status = resp.status
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        status = exc.code
    except Exception as exc:  # pragma: no cover - network failures
        return {"status": None, "body": str(exc), "json": None}
    parsed: Optional[Any]
    try:
        parsed = json.loads(body)
    except Exception:
        parsed = None
    return {"status": status, "body": body, "json": parsed}


def _expect_token() -> str:
    resp = _request("GET", "/session/token")
    if not resp.get("status") == 200:
        raise SystemExit(f"Failed to fetch session token: {resp}")
    payload = resp.get("json")
    if isinstance(payload, dict) and payload.get("token"):
        return str(payload["token"])
    if isinstance(payload, dict) and payload.get("token") is None and "token" in payload:
        return ""
    # Some builds return raw token text
    body = resp.get("body", "").strip()
    if body:
        try:
            data = json.loads(body)
            return str(data.get("token", body))
        except Exception:
            return body
    raise SystemExit("Session token missing from /session/token response")


def _ensure_writes(token: str) -> None:
    _request("POST", "/dev/writes", token=token, payload={"enabled": True})


def _sync_launcher_db() -> None:
    repo_db = Path("./data/app.db")
    base = os.environ.get("LOCALAPPDATA")
    if base:
        target_dir = Path(base) / "BUSCore"
    else:
        target_dir = Path.home() / "AppData" / "Local" / "BUSCore"
    target = target_dir / "app.db"
    if repo_db.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(repo_db, target)


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
        isinstance(hp_json, dict) and "licenses" in hp_json,
        isinstance(hp_json, dict) and "run_id" in hp_json,
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

    vendor_statuses = "/".join(
        str(x)
        for x in (
            vendor_create.get("status"),
            vendor_read.get("status"),
            vendor_update.get("status"),
            vendor_delete.get("status"),
        )
    )
    item_statuses = "/".join(
        str(x)
        for x in (
            item_create.get("status"),
            items_get.get("status"),
            item_update.get("status"),
            item_delete.get("status"),
        )
    )

    print(
        f"health(public): status {health_public.get('status')}, body {{\"ok\": true}} seen: {_fmt_bool(public_ok)}"
    )
    print(
        "health(protected): status {}, keys present [version, policy, license, run-id]: {}".format(
            health_protected.get("status"),
            [
                _fmt_bool(flag)
                for flag in hp_keys
            ],
        )
    )
    print(f"ui(shell): status {ui_shell.get('status')}, length>0: {_fmt_bool(ui_non_empty)}")
    print(
        f"import.preview (writes on): status {import_preview.get('status')} (expect 200)"
    )
    print(
        f"items.PUT(one-off): status {item_update.get('status')} (expect 200)"
    )
    print(
        f"rfq.generate: status {rfq_generate.get('status')} (expect rejection)"
    )
    print(
        f"inventory.run: status {inventory_run.get('status')} (expect rejection)"
    )
    print(
        f"import.commit: status {import_commit.get('status')} (expect rejection)"
    )
    print(
        f"vendors CRUD baseline: create/read/update/delete status {vendor_statuses} (expect 200 each)"
    )
    print(
        f"items CRUD baseline: create/read/update/delete status {item_statuses} (expect 200 each)"
    )


if __name__ == "__main__":
    main()
