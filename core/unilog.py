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

"""Unified logging helpers."""

from __future__ import annotations

import json
import os
import pathlib
import time
from typing import Any

_DEFAULT_PATH = "reports/all.log"


def _log_path() -> pathlib.Path:
    path_value = os.getenv("UNIFIED_LOG_PATH", _DEFAULT_PATH)
    path = pathlib.Path(path_value)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write(event: str, run_id: str | None = None, **fields: Any) -> None:
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "event": event,
        "run_id": run_id,
        **fields,
    }
    with _log_path().open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")

