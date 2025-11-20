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

"""Internal runtime helpers for capability execution."""

import time
import uuid
from typing import Any, Dict, Optional

from core.services.capabilities import meta, resolve
from core.config import load_core_config
from core.permissions import require
from core.plugin_api import Context
from core.safelog import logger

_RUNTIME_LIMITS: Dict[str, Any] = {}


def set_runtime_limits(limits: Dict[str, Any]) -> None:
    global _RUNTIME_LIMITS
    _RUNTIME_LIMITS = dict(limits)


def get_runtime_limits() -> Dict[str, Any]:
    return dict(_RUNTIME_LIMITS)


def generate_run_id() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ") + "-" + str(uuid.uuid4())[:8]


def run_capability(cap_name: str, run_id: Optional[str] = None, **params):
    fn = resolve(cap_name)
    m = meta(cap_name)
    require(m["plugin"], m["scopes"])
    ctx = Context(
        run_id=run_id or generate_run_id(),
        config=load_core_config(),
        limits=get_runtime_limits(),
        logger=logger,
    )
    return fn(ctx, **params)
