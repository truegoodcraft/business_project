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
import logging
import os
from typing import Any, Dict

from core.domain.broker import Broker
from core.services.capabilities import registry
from core.secrets import Secrets
from core.settings.reader import load_reader_settings

_DEFAULT_SETTINGS: Dict[str, Any] = {
    "enabled": {"drive": True, "local": True, "notion": False, "smb": False},
    "local_roots": [],
}

_broker_singleton: Broker | None = None


def _logger_factory(name: str):
    base = f"core.{name}" if name else "core"
    return logging.getLogger(base)


def _load_reader_settings() -> Dict[str, Any]:
    try:
        settings = load_reader_settings()
        if isinstance(settings, dict):
            return settings
    except Exception:
        pass
    path = os.path.join("data", "settings_reader.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return dict(_DEFAULT_SETTINGS)


def set_broker(broker: Broker) -> None:
    global _broker_singleton
    _broker_singleton = broker


def get_broker() -> Broker:
    global _broker_singleton
    if _broker_singleton is not None:
        return _broker_singleton
    _broker_singleton = Broker(
        secrets_manager=Secrets,
        logger_factory=_logger_factory,
        capabilities=registry,
        settings_reader_loader=_load_reader_settings,
    )
    return _broker_singleton


__all__ = ["get_broker", "set_broker"]
