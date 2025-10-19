from __future__ import annotations

import json
import secrets
import time
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from fastapi import Body, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

import requests

from core.capabilities import registry
from core.capabilities.registry import MANIFEST_PATH
from core.runtime.core_alpha import CoreAlpha
from core.runtime.policy import PolicyDecision
from core.runtime.probe import PROBE_TIMEOUT_SEC
from core.secrets.manager import SecretError, Secrets
from core.version import VERSION
from tgc.bootstrap_fs import DATA, LOGS

APP = FastAPI(title="BUS Core Alpha", version=VERSION)
LICENSE_NAME = "PolyForm-Noncommercial-1.0.0"
LICENSE_URL = "https://polyformproject.org/licenses/noncommercial/1.0.0/"

CORE: CoreAlpha | None = None
RUN_ID: str = ""
SESSION_TOKEN: str = ""
LOG_FILE: Path | None = None
_OAUTH_STATES: Dict[str, Dict[str, Any]] = {}


def log(msg: str) -> None:
    path = LOG_FILE or (LOGS / "core.log")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(msg.rstrip() + "\n")


def _resolve_ui_static_dir() -> Path:
    exe_dir = Path(sys.executable).resolve().parent
    repo_dir = Path(__file__).resolve().parents[2]
    meipass_root = getattr(sys, "_MEIPASS", "")
    candidates = [
        exe_dir / "core" / "ui",
        repo_dir / "core" / "ui",
    ]
    if meipass_root:
        candidates.append(Path(meipass_root) / "core" / "ui")

    for candidate in candidates:
        if candidate.exists():
            log(f"[ui] static_dir={candidate} exists=True")
            return candidate

    fallback = candidates[0]
    log(f"[ui] static_dir={fallback} exists=False")
    return fallback


UI_STATIC_DIR = _resolve_ui_static_dir()
APP.mount("/ui/static", StaticFiles(directory=str(UI_STATIC_DIR)), name="ui-static")


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


def _prune_oauth_states() -> None:
    if not _OAUTH_STATES:
        return
    now = time.time()
    expired = [key for key, meta in _OAUTH_STATES.items() if meta.get("expires_at", 0) <= now]
    for key in expired:
        _OAUTH_STATES.pop(key, None)


@APP.get("/ui")
def ui_index() -> FileResponse:
    return FileResponse(UI_STATIC_DIR / "index.html")


def _load_google_client() -> tuple[str, str]:
    client_id = Secrets.get("google_drive", "client_id")
    client_secret = Secrets.get("google_drive", "client_secret")
    if not client_id or not client_secret:
        raise ValueError("missing_client")
    return client_id, client_secret


@APP.post("/oauth/google/start")
def oauth_google_start(
    body: Optional[Dict[str, Any]] = Body(default=None),
    x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token"),
) -> Dict[str, Any]:
    _require_token(x_session_token)
    _prune_oauth_states()
    try:
        client_id, _ = _load_google_client()
    except ValueError:
        return {"error": "missing_client"}

    redirect_uri = "http://127.0.0.1:8765/oauth/google/callback"
    if isinstance(body, dict):
        candidate = str(body.get("redirect") or "").strip()
        if candidate:
            redirect_uri = candidate

    state = secrets.token_urlsafe(24)
    _OAUTH_STATES[state] = {
        "redirect": redirect_uri,
        "expires_at": time.time() + 600,
    }

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/drive.readonly",
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",
        "state": state,
    }
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return {"auth_url": auth_url, "state": state}


@APP.get("/oauth/google/callback")
def oauth_google_callback(code: str = "", state: str = "") -> RedirectResponse:
    if not code:
        raise HTTPException(status_code=400, detail="missing_code")
    if not state:
        raise HTTPException(status_code=400, detail="missing_state")

    _prune_oauth_states()
    meta = _OAUTH_STATES.pop(state, None)
    if not meta:
        raise HTTPException(status_code=400, detail="invalid_state")

    try:
        client_id, client_secret = _load_google_client()
    except ValueError:
        raise HTTPException(status_code=400, detail="missing_client") from None

    redirect_uri = str(meta.get("redirect") or "http://127.0.0.1:8765/oauth/google/callback")
    data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    try:
        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data=data,
            timeout=5,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:  # pragma: no cover - network failure path
        raise HTTPException(status_code=502, detail="oauth_exchange_failed") from exc

    refresh_token = payload.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="missing_refresh_token")

    try:
        Secrets.set("google_drive", "oauth_refresh", refresh_token)
    except SecretError as exc:
        raise HTTPException(status_code=500, detail="secret_store_error") from exc

    return RedirectResponse(url="/ui?connected=google_drive", status_code=302)


@APP.post("/oauth/google/revoke")
def oauth_google_revoke(
    x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token"),
) -> Dict[str, Any]:
    _require_token(x_session_token)
    token = Secrets.get("google_drive", "oauth_refresh")
    if token:
        try:
            requests.post(
                "https://oauth2.googleapis.com/revoke",
                data={"token": token},
                timeout=5,
            )
        except Exception:
            pass
        try:
            Secrets.delete("google_drive", "oauth_refresh")
        except SecretError:
            pass
    return {"ok": True}


@APP.get("/oauth/google/status")
def oauth_google_status(
    x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token"),
) -> Dict[str, Any]:
    _require_token(x_session_token)
    token = Secrets.get("google_drive", "oauth_refresh")
    connected = bool(token)
    return {"connected": connected}


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


__all__ = ["APP", "UI_STATIC_DIR", "build_app", "SESSION_TOKEN"]
