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

"""Persistent plugin enable/disable state management."""

from __future__ import annotations

import json
import pathlib
from typing import Dict

_STATE_PATH = pathlib.Path("data/plugins_state.json")


def _ensure_parent() -> None:
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)


def _load_raw() -> Dict[str, dict]:
    try:
        raw = json.loads(_STATE_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}
    if isinstance(raw, dict):
        return {str(k): (v if isinstance(v, dict) else {}) for k, v in raw.items()}
    return {}


def _write_raw(data: Dict[str, dict]) -> None:
    _ensure_parent()
    _STATE_PATH.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def all_states() -> Dict[str, dict]:
    """Return the stored state mapping."""

    return _load_raw()


def is_enabled(plugin: str) -> bool:
    """Return whether ``plugin`` is enabled (default True)."""

    state = _load_raw()
    entry = state.get(plugin) or {}
    enabled = entry.get("enabled")
    if isinstance(enabled, bool):
        return enabled
    return True


def set_enabled(plugin: str, enabled: bool) -> None:
    """Persist the enabled flag for ``plugin``."""

    state = _load_raw()
    entry = state.get(plugin) or {}
    entry["enabled"] = bool(enabled)
    state[plugin] = entry
    _write_raw(state)


def state_path() -> pathlib.Path:
    """Return the path where plugin state is stored."""

    return _STATE_PATH
