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
from typing import Any, Dict
from .jsonrpc import unpack_frame, pack, res, err
from .pipes import PipeConnection

class PluginBroker:
    """
    Thin dispatcher for plugin requests. No secrets; read-only services later.
    """
    def dispatch(self, method: str, params: Dict[str, Any]) -> Any:
        if method == "hello":   # params: {plugin_id, api_version}
            return {"ok": True}
        if method == "ping":
            return {"ok": True}
        raise KeyError("Method not found")

def handle_connection(conn: PipeConnection, broker: PluginBroker):
    while True:
        try:
            req_obj = unpack_frame(conn.read_frame())
        except Exception:
            break
        mid = req_obj.get("id", 0)
        try:
            result = broker.dispatch(req_obj.get("method",""), req_obj.get("params",{}))
            conn.write_frame(pack(res(mid, result)))
        except Exception as e:
            conn.write_frame(pack(err(mid, -32601, str(e))))
