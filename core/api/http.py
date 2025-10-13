from __future__ import annotations

import os
import secrets
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from core.conn_broker import ConnectionBroker
from tgc.bootstrap_fs import DATA, LOGS, TOKEN_FILE, ensure_first_run

# Ensure filesystem bootstrap happens before any runtime writes.
ensure_first_run()

APP = FastAPI(title="TGC Alpha Core", version="0.1.0")
RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
SESSION_TOKEN = secrets.token_urlsafe(24)
TOKEN_FILE.write_text(SESSION_TOKEN, encoding="utf-8")

LOG_FILE = LOGS / f"core_{RUN_ID}.log"


def _log(msg: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(msg.rstrip() + "\n")


class ProbeReq(BaseModel):
    services: Optional[List[str]] = None


class CrawlReq(BaseModel):
    limits: Optional[Dict[str, Any]] = None
    targets: Optional[Dict[str, Any]] = None


_CRAWLS: Dict[str, Dict[str, Any]] = {}


def _require_token(token: Optional[str]) -> None:
    if token != SESSION_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid session token")


def _discover_plugins() -> List[Dict[str, Any]]:
    try:
        from core.plugins_alpha import discover_alpha_plugins

        plugins = discover_alpha_plugins()
        discovered: List[Dict[str, Any]] = []
        for plugin in plugins:
            try:
                description = plugin.describe() or {}
            except Exception:
                description = {}
            services = description.get("services") or []
            scopes = description.get("scopes") or []
            discovered.append(
                {
                    "id": getattr(plugin, "id", plugin.__class__.__name__),
                    "name": getattr(plugin, "name", plugin.__class__.__name__),
                    "services": [str(s) for s in services if isinstance(s, str)],
                    "scopes": [str(s) for s in scopes if isinstance(s, str)],
                    "version": getattr(plugin, "version", "0"),
                }
            )
        return discovered
    except Exception:
        return [
            {
                "id": "example",
                "name": "Example Alpha Plugin",
                "services": ["drive"],
                "scopes": ["read_base"],
                "version": "0",
            }
        ]


def _probe_services(services: List[str]) -> Dict[str, Dict[str, Any]]:
    try:
        from tgc.bootstrap import bootstrap_controller

        controller = bootstrap_controller()
    except Exception:
        controller = object()
    broker = ConnectionBroker(controller)
    results: Dict[str, Dict[str, Any]] = {}
    for svc in services:
        result = broker.probe(svc)
        if not result.get("ok"):
            _augment_probe_hint(svc, result)
        results[svc] = result
    return results


def _augment_probe_hint(service: str, result: Dict[str, Any]) -> None:
    service = service.lower()
    if "hint" in result and result["hint"]:
        return
    creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    if service == "drive":
        if not creds:
            result.setdefault("hint", "Set GOOGLE_APPLICATION_CREDENTIALS or edit .env")
        else:
            path = Path(creds)
            if not path.exists():
                result.setdefault("hint", f"File not found: {path}")


def _start_crawl_async(run_id: str, limits: Optional[Dict[str, Any]] = None) -> None:
    state = _CRAWLS[run_id] = {
        "state": "running",
        "progress": 0,
        "stats": {},
        "last_error": None,
    }

    def worker() -> None:
        try:
            for index in range(1, 11):
                time.sleep(0.5)
                state["progress"] = index * 10
                _log(f"[{run_id}] progress={state['progress']}")
            state["state"] = "done"
            state["stats"] = {"items": 123, "duration_sec": 5}
            _log(f"[{run_id}] done")
        except Exception as exc:  # pragma: no cover - defensive guard
            state["state"] = "error"
            state["last_error"] = str(exc)
            _log(f"[{run_id}] error: {exc}")

    threading.Thread(target=worker, name=f"crawl-{run_id}", daemon=True).start()


@APP.get("/health")
def health(x_session_token: Optional[str] = Header(default=None, convert_underscores=False)) -> Dict[str, Any]:
    _require_token(x_session_token)
    return {"ok": True, "version": APP.version, "run_id": RUN_ID}


@APP.get("/plugins")
def plugins(x_session_token: Optional[str] = Header(default=None, convert_underscores=False)) -> List[Dict[str, Any]]:
    _require_token(x_session_token)
    return _discover_plugins()


@APP.post("/probe")
def probe(
    body: ProbeReq,
    x_session_token: Optional[str] = Header(default=None, convert_underscores=False),
) -> Dict[str, Any]:
    _require_token(x_session_token)
    bootstrap = ensure_first_run()
    services = body.services
    if not services:
        discovered = _discover_plugins()
        services = sorted({svc for plugin in discovered for svc in plugin.get("services", [])}) or ["drive"]
    results = _probe_services(services)
    return {"bootstrap": bootstrap, "results": results}


@APP.post("/crawl")
def crawl(
    body: CrawlReq,
    x_session_token: Optional[str] = Header(default=None, convert_underscores=False),
) -> Dict[str, str]:
    _require_token(x_session_token)
    run_id = f"crawl-{int(time.time())}"
    _start_crawl_async(run_id, body.limits or {})
    return {"run_id": run_id}


@APP.get("/crawl/{run_id}/status")
def crawl_status(
    run_id: str, x_session_token: Optional[str] = Header(default=None, convert_underscores=False)
) -> Dict[str, Any]:
    _require_token(x_session_token)
    return _CRAWLS.get(run_id, {"state": "unknown"})


@APP.get("/logs")
def logs(x_session_token: Optional[str] = Header(default=None, convert_underscores=False)) -> str:
    _require_token(x_session_token)
    if not LOG_FILE.exists():
        return "no logs yet"
    lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
    tail = lines[-200:]
    return "\n".join(tail)


def build_app() -> Tuple[FastAPI, str]:
    ensure_first_run()
    _log(f"session_token={SESSION_TOKEN}")
    return APP, SESSION_TOKEN


__all__ = ["APP", "build_app"]
