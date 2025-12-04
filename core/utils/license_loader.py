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

from pathlib import Path
import os, json
from typing import Any, Dict

_DEFAULT = {"tier": "community", "features": {}, "plugins": {}}

def _license_path() -> Path:
    # Dev: BUS_ROOT\license.json ; Prod: %LOCALAPPDATA%\BUSCore\license.json
    if os.environ.get("BUS_ROOT"):
        return Path(os.environ["BUS_ROOT"]).resolve() / "license.json"
    local_root = os.environ.get("LOCALAPPDATA")
    if local_root:
        return Path(local_root) / "BUSCore" / "license.json"
    return Path.home() / "BUSCore" / "license.json"


def _coerce_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "on", "enabled")
    if isinstance(v, dict):
        # allow {"enabled": true}
        if "enabled" in v:
            return _coerce_bool(v["enabled"])
    return bool(v)


def get_license(*, force_reload: bool | None = None) -> Dict[str, Any]:
    """
    ALWAYS read from disk in dev (BUS_ROOT set). No cache.
    Accept UTF-8 and UTF-8 with BOM.
    """
    path = _license_path()
    data: Dict[str, Any] = dict(_DEFAULT)
    try:
        with path.open("r", encoding="utf-8-sig") as f:  # BOM-safe
            raw = json.load(f)
        if isinstance(raw, dict):
            data.update(raw)
    except Exception:
        # keep defaults if file missing/invalid
        pass

    # Normalize features/plugins
    feats = data.get("features", {})
    if not isinstance(feats, dict):
        feats = {}
    data["features"] = {k: _coerce_bool(v) for k, v in feats.items()}

    if not isinstance(data.get("plugins"), dict):
        data["plugins"] = {}

    data.setdefault("tier", "community")
    return data


def feature_enabled(name: str) -> bool:
    # CRITICAL: force fresh read so gates reflect current file in dev
    lic = get_license(force_reload=True)
    return bool(lic.get("features", {}).get(name, False))
