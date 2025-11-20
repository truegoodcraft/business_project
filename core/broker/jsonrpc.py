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
import json, struct
from typing import Any, Dict

_LEN = struct.Struct("<I")

def pack(obj: Dict[str, Any]) -> bytes:
    data = json.dumps(obj, separators=(",",":")).encode("utf-8")
    return _LEN.pack(len(data)) + data

def unpack_frame(buf: bytes) -> Dict[str, Any]:
    return json.loads(buf.decode("utf-8"))

def req(method: str, params: dict, id: int) -> dict:
    return {"jsonrpc":"2.0","method":method,"params":params,"id":id}

def res(id: int, result: Any) -> dict:
    return {"jsonrpc":"2.0","result":result,"id":id}

def err(id: int, code: int, message: str, data: Any|None=None) -> dict:
    e = {"code":code,"message":message}
    if data is not None: e["data"]=data
    return {"jsonrpc":"2.0","error":e,"id":id}
