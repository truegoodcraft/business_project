# SPDX-License-Identifier: AGPL-3.0-or-later
# TGC BUS Core (Business Utility System Core)
# Copyright (C) 2025 True Good Craft
#
# This file is part of TGC BUS Core.
#
# TGC BUS Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# TGC BUS Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with TGC BUS Core.  If not, see <https://www.gnu.org/licenses/>.

SERVICE_ID = "google_drive"
VERSION = "1.0.0"
_b = None


def describe():
    return {
        "id": SERVICE_ID,
        "name": "Google Drive (built-in, read)",
        "version": VERSION,
        "services": ["drive.read"],
        "scopes": ["read"],
        "builtin": True,
        "capabilities": ["drive.files.read"],
    }


def register_broker(broker):
    global _b
    _b = broker


def probe(timeout_s=0.9):
    try:
        status = _b.service_call("google_drive", "status", {})
        ok = bool(status.get("configured") and status.get("can_exchange_token"))
        return {
            "ok": ok,
            "status": "ready" if ok else "blocked",
            "details": {"configured": status.get("configured", False)},
        }
    except Exception:
        return {"ok": False, "status": "blocked"}


def read(op, params):
    if op == "children":
        return _b.service_call(
            "google_drive",
            "list_children",
            {
                "parent_id": params.get("parent_id", "drive:root"),
                "page_size": int(params.get("page_size", 200)),
                "page_token": params.get("page_token"),
            },
        )
    if op == "catalog_open":
        return _b.catalog_open(
            "google_drive",
            params.get("scope", "allDrives"),
            {
                "recursive": bool(params.get("recursive", True)),
                "page_size": int(params.get("page_size", 500)),
                "fingerprint": bool(params.get("fingerprint", False)),
            },
        )
    if op == "catalog_next":
        return _b.catalog_next(params["stream_id"], int(params.get("max_items", 500)))
    if op == "catalog_close":
        return _b.catalog_close(params["stream_id"])
    return {"error": "unknown_op"}
