from __future__ import annotations

import json
import secrets
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Body, FastAPI, Header, HTTPException, Request

from core.capabilities import registry
from core.capabilities.registry import MANIFEST_PATH
from core.runtime.core_alpha import CoreAlpha
from core.runtime.policy import PolicyDecision
from core.runtime.probe import PROBE_TIMEOUT_SEC
from core.version import VERSION
from tgc.bootstrap_fs import DATA, LOGS

APP = FastAPI(title="BUS Core Alpha", version=VERSION)
LICENSE_NAME = "PolyForm-Noncommercial-1.0.0"
LICENSE_URL = "https://polyformproject.org/licenses/noncommercial/1.0.0/"

CORE: CoreAlpha | None = None
RUN_ID: str = ""
SESSION_TOKEN: str = ""
LOG_FILE: Path | None = None


def log(msg: str) -> None:
    path = LOG_FILE or (LOGS / "core.log")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(msg.rstrip() + "\n")


@APP.middleware("http")
async def _license_header_mw(request: Request, call_next):
    start = time.time()
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        elapsed_ms = int((time.time() - start) * 1000)
        summary = {
            "path": request.url.path,
            "method": request.method,
            "elapsed_ms": elapsed_ms,
            "run_id": RUN_ID,
            "status": getattr(response, "status_code", 0),
        }
        try:
            if response is not None:
                response.headers["X-TGC-License"] = LICENSE_NAME
                response.headers["X-TGC-License-URL"] = LICENSE_URL
        except Exception:
            pass
        log(f"[request] {json.dumps(summary, separators=(',', ':'))}")


def _require_core() -> CoreAlpha:
    if CORE is None:
        raise HTTPException(status_code=503, detail="core_not_initialized")
    return CORE


def _require_token(token: Optional[str]) -> None:
    if token != SESSION_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid session token")


def _with_run_id(payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(payload)
    payload.setdefault("run_id", RUN_ID)
    return payload


@APP.get("/health")
def health(x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token")) -> Dict[str, Any]:
    _require_token(x_session_token)
    return _with_run_id({"ok": True, "version": VERSION})


@APP.get("/plugins")
def plugins(x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token")) -> Dict[str, Any]:
    _require_token(x_session_token)
    core = _require_core()
    out = core.plugin_list()
    return _with_run_id({"plugins": out})


@APP.post("/probe")
def probe(
    body: Any = Body(default=None),
    x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token"),
) -> Dict[str, Any]:
    _require_token(x_session_token)
    core = _require_core()
    services: List[str]
    if body is None:
        services = sorted({svc for item in core.plugin_list() for svc in item.get("services", [])})
    elif isinstance(body, dict) and isinstance(body.get("services"), list):
        services = [str(s) for s in body.get("services", [])]
    elif isinstance(body, list):
        services = [str(s) for s in body]
    else:
        services = []
    results = core.probe_services(services)
    payload = {
        "bootstrap": core.bootstrap,
        "results": results,
        "probe_timeout_sec": PROBE_TIMEOUT_SEC,
    }
    return _with_run_id(payload)


@APP.get("/capabilities")
def get_capabilities(x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token")) -> Dict[str, Any]:
    _require_token(x_session_token)
    manifest = registry.emit_manifest_async()
    manifest.setdefault("license", {"core": LICENSE_NAME, "core_url": LICENSE_URL})
    return _with_run_id(manifest)


@APP.post("/execTransform")
def exec_transform(
    body: Dict[str, Any] = Body(...),
    x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token"),
) -> Dict[str, Any]:
    _require_token(x_session_token)
    core = _require_core()
    plugin = str(body.get("plugin") or "").strip()
    fn = str(body.get("fn") or "").strip()
    idempotency_key = str(body.get("idempotency_key") or "").strip()
    if not plugin or not fn or not idempotency_key:
        raise HTTPException(status_code=400, detail="Missing plugin/fn/idempotency_key")
    input_payload = body.get("input") or {}
    limits = body.get("limits") or {}
    outcome = core.transform(
        plugin_id=plugin,
        fn=fn,
        input_payload=input_payload,
        limits=limits,
        idempotency_key=idempotency_key,
    )
    proposal = outcome.get("proposal")
    policy = outcome.get("policy")
    if isinstance(policy, PolicyDecision):
        policy_block = {"decision": policy.decision, "reasons": list(policy.reasons)}
    elif isinstance(policy, dict):
        policy_block = {
            "decision": str(policy.get("decision", "deny")),
            "reasons": list(policy.get("reasons", [])),
        }
    else:
        policy_block = {"decision": "deny", "reasons": ["unknown_policy"]}
    return _with_run_id({"proposal": proposal, "policy": policy_block})


@APP.post("/policy.simulate")
def policy_simulate(
    body: Dict[str, Any] = Body(...),
    x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token"),
) -> Dict[str, Any]:
    _require_token(x_session_token)
    core = _require_core()
    intent = str(body.get("intent") or "").strip()
    metadata = body.get("metadata") or {}
    decision = core.policy.simulate(intent, metadata)
    payload = {
        "decision": decision.decision,
        "reasons": list(decision.reasons),
    }
    return _with_run_id(payload)


@APP.post("/nodes.manifest.sync")
def manifest_sync(
    body: Dict[str, Any] = Body(...),
    x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token"),
) -> Dict[str, Any]:
    _require_token(x_session_token)
    manifest = body.get("manifest")
    if not isinstance(manifest, dict):
        raise HTTPException(status_code=400, detail="invalid_manifest")
    if not registry.validate_signature(manifest):
        raise HTTPException(status_code=400, detail="signature_invalid")
    return _with_run_id({"ok": True})


@APP.get("/transparency.report")
def transparency_report(x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token")) -> Dict[str, Any]:
    _require_token(x_session_token)
    core = _require_core()
    report = core.transparency_report()
    report["manifest_path"] = str(MANIFEST_PATH)
    return _with_run_id(report)


@APP.get("/logs")
def logs(x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token")) -> Dict[str, Any]:
    _require_token(x_session_token)
    path = LOG_FILE or (LOGS / "core.log")
    if not path.exists():
        return _with_run_id({"logs": []})
    lines = path.read_text(encoding="utf-8").splitlines()[-200:]
    return _with_run_id({"logs": lines})


def build_app():
    global CORE, RUN_ID, SESSION_TOKEN, LOG_FILE
    policy_path = Path("config/policy.json")
    CORE = CoreAlpha(policy_path=policy_path)
    RUN_ID = CORE.run_id
    SESSION_TOKEN = secrets.token_urlsafe(24)
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "session_token.txt").write_text(SESSION_TOKEN, encoding="utf-8")
    CORE.configure_session_token(SESSION_TOKEN)
    LOG_FILE = LOGS / f"core_{RUN_ID}.log"
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    banner = f"[trust] mode={CORE.policy.mode} telemetry=off data={DATA} logs={LOGS}"
    print(banner)
    log(banner)
    return APP, SESSION_TOKEN


__all__ = ["APP", "build_app", "SESSION_TOKEN"]
