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
