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

from core.domain.broker import Broker

_broker_singleton: Broker | None = None


def set_broker():
    """
    Initialize the Broker.
    In a full Microkernel, this is where we would scan a /plugins directory.
    For now, it initializes an empty, stable core.
    """
    global _broker_singleton
    if _broker_singleton is None:
        _broker_singleton = Broker()
    # Core services with zero external deps could be registered here.
    # Plugins should call Broker.register_provider(...) at runtime.
    return


def get_broker() -> Broker:
    global _broker_singleton
    if _broker_singleton is None:
        _broker_singleton = Broker()
    return _broker_singleton


__all__ = ["get_broker", "set_broker"]
