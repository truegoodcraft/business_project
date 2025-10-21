SERVICE_ID = "local"
VERSION = "1.0.0"
_b = None


def describe():
    return {
        "id": SERVICE_ID,
        "name": "Local Files (built-in, read)",
        "version": VERSION,
        "services": ["local.read"],
        "scopes": ["read"],
        "builtin": True,
        "capabilities": ["local.files.read"],
    }


def register_broker(broker):
    global _b
    _b = broker


def probe(timeout_s=0.9):
    try:
        status = _b.service_call("local_fs", "status", {})
        ok = bool(status.get("configured"))
        return {
            "ok": ok,
            "status": "ready" if ok else "blocked",
            "details": {"roots": status.get("roots", [])},
        }
    except Exception:
        return {"ok": False, "status": "blocked"}


def read(op, params):
    if op == "children":
        return _b.service_call(
            "local_fs",
            "list_children",
            {"parent_id": params.get("parent_id", "local:root")},
        )
    if op == "catalog_open":
        return _b.catalog_open(
            "local_fs",
            params.get("scope", "local_roots"),
            {
                "recursive": bool(params.get("recursive", True)),
                "page_size": int(params.get("page_size", 500)),
                "fingerprint": bool(params.get("fingerprint", False)),
            },
        )
    if op == "catalog_next":
        return _b.catalog_next(params["stream_id"], int(params.get("max_items", 500)))
    if op == "catalog_close":
        return _b.catalog_close(params["stream_id"])
    return {"error": "unknown_op"}
