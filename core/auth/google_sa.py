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

from __future__ import annotations
import os, json
from pathlib import Path
from typing import Dict, Any, Tuple

def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]  # core/auth -> core -> repo

def _resolve_creds_path() -> Path:
    envp = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if envp:
        p = Path(os.path.expandvars(os.path.expanduser(envp)))
        if not p.is_absolute():
            p = (_project_root() / p).resolve()
        return p
    return (_project_root() / "credentials" / "service-account.json").resolve()

def validate_google_service_account() -> Tuple[bool, Dict[str, Any]]:
    """
    Validate presence & basic structure of service-account JSON.
    Returns (ready, meta) with no secrets.
    """
    p = _resolve_creds_path()
    meta: Dict[str, Any] = {"path_exists": p.exists(), "path": str(p)}
    if not p.exists():
        return False, {**meta, "detail": "missing_credentials",
                       "hint": "Place service-account.json under credentials/ or set GOOGLE_APPLICATION_CREDENTIALS"}
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
        if obj.get("type") != "service_account":
            return False, {**meta, "detail": "not_service_account"}
        meta.update({"project_id": obj.get("project_id"), "client_email": obj.get("client_email")})
        return True, meta
    except Exception as e:
        return False, {**meta, "detail": "invalid_json", "error": str(e)}
