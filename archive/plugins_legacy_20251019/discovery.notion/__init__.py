"""Discovery plugin for Notion pages."""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional

from core.bus.models import ApplyResult, CommandContext, HealthStatus, RollbackResult
from tgc.master_index_controller import (
    MAX_NOTION_ITEMS,
    MasterIndexController,
    TraversalLimits,
    collect_notion_pages,
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
    if "fast" in text or "max pages" in text:
        return "fast limit hit"
    return reason


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

    discovery_options = getattr(ctx, "options", {}).get("discovery", {})
    limits_cfg = discovery_options.get("limits", {}) if isinstance(discovery_options, dict) else {}
    fast_mode = bool(limits_cfg.get("fast"))
    timeout_sec = limits_cfg.get("timeout_sec") if isinstance(limits_cfg, dict) else None
    max_pages = limits_cfg.get("max_pages") if isinstance(limits_cfg, dict) else None
    scope = "read_base" if fast_mode else "read_crawl"
    broker = ctx.extras.get("conn_broker") if isinstance(ctx.extras, dict) else None
    client_handle = broker.get_client("notion", scope=scope) if broker is not None else None
    notion_client = getattr(client_handle, "handle", None)
    traversal_limits = TraversalLimits(
        max_seconds=timeout_sec,
        max_pages=max_pages,
    )
    limit_value = max_pages if max_pages else None

    result = collect_notion_pages(
        notion_module,
        roots,
        max_depth=notion_module.config.max_depth,
        page_size=notion_module.config.page_size,
        limit=limit_value or MAX_NOTION_ITEMS,
        limits=traversal_limits,
        client=notion_client,
    )
    metadata["elapsed"] = time.perf_counter() - start
    metadata["partial"] = result.partial
    metadata["reason"] = result.reason
    metadata["limits"] = limits_cfg
    metadata["scope"] = scope
    if limit_value and len(result.records) >= limit_value:
        metadata["partial"] = True
        metadata["reason"] = metadata.get("reason") or f"Reached fast page limit ({limit_value})"
    if timeout_sec and not within_timeout(start, timeout_sec):
        if not metadata.get("partial"):
            metadata["partial"] = True
        metadata["reason"] = metadata.get("reason") or f"Timeout after {timeout_sec}s"
    if metadata.get("partial"):
        logger.warning(
            "discovery.notion.partial",
            extra={
                "count": len(result.records),
                "reason": metadata.get("reason"),
                "limits": limits_cfg,
            },
        )
    summary = f"Notion discovery: {len(result.records)} pages"
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
    return HealthStatus(ok=True, notes=["Notion discovery available"])
