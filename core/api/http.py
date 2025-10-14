from __future__ import annotations

import secrets
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from core.conn_broker import ConnectionBroker
from core.version import VERSION
from tgc.bootstrap_fs import DATA, LOGS, ensure_first_run

ensure_first_run()

APP = FastAPI(title="TGC Alpha Core", version=VERSION)
RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
SESSION_TOKEN = secrets.token_urlsafe(24)
(DATA / "session_token.txt").write_text(SESSION_TOKEN, encoding="utf-8")

LOG_FILE = LOGS / f"core_{RUN_ID}.log"


def log(msg: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(msg.rstrip() + "\n")


class ProbeReq(BaseModel):
    services: Optional[List[str]] = None


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


def _probe_services(broker: ConnectionBroker, services: List[str]) -> Dict[str, Dict[str, Any]]:
    return {service: broker.probe(service) for service in services}


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
def health(x_session_token: Optional[str] = Header(default=None, convert_underscores=False)) -> Dict[str, Any]:
    _require_token(x_session_token)
    return {"ok": True, "version": APP.version, "run_id": RUN_ID}


@APP.get("/plugins")
def plugins(x_session_token: Optional[str] = Header(default=None, convert_underscores=False)) -> List[Dict[str, Any]]:
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
def probe(body: ProbeReq, x_session_token: Optional[str] = Header(default=None, convert_underscores=False)) -> Dict[str, Any]:
    _require_token(x_session_token)
    bootstrap = ensure_first_run()
    plugs = _discover_plugins()
    broker = ConnectionBroker(controller=None)
    _register_providers(broker, plugs)
    declared = sorted(
        {
            svc
            for plugin in plugs
            for svc in (getattr(plugin, "describe", lambda: {})() or {}).get("services", [])
        }
    )
    services = body.services or declared
    if not services:
        return {"bootstrap": bootstrap, "results": {}}
    results = _probe_services(broker, services)
    return {"bootstrap": bootstrap, "results": results}


@APP.post("/crawl")
def crawl(body: CrawlReq, x_session_token: Optional[str] = Header(default=None, convert_underscores=False)) -> Dict[str, str]:
    _require_token(x_session_token)
    run_id = f"crawl-{int(time.time())}"
    _start_crawl_async(run_id, body.limits or {})
    return {"run_id": run_id}


@APP.get("/crawl/{run_id}/status")
def crawl_status(run_id: str, x_session_token: Optional[str] = Header(default=None, convert_underscores=False)) -> Dict[str, Any]:
    _require_token(x_session_token)
    return _CRAWLS.get(run_id, {"state": "unknown"})


@APP.get("/logs")
def logs(x_session_token: Optional[str] = Header(default=None, convert_underscores=False)) -> str:
    _require_token(x_session_token)
    if not LOG_FILE.exists():
        return "no logs yet"
    return "\n".join(LOG_FILE.read_text(encoding="utf-8").splitlines()[-200:])


def build_app():
    ensure_first_run()
    log(f"session_token={SESSION_TOKEN}")
    return APP, SESSION_TOKEN
