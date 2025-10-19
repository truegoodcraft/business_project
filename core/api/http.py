from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Request, Response, APIRouter
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import requests

from core.capabilities import registry
from core.capabilities.registry import MANIFEST_PATH
from core.runtime.core_alpha import CoreAlpha
from core.runtime.policy import PolicyDecision
from core.runtime.probe import PROBE_TIMEOUT_SEC
from core.secrets import SecretError, Secrets
from core.version import VERSION
from tgc.bootstrap_fs import DATA, LOGS

from pydantic import BaseModel


def _load_session_token() -> str:
    return Path("data/session_token.txt").read_text(encoding="utf-8").strip()


def _b64u_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _b64u_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _mk_state() -> str:
    """
    Create a per-flow state: base64url(nonce . hmac_sha256(session_token, nonce))
    """

    nonce = secrets.token_urlsafe(16).encode()
    sig = hmac.new(_load_session_token().encode(), nonce, hashlib.sha256).digest()
    return _b64u_encode(nonce + b"." + sig)


def _check_state(state_b64: str) -> bool:
    try:
        blob = _b64u_decode(state_b64)
        nonce, sig = blob.split(b".", 1)
        expected = hmac.new(_load_session_token().encode(), nonce, hashlib.sha256).digest()
        return hmac.compare_digest(sig, expected)
    except Exception:
        return False


READER_SETTINGS_PATH = Path("data/settings_reader.json")


def _load_reader_settings() -> dict:
    if READER_SETTINGS_PATH.exists():
        try:
            return json.loads(READER_SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "enabled": {"drive": True, "local": True, "notion": False, "smb": False},
        "local_roots": [],
    }


def _save_reader_settings(settings: dict) -> None:
    READER_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    READER_SETTINGS_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")


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


def require_token_ctx(
    x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token"),
) -> Dict[str, Optional[str]]:
    _require_token(x_session_token)
    return {"token": x_session_token}


protected = APIRouter(dependencies=[Depends(require_token_ctx)])
oauth = APIRouter()


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


class GoogleStartIn(BaseModel):
    redirect: str | None = None


class GoogleSettingsIn(BaseModel):
    client_id: str | None = None
    client_secret: str | None = None


class GoogleSettingsOut(BaseModel):
    connected: bool
    has_client_id: bool
    client_id_mask: str | None
    has_client_secret: bool


def _mask_secret(value: Optional[str]) -> str | None:
    if not value:
        return None
    return "..." + value[-4:]


@protected.get("/settings/google", response_model=GoogleSettingsOut)
def settings_google_get(response: Response) -> GoogleSettingsOut:
    response.headers["Cache-Control"] = "no-store"

    client_id = Secrets.get("google_drive", "client_id") or ""
    client_secret = Secrets.get("google_drive", "client_secret") or ""
    refresh_token = Secrets.get("google_drive", "oauth_refresh") or ""

    has_client_id = bool(client_id)
    has_client_secret = bool(client_secret)
    connected = bool(refresh_token)

    return GoogleSettingsOut(
        connected=connected,
        has_client_id=has_client_id,
        client_id_mask=_mask_secret(client_id) if has_client_id else None,
        has_client_secret=has_client_secret,
    )


@protected.post("/settings/google")
def settings_google_post(
    payload: GoogleSettingsIn,
    response: Response,
) -> Dict[str, Any]:
    response.headers["Cache-Control"] = "no-store"

    updated: List[str] = []
    try:
        if payload.client_id is not None:
            Secrets.set("google_drive", "client_id", payload.client_id)
            updated.append("client_id")
        if payload.client_secret is not None:
            Secrets.set("google_drive", "client_secret", payload.client_secret)
            updated.append("client_secret")
    except SecretError as exc:
        raise HTTPException(status_code=500, detail="secret_store_error") from exc

    if updated:
        log(f"settings.google updated: fields={','.join(updated)}")

    return {"ok": True}


@protected.delete("/settings/google")
def settings_google_delete(response: Response) -> Dict[str, Any]:
    response.headers["Cache-Control"] = "no-store"

    for key in ("client_id", "client_secret", "oauth_refresh"):
        try:
            Secrets.delete("google_drive", key)
        except SecretError:
            continue

    log("settings.google cleared")
    return {"ok": True}


@protected.get("/settings/reader", response_model=None)
def get_reader_settings() -> Dict[str, Any]:
    return _load_reader_settings()


@protected.post("/settings/reader", response_model=None)
def post_reader_settings(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:  # type: ignore[assignment]
    current = _load_reader_settings()
    enabled_payload = current.get("enabled", {})
    local_roots_payload = current.get("local_roots", [])
    if isinstance(payload, dict):
        enabled_candidate = payload.get("enabled", enabled_payload)
        if isinstance(enabled_candidate, dict):
            enabled_payload = {str(k): bool(v) for k, v in enabled_candidate.items()}
        local_roots_candidate = payload.get("local_roots", local_roots_payload)
        if isinstance(local_roots_candidate, list):
            local_roots_payload = [str(item) for item in local_roots_candidate if isinstance(item, str)]
    settings_payload = {"enabled": enabled_payload, "local_roots": local_roots_payload}
    _save_reader_settings(settings_payload)
    return {"ok": True, "settings": settings_payload}


@oauth.post("/oauth/google/start", response_model=None)
def oauth_google_start(
    body: GoogleStartIn | None = Body(default=None),
    _ctx=Depends(require_token_ctx),
):
    _prune_oauth_states()
    payload = body or GoogleStartIn()
    try:
        client_id, _ = _load_google_client()
    except ValueError:
        error_response = JSONResponse({"error": "missing_client"}, status_code=400)
        error_response.headers["Cache-Control"] = "no-store"
        return error_response

    redirect_uri = "http://127.0.0.1:8765/oauth/google/callback"
    if payload.redirect:
        candidate = str(payload.redirect).strip()
        if candidate:
            redirect_uri = candidate

    state = _mk_state()
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
    response = JSONResponse({"auth_url": auth_url, "state": state})
    response.headers["Cache-Control"] = "no-store"
    return response


@oauth.get("/oauth/google/callback", response_model=None)
def oauth_google_callback(request: Request):
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    if not state or not _check_state(state):
        raise HTTPException(status_code=401, detail="Invalid session token")

    if not code:
        raise HTTPException(status_code=400, detail="Missing code")

    _prune_oauth_states()
    meta = _OAUTH_STATES.pop(state, None)
    if not meta:
        raise HTTPException(status_code=401, detail="Invalid session token")

    try:
        client_id, client_secret = _load_google_client()
    except ValueError:
        raise HTTPException(status_code=400, detail="missing_client") from None

    default_redirect = "http://127.0.0.1:8765/oauth/google/callback"
    redirect_uri = str(meta.get("redirect") or default_redirect)
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


@oauth.post("/oauth/google/revoke", response_model=None)
def oauth_google_revoke(_ctx=Depends(require_token_ctx)):
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
    response = JSONResponse({"ok": True})
    response.headers["Cache-Control"] = "no-store"
    return response


@oauth.get("/oauth/google/status", response_model=None)
def oauth_google_status(_ctx=Depends(require_token_ctx)):
    token = Secrets.get("google_drive", "oauth_refresh")
    connected = bool(token)
    response = JSONResponse({"connected": connected})
    response.headers["Cache-Control"] = "no-store"
    return response


@protected.get("/health")
def health() -> Dict[str, Any]:
    return _with_run_id({"ok": True, "version": VERSION})


@protected.get("/plugins")
def plugins() -> Dict[str, Any]:
    core = _require_core()
    out = core.plugin_list()
    return _with_run_id({"plugins": out})


def _get_plugin_by_id(service_id: str):
    try:
        from core.plugins.loader import get_plugin  # type: ignore
    except Exception:
        return None
    return get_plugin(service_id)


@protected.post("/plugins/{service_id}/read", response_model=None)
def plugin_read(service_id: str, body: Dict[str, Any] = Body(default={})):  # type: ignore[assignment]
    plugin = _get_plugin_by_id(service_id)
    if not plugin or not hasattr(plugin, "read"):
        raise HTTPException(status_code=404, detail="plugin or op not found")
    op = body.get("op") if isinstance(body, dict) else None
    params = body.get("params") if isinstance(body, dict) else None
    if not isinstance(params, dict):
        params = {}
    try:
        return plugin.read(op, params)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"read failed: {type(exc).__name__}") from exc


@protected.post("/probe")
def probe(
    body: Any = Body(default=None),
) -> Dict[str, Any]:
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
    if "reader" in services:
        plugin = _get_plugin_by_id("reader")
        if plugin and hasattr(plugin, "probe"):
            try:
                probe_result = plugin.probe()
            except Exception as exc:
                probe_result = {
                    "ok": False,
                    "detail": "probe_exception",
                    "error": type(exc).__name__,
                }
            results["reader"] = probe_result
            try:
                registry.update_from_probe(
                    "reader",
                    ["catalog.list", "catalog.search"],
                    probe_result,
                )
            except Exception:
                pass
    payload = {
        "bootstrap": core.bootstrap,
        "results": results,
        "probe_timeout_sec": PROBE_TIMEOUT_SEC,
    }
    return _with_run_id(payload)


@protected.get("/capabilities")
def get_capabilities() -> Dict[str, Any]:
    manifest = registry.emit_manifest_async()
    manifest.setdefault("license", {"core": LICENSE_NAME, "core_url": LICENSE_URL})
    return _with_run_id(manifest)


@protected.post("/execTransform")
def exec_transform(
    body: Dict[str, Any] = Body(...),
) -> Dict[str, Any]:
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


@protected.post("/policy.simulate")
def policy_simulate(
    body: Dict[str, Any] = Body(...),
) -> Dict[str, Any]:
    core = _require_core()
    intent = str(body.get("intent") or "").strip()
    metadata = body.get("metadata") or {}
    decision = core.policy.simulate(intent, metadata)
    payload = {
        "decision": decision.decision,
        "reasons": list(decision.reasons),
    }
    return _with_run_id(payload)


@protected.post("/nodes.manifest.sync")
def manifest_sync(
    body: Dict[str, Any] = Body(...),
) -> Dict[str, Any]:
    manifest = body.get("manifest")
    if not isinstance(manifest, dict):
        raise HTTPException(status_code=400, detail="invalid_manifest")
    if not registry.validate_signature(manifest):
        raise HTTPException(status_code=400, detail="signature_invalid")
    return _with_run_id({"ok": True})


@protected.get("/transparency.report")
def transparency_report() -> Dict[str, Any]:
    core = _require_core()
    report = core.transparency_report()
    report["manifest_path"] = str(MANIFEST_PATH)
    return _with_run_id(report)


@protected.get("/logs")
def logs() -> Dict[str, Any]:
    path = LOG_FILE or (LOGS / "core.log")
    if not path.exists():
        return _with_run_id({"logs": []})
    lines = path.read_text(encoding="utf-8").splitlines()[-200:]
    return _with_run_id({"logs": lines})


APP.include_router(oauth)
APP.include_router(protected)


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
