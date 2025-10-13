"""Discovery plugin for Google Drive files."""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional

from core.bus.models import ApplyResult, CommandContext, HealthStatus, RollbackResult
from tgc.master_index_controller import (
    MAX_DRIVE_ITEMS,
    MasterIndexController,
    TraversalLimits,
    collect_drive_files,
)
from tgc.util.watchdog import within_timeout


logger = logging.getLogger(__name__)


def _format_partial(reason: Optional[str]) -> str:
    if not reason:
        return "partial"
    text = reason.lower()
    if "max seconds" in text or "timeout" in text:
        digits = "".join(ch for ch in reason if ch.isdigit())
        return f"partial after {digits}s" if digits else "partial (time limit)"
    if "fast" in text or "max files" in text:
        return "fast limit hit"
    if "max pages" in text:
        return "fast limit hit"
    return reason


def discover(ctx: CommandContext) -> Dict[str, object]:
    controller = getattr(ctx, "controller", None)
    if controller is None:
        return {"records": [], "errors": ["controller unavailable"], "roots": []}

    master = MasterIndexController(controller)
    drive_module = master._drive_module()
    if drive_module is None:
        return {
            "records": [],
            "errors": ["Google Drive module unavailable"],
            "roots": [],
            "message": "Google Drive module unavailable",
        }

    roots = master._drive_root_ids(drive_module)
    ctx.extras.setdefault("drive_roots", roots)
    metadata: Dict[str, object] = {"roots": roots}

    discovery_options = getattr(ctx, "options", {}).get("discovery", {})
    limits_cfg = discovery_options.get("limits", {}) if isinstance(discovery_options, dict) else {}
    fast_mode = bool(limits_cfg.get("fast"))
    max_files = limits_cfg.get("max_files") if isinstance(limits_cfg, dict) else None
    timeout_sec = limits_cfg.get("timeout_sec") if isinstance(limits_cfg, dict) else None
    page_size_override = limits_cfg.get("page_size") if isinstance(limits_cfg, dict) else None
    traversal_limits = TraversalLimits(
        max_seconds=timeout_sec,
        max_pages=limits_cfg.get("max_pages") if isinstance(limits_cfg, dict) else None,
    )
    scope = "read_base" if fast_mode else "read_crawl"
    service_handle = None
    broker = ctx.extras.get("conn_broker") if isinstance(ctx.extras, dict) else None
    if broker is not None:
        service_handle = broker.get_client("drive", scope=scope)
    drive_service = getattr(service_handle, "handle", None)

    start = time.perf_counter()
    if ctx.dry_run and roots:
        records = [
            {
                "name": f"(dry-run placeholder for root {root[:8]}…)",
                "file_id": root,
                "path_or_link": "/",
                "mimeType": "",
                "modifiedTime": "",
                "size": "",
            }
            for root in roots
        ]
        metadata["elapsed"] = time.perf_counter() - start
        return {"records": records, "errors": [], **metadata}

    if not roots:
        metadata["elapsed"] = time.perf_counter() - start
        return {"records": [], "errors": [], **metadata}

    mime_whitelist = list(drive_module.config.mime_whitelist) or None
    limit_value = max_files if max_files else None
    page_size = page_size_override or drive_module.config.page_size
    result = collect_drive_files(
        drive_module,
        roots,
        mime_whitelist=mime_whitelist,
        max_depth=drive_module.config.max_depth,
        page_size=page_size,
        limit=limit_value or MAX_DRIVE_ITEMS,
        limits=traversal_limits,
        service=drive_service,
    )
    metadata["elapsed"] = time.perf_counter() - start
    metadata["partial"] = result.partial
    metadata["reason"] = result.reason
    metadata["limits"] = limits_cfg
    metadata["scope"] = scope
    if limit_value and len(result.records) >= limit_value:
        metadata["partial"] = True
        metadata["reason"] = metadata.get("reason") or f"Reached fast file limit ({limit_value})"
    if timeout_sec and not within_timeout(start, timeout_sec):
        if not metadata.get("partial"):
            metadata["partial"] = True
        metadata["reason"] = metadata.get("reason") or f"Timeout after {timeout_sec}s"
    if metadata.get("partial"):
        logger.warning(
            "discovery.drive.partial",
            extra={
                "count": len(result.records),
                "reason": metadata.get("reason"),
                "limits": limits_cfg,
            },
        )
    summary = f"Drive discovery: {len(result.records)} files"
    if metadata.get("partial"):
        summary += f" ({_format_partial(metadata.get('reason'))})"
    print(summary)
    return {
        "records": result.records,
        "errors": result.errors,
        **metadata,
    }


def propose(ctx: CommandContext, findings) -> List[Dict[str, object]]:  # pragma: no cover - optional hook
    _ = ctx, findings
    return []


def apply(ctx: CommandContext, card_id: str, approval_token: str) -> ApplyResult:
    _ = ctx, card_id, approval_token
    return ApplyResult(ok=True)


def rollback(ctx: CommandContext, op_id: str) -> RollbackResult:
    _ = ctx, op_id
    return RollbackResult(ok=True, notes=["Rollback not implemented for discovery plugins."])


def health(ctx: CommandContext) -> HealthStatus:
    _ = ctx
    return HealthStatus(ok=True, notes=["Drive discovery available"])
