"""Discovery plugin for Google Drive files."""

from __future__ import annotations

import time
from typing import Dict, List

from core.bus.models import ApplyResult, CommandContext, HealthStatus, RollbackResult
from tgc.master_index_controller import MasterIndexController, TraversalLimits, collect_drive_files


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
    limits = ctx.limits if isinstance(ctx.limits, TraversalLimits) else ctx.limits
    result = collect_drive_files(
        drive_module,
        roots,
        mime_whitelist=mime_whitelist,
        max_depth=drive_module.config.max_depth,
        page_size=drive_module.config.page_size,
        limits=limits,
    )
    metadata["elapsed"] = time.perf_counter() - start
    metadata["partial"] = result.partial
    metadata["reason"] = result.reason
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
