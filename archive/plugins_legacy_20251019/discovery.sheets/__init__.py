"""Discovery plugin placeholder for Sheets index data."""

from __future__ import annotations

from typing import Dict, List

from core.bus.models import ApplyResult, CommandContext, HealthStatus, RollbackResult


def discover(ctx: CommandContext) -> Dict[str, object]:
    roots = ctx.extras.get("drive_roots", [])
    return {
        "records": [],
        "errors": [],
        "roots": roots,
        "message": "Sheets discovery deferred to writer plugin",
    }


def propose(ctx: CommandContext, findings) -> List[Dict[str, object]]:  # pragma: no cover - optional hook
    _ = ctx, findings
    return []


def apply(ctx: CommandContext, card_id: str, approval_token: str) -> ApplyResult:
    _ = ctx, card_id, approval_token
    return ApplyResult(ok=True)


def rollback(ctx: CommandContext, op_id: str) -> RollbackResult:
    _ = ctx, op_id
    return RollbackResult(ok=True, notes=["Sheets discovery has no side effects."])


def health(ctx: CommandContext) -> HealthStatus:
    _ = ctx
    return HealthStatus(ok=True, notes=["Sheets discovery delegated to writer"]) 
