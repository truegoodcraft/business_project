from __future__ import annotations

import concurrent.futures
import json
import secrets
import threading
import time
import time as _time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import Body, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel
from starlette.responses import StreamingResponse
from core.auth.google_sa import validate_google_service_account
from core.capabilities import registry
from core.conn_broker import ConnectionBroker
from core.version import VERSION
from tgc.bootstrap_fs import DATA, LOGS, ensure_first_run

APP = FastAPI(title="TGC Alpha Core", version=VERSION)
LICENSE_NAME = "PolyForm-Noncommercial-1.0.0"
LICENSE_URL = "https://polyformproject.org/licenses/noncommercial/1.0.0/"
RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
SESSION_TOKEN = secrets.token_urlsafe(24)
(DATA / "session_token.txt").write_text(SESSION_TOKEN, encoding="utf-8")

LOG_FILE = LOGS / f"core_{RUN_ID}.log"

_SUBSCRIBERS: set[Any] = set()

PROBE_TIMEOUT_SEC = 5  # per-service timeout


@APP.middleware("http")
async def _license_header_mw(request: Request, call_next):
    resp = await call_next(request)
    try:
        resp.headers["X-TGC-License"] = LICENSE_NAME
        resp.headers["X-TGC-License-URL"] = LICENSE_URL
    except Exception:
        pass
    return resp


def log(msg: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(msg.rstrip() + "\n")


class CrawlReq(BaseModel):
    limits: Optional[Dict[str, Any]] = None
    targets: Optional[Dict[str, Any]] = None


_CRAWLS: Dict[str, Dict[str, Any]] = {}


def _require_token(token: Optional[str]) -> None:
    if token != SESSION_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid session token")


def _discover_plugins() -> List[Any]:
    try:
        from core.plugins_alpha import discover_alpha_plugins

        return discover_alpha_plugins()
    except Exception:
        return []


def _register_providers(broker: ConnectionBroker, plugins: List[Any]) -> None:
    for plugin in plugins:
        if hasattr(plugin, "register_broker"):
            try:
                plugin.register_broker(broker)
            except Exception:
                pass


def _probe_one(broker: ConnectionBroker, svc: str) -> dict:
    t0 = _time.time()
    try:
        res = broker.probe(svc)
        if not isinstance(res, dict):
            res = {"ok": bool(res)}
        res.setdefault("elapsed_ms", int((_time.time() - t0) * 1000))
        return res
    except Exception as e:
        return {
            "ok": False,
            "detail": "probe_exception",
            "error": str(e),
            "elapsed_ms": int((_time.time() - t0) * 1000),
        }


def _probe_services(broker: ConnectionBroker, services: list[str]) -> dict[str, dict]:
    results: dict[str, dict] = {}
    if not services:
        return results
    max_workers = min(8, max(1, len(services)))
    wall_timeout = PROBE_TIMEOUT_SEC * max(1, len(services))
    t_start = _time.time()
    log(f"[probe] start services={services} per={PROBE_TIMEOUT_SEC}s wall={wall_timeout}s")
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futs = {pool.submit(_probe_one, broker, svc): svc for svc in services}
        try:
            for fut in concurrent.futures.as_completed(futs, timeout=wall_timeout):
                svc = futs[fut]
                try:
                    results[svc] = fut.result(timeout=0)
                except concurrent.futures.TimeoutError:
                    results[svc] = {
                        "ok": False,
                        "detail": "probe_timeout",
                        "timeout_sec": PROBE_TIMEOUT_SEC,
                    }
                except Exception as e:
                    results[svc] = {
                        "ok": False,
                        "detail": "probe_exception",
                        "error": str(e),
                    }
        except concurrent.futures.TimeoutError:
            pass
    for fut, svc in futs.items():
        if svc not in results:
            results[svc] = {
                "ok": False,
                "detail": "probe_timeout",
                "timeout_sec": PROBE_TIMEOUT_SEC,
            }
    log(
        f"[probe] done elapsed_ms={int((_time.time()-t_start)*1000)} results="
        f"{ {k: ('ok' if v.get('ok') else v.get('detail','fail')) for k,v in results.items()} }"
    )
    return results


def _bootstrap_capabilities() -> None:
    ok, meta = validate_google_service_account()
    registry.upsert(
        "auth.google.service_account",
        provider="core",
        status="ready" if ok else "blocked",
        policy={"allowed": ok, "mode": "read-only"},
        meta={k: v for k, v in meta.items() if k in ("project_id", "client_email", "path_exists")},
    )

    plugs = _discover_plugins()
    provides: Dict[str, str] = {}
    requires: Dict[str, List[str]] = {}
    for plugin in plugs:
        pid = getattr(plugin, "id", plugin.__class__.__name__)
        try:
            caps = plugin.capabilities() or {}
        except Exception:
            caps = {}
        prov = [str(item) for item in caps.get("provides", [])]
        req = [str(item) for item in caps.get("requires", [])]
        requires[pid] = req
        for cap in prov:
            provides[cap] = pid

    for cap, pid in provides.items():
        registry.upsert(cap, provider=pid, status="pending", policy={"allowed": True})

    current = {c.cap: c for c in registry.list()}
    for pid, reqs in requires.items():
        missing = [r for r in reqs if r not in current or current[r].status != "ready"]
        if missing:
            for cap, provider in provides.items():
                if provider == pid:
                    registry.upsert(
                        cap,
                        provider=pid,
                        status="blocked",
                        policy={"allowed": False, "reason": f"requires_missing:{','.join(missing)}"},
                    )

    current = {c.cap: c for c in registry.list()}
    for cap, capability in current.items():
        if capability.status == "pending":
            registry.upsert(cap, provider=capability.provider, status="ready", policy={"allowed": True})

    registry.emit_manifest_async()
    log("[capabilities] async manifest write requested after probe")


def _start_crawl_async(run_id: str, limits: Dict[str, Any]) -> None:
    state = _CRAWLS[run_id] = {"state": "running", "progress": 0, "stats": {}, "last_error": None}

    def work() -> None:
        try:
            for index in range(1, 11):
                time.sleep(0.5)
                state["progress"] = index * 10
                log(f"[{run_id}] progress={state['progress']}")
            state["state"] = "done"
            state["stats"] = {"items": 123, "duration_sec": 5}
            log(f"[{run_id}] done")
        except Exception as exc:  # pragma: no cover - defensive guard
            state["state"] = "error"
            state["last_error"] = str(exc)
            log(f"[{run_id}] error: {exc}")

    threading.Thread(target=work, daemon=True).start()


@APP.get("/health")
def health(x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token")) -> Dict[str, Any]:
    _require_token(x_session_token)
    return {"ok": True, "version": APP.version, "run_id": RUN_ID}


@APP.get("/license")
def license_info(x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token")):
    _require_token(x_session_token)
    return {
        "component": "BUS core",
        "license": LICENSE_NAME,
        "url": LICENSE_URL,
        "note": "Noncommercial use only. Commercial use requires permission. Contact Truegoodcraft@gmail.com",
    }


@APP.get("/plugins")
def plugins(x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token")) -> List[Dict[str, Any]]:
    _require_token(x_session_token)
    plugs = _discover_plugins()
    out: List[Dict[str, Any]] = []
    for plugin in plugs:
        try:
            desc = plugin.describe() or {}
        except Exception:
            desc = {}
        out.append(
            {
                "id": getattr(plugin, "id", plugin.__class__.__name__),
                "name": getattr(plugin, "name", plugin.__class__.__name__),
                "services": list(desc.get("services", [])),
                "scopes": list(desc.get("scopes", [])),
                "version": getattr(plugin, "version", "0"),
            }
        )
    return out


@APP.post("/probe")
def probe(
    x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token"),
    body: Any = Body(default=None),
) -> Dict[str, Any]:
    _require_token(x_session_token)
    bootstrap = ensure_first_run()

    plugs = _discover_plugins()
    broker = ConnectionBroker(controller=None)
    _register_providers(broker, plugs)

    declared = sorted(
        {
            svc
            for p in plugs
            for svc in ((getattr(p, "describe", lambda: {})() or {}).get("services", []) or [])
        }
    )

    services: list[str] = []
    try:
        if body is None:
            services = declared
        elif isinstance(body, dict) and "services" in body:
            s = body.get("services") or []
            services = list(s) if isinstance(s, list) else []
        elif isinstance(body, list):
            services = list(body)
        else:
            services = declared
    except Exception:
        services = declared

    if not services:
        return {"bootstrap": bootstrap, "results": {}}

    results = _probe_services(broker, services)
    return {"bootstrap": bootstrap, "results": results}


@APP.post("/crawl")
def crawl(
    body: CrawlReq, x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token")
) -> Dict[str, str]:
    _require_token(x_session_token)
    run_id = f"crawl-{int(time.time())}"
    _start_crawl_async(run_id, body.limits or {})
    return {"run_id": run_id}


@APP.get("/crawl/{run_id}/status")
def crawl_status(
    run_id: str, x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token")
) -> Dict[str, Any]:
    _require_token(x_session_token)
    return _CRAWLS.get(run_id, {"state": "unknown"})


@APP.get("/logs")
def logs(x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token")) -> str:
    _require_token(x_session_token)
    if not LOG_FILE.exists():
        return "no logs yet"
    return "\n".join(LOG_FILE.read_text(encoding="utf-8").splitlines()[-200:])


@APP.get("/capabilities")
def get_capabilities(
    x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token")
) -> Dict[str, Any]:
    _require_token(x_session_token)
    out = registry.emit_manifest_async()
    out.setdefault("license", {"core": LICENSE_NAME, "core_url": LICENSE_URL})
    log("[capabilities] served manifest to client; async write started")
    return out


@APP.get("/capabilities/stream")
def stream_capabilities(
    x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token")
) -> StreamingResponse:
    _require_token(x_session_token)

    async def event_gen():
        import asyncio

        while True:
            data = registry.emit_manifest()
            yield f"event: CAPABILITY_UPDATE\ndata: {json.dumps(data)}\n\n"
            await asyncio.sleep(5)

    return StreamingResponse(event_gen(), media_type="text/event-stream")


def build_app():
    ensure_first_run()
    _bootstrap_capabilities()
    log(f"session_token={SESSION_TOKEN}")
    return APP, SESSION_TOKEN
