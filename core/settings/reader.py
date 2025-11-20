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

import json
from pathlib import Path
from typing import Any, Dict, cast

READER_SETTINGS_PATH = Path("data/settings_reader.json")

_DEFAULT_SETTINGS: Dict[str, object] = {
    "enabled": {"drive": True, "local": True, "notion": False, "smb": False},
    "local_roots": [],
    "drive_includes": {
        "include_my_drive": True,
        "my_drive_root_id": None,
        "include_shared_drives": True,
        "shared_drive_ids": [],
    },
}


def load_reader_settings() -> Dict[str, object]:
    data: Dict[str, object] = {}
    if READER_SETTINGS_PATH.exists():
        try:
            loaded = json.loads(READER_SETTINGS_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
        except Exception:
            data = {}

    result: Dict[str, object] = {
        "enabled": dict(_DEFAULT_SETTINGS["enabled"]),
        "local_roots": list(_DEFAULT_SETTINGS["local_roots"]),
        "drive_includes": dict(_DEFAULT_SETTINGS["drive_includes"]),
    }

    enabled = data.get("enabled")
    if isinstance(enabled, dict):
        result["enabled"].update({str(k): bool(v) for k, v in enabled.items()})

    local_roots = data.get("local_roots")
    if isinstance(local_roots, list):
        result["local_roots"] = [str(item) for item in local_roots if isinstance(item, str)]

    drive_includes = data.get("drive_includes")
    if isinstance(drive_includes, dict):
        di_defaults = cast(Dict[str, Any], result["drive_includes"])
        shared_ids_src = drive_includes.get(
            "shared_drive_ids", di_defaults.get("shared_drive_ids", [])
        )
        if isinstance(shared_ids_src, list):
            shared_ids = [str(item) for item in shared_ids_src if isinstance(item, str)]
        else:
            shared_ids = []

        di: Dict[str, object] = {
            "include_my_drive": bool(
                drive_includes.get("include_my_drive", di_defaults["include_my_drive"])
            ),
            "my_drive_root_id": drive_includes.get("my_drive_root_id") or None,
            "include_shared_drives": bool(
                drive_includes.get("include_shared_drives", di_defaults["include_shared_drives"])
            ),
            "shared_drive_ids": shared_ids,
        }
        result["drive_includes"] = di

    return result


def save_reader_settings(settings: Dict[str, object]) -> None:
    READER_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    READER_SETTINGS_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")
