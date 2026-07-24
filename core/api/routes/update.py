# Copyright (C) 2025 BUS Core Authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import threading
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request

from core.auth.dependencies import require_permission
from core.auth.permissions import PERMISSION_UPDATES_CHECK, PERMISSION_UPDATES_STAGE
from core.config.writes import require_writes
from core.config.manager import (
    get_update_check_first_reported,
    load_config,
    set_update_check_first_reported,
)
from core.runtime.manifest_keys import active_manifest_public_keys
from core.services.update import UpdateResult, UpdateService
from core.services.update_stage import UpdateStageResult, UpdateStageService
from core.version import VERSION as CURRENT_VERSION
from core.telemetry import emit_telemetry
from tgc.security import require_token_ctx

router = APIRouter()


def get_update_service() -> UpdateService:
    return UpdateService(trusted_manifest_public_keys=active_manifest_public_keys())


def _read_first_reported() -> bool:
    try:
        return get_update_check_first_reported()
    except Exception:
        # A local-state read failure must never block the update check. Treat as
        # already-reported so we do not risk inflating first_check on flaky IO.
        return True


def _record_first_reported() -> None:
    try:
        set_update_check_first_reported(True)
    except Exception:
        # Persisting the flag is best-effort; a failure here must not surface.
        pass


def get_update_stage_update_service() -> UpdateService:
    return UpdateService(
        trusted_manifest_public_keys=active_manifest_public_keys(),
        require_signed_manifest=True,
    )


def get_update_stage_service() -> UpdateStageService:
    return UpdateStageService(update_service=get_update_stage_update_service())


def _result_payload(result: UpdateResult) -> dict[str, object | None]:
    return {
        "current_version": result.current_version,
        "latest_version": result.latest_version,
        "update_available": result.update_available,
        "download_url": result.download_url,
        "error_code": result.error_code,
        "error_message": result.error_message,
    }


def _check_payload(
    result: UpdateResult,
    *,
    source: str,
    performed: bool,
    skip_reason: str | None = None,
) -> dict[str, object | None]:
    return {
        **_result_payload(result),
        "check_source": source,
        "check_performed": performed,
        "skip_reason": skip_reason,
    }


def _neutral_result() -> UpdateResult:
    return UpdateResult(
        current_version=CURRENT_VERSION,
        latest_version=None,
        update_available=False,
        download_url=None,
        error_code=None,
        error_message=None,
    )


def _run_update_check(source: str) -> dict[str, object | None]:
    emit_telemetry(f"update_check_{source}", deduplicate=False)
    try:
        cfg = load_config().updates
        first_check = not _read_first_reported()
        try:
            result = get_update_service().check(
                manifest_url=cfg.manifest_url,
                channel=cfg.channel,
                first_check=first_check,
            )
        finally:
            # This remains an installation-level first-check flag. It is not
            # reset for a new app version.
            if first_check:
                _record_first_reported()
        if result.error_code:
            emit_telemetry("update_failure", deduplicate=False)
        return _check_payload(result, source=source, performed=True)
    except Exception:
        emit_telemetry("update_failure", deduplicate=False)
        return _check_payload(
            UpdateResult(
                current_version=CURRENT_VERSION,
                latest_version=None,
                update_available=False,
                download_url=None,
                error_code="update_check_failed",
                error_message="Update check failed.",
            ),
            source=source,
            performed=True,
        )


def _startup_check_lock(request: Request) -> threading.Lock:
    lock = getattr(request.app.state, "startup_update_check_lock", None)
    if lock is None:
        lock = threading.Lock()
        request.app.state.startup_update_check_lock = lock
    return lock


def _stage_payload(result: UpdateStageResult) -> dict[str, object | None]:
    return {
        "ok": result.ok,
        "status": result.status,
        "current_version": result.current_version,
        "latest_version": result.latest_version,
        "exe_path": result.exe_path,
        "restart_available": result.restart_available,
        "error_code": result.error_code,
        "error_message": result.error_message,
    }


@router.get("/update/check")
def check_for_updates(
    request: Request,
    source: Literal["startup", "manual"] = Query("manual"),
) -> dict[str, object | None]:
    # Manual checks are always available. Startup checks are the one canonical
    # policy-controlled automatic path and execute at most once per app launch.
    if source == "manual":
        return _run_update_check(source)

    with _startup_check_lock(request):
        cached = getattr(request.app.state, "startup_update_check_result", None)
        if isinstance(cached, dict):
            return {
                **cached,
                "check_source": "startup",
                "check_performed": False,
                "skip_reason": "already_checked_this_launch",
            }
        result: dict[str, object | None] | None = None
        reason: str | None = None
        try:
            cfg = load_config().updates
        except Exception:
            result = _check_payload(
                UpdateResult(
                    current_version=CURRENT_VERSION,
                    latest_version=None,
                    update_available=False,
                    download_url=None,
                    error_code="update_config_unavailable",
                    error_message="Update configuration is unavailable.",
                ),
                source="startup",
                performed=False,
                skip_reason="update_config_unavailable",
            )
        else:
            if not cfg.enabled:
                reason = "updates_disabled"
            elif not cfg.check_on_startup:
                reason = "startup_check_disabled"
        if result is None:
            if reason is None:
                result = _run_update_check("startup")
            else:
                result = _check_payload(
                    _neutral_result(),
                    source="startup",
                    performed=False,
                    skip_reason=reason,
                )
        request.app.state.startup_update_check_result = dict(result)
        return result


@router.post("/update/stage")
def stage_update(
    _permission=Depends(require_permission(PERMISSION_UPDATES_STAGE)),
    _token: None = Depends(require_token_ctx),
    _writes: None = Depends(require_writes),
) -> dict[str, object | None]:
    try:
        result = get_update_stage_service().stage_from_config()
        emit_telemetry("update_staged" if result.ok else "update_failure", deduplicate=False)
        return _stage_payload(result)
    except Exception:
        emit_telemetry("update_failure", deduplicate=False)
        return _stage_payload(
            UpdateStageResult(
                ok=False,
                status="failed",
                current_version=CURRENT_VERSION,
                latest_version=None,
                exe_path=None,
                restart_available=False,
                error_code="update_stage_failed",
                error_message="Update staging failed.",
            )
        )
