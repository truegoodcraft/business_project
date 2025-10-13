"""Discovery plugin for Notion pages."""

from __future__ import annotations

import time
from typing import Dict, List

from core.bus.models import ApplyResult, CommandContext, HealthStatus, RollbackResult
from tgc.master_index_controller import MasterIndexController, TraversalLimits, collect_notion_pages


def discover(ctx: CommandContext) -> Dict[str, object]:
    controller = getattr(ctx, "controller", None)
    if controller is None:
        return {"records": [], "errors": ["controller unavailable"], "roots": []}

    master = MasterIndexController(controller)
    notion_module = master._notion_module()
    if notion_module is None:
        return {
            "records": [],
            "errors": ["Notion module unavailable"],
            "roots": [],
            "message": "Notion module unavailable",
        }

    roots = master._notion_root_ids(notion_module)
    ctx.extras.setdefault("notion_roots", roots)
    metadata: Dict[str, object] = {"roots": roots}

    start = time.perf_counter()
    if ctx.dry_run and roots:
        records = [
            {
                "title": f"(dry-run placeholder for root {root[:8]}…)",
                "page_id": root,
                "url": "",
                "parent": "/",
                "last_edited": "",
            }
            for root in roots
        ]
        metadata["elapsed"] = time.perf_counter() - start
        return {"records": records, "errors": [], **metadata}

    if not roots:
        metadata["elapsed"] = time.perf_counter() - start
        return {"records": [], "errors": [], **metadata}

    limits = ctx.limits if isinstance(ctx.limits, TraversalLimits) else ctx.limits
    result = collect_notion_pages(
        notion_module,
        roots,
        max_depth=notion_module.config.max_depth,
        page_size=notion_module.config.page_size,
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
    return HealthStatus(ok=True, notes=["Notion discovery available"])
