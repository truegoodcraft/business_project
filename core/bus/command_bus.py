"""Command bus orchestration for the thin core."""

from __future__ import annotations

import importlib
import logging
import time
from typing import Dict, List, Tuple

from core.action_cards.planner import build_cards_from_findings
from core.audit import write_audit
from core.backup.snapshot import create_snapshot
from core.policy import approvals
from core.registry import plugins_json
from core.unilog import write as uni_write

from .models import ApplyResult, CommandContext, PluginFinding

_DISCOVERY_PLUGINS: Tuple[str, ...] = (
    "discovery.notion",
    "discovery.drive",
    "discovery.sheets",
)

_PLUGIN_MODULES: Dict[str, str] = {
    "discovery.notion": "plugins.discovery.notion",
    "discovery.drive": "plugins.discovery.drive",
    "discovery.sheets": "plugins.discovery.sheets",
    "writer.markdown": "plugins.writer.markdown",
}


def _load_plugin(name: str):
    module_path = _PLUGIN_MODULES.get(name)
    if module_path is None:
        raise KeyError(f"Unknown plugin '{name}'")
    return importlib.import_module(module_path)


def _normalise_finding(plugin: str, payload) -> PluginFinding:
    if isinstance(payload, PluginFinding):
        return payload
    records = []
    errors: List[str] = []
    metadata: Dict[str, object] = {}
    partial = False
    reason = None
    if isinstance(payload, dict):
        records = payload.get("records") or []
        errors = payload.get("errors") or []
        metadata = {
            key: value
            for key, value in payload.items()
            if key not in {"records", "errors", "partial", "reason"}
        }
        partial = bool(payload.get("partial"))
        reason = payload.get("reason")
    elif payload is None:
        records = []
    else:
        metadata["payload"] = payload
    if not isinstance(records, list):
        records = []
    if not isinstance(errors, list):
        errors = [str(errors)] if errors else []
    finding = PluginFinding(
        plugin=plugin,
        records=[dict(item) for item in records if isinstance(item, dict)],
        errors=[str(err) for err in errors],
        metadata=metadata,
        partial=partial,
        reason=str(reason) if reason else None,
    )
    return finding


def _finding_to_mapping(finding: PluginFinding) -> Dict[str, object]:
    payload = {
        "records": finding.records,
        "errors": finding.errors,
        "partial": finding.partial,
        "reason": finding.reason,
    }
    payload.update(finding.metadata)
    return payload


def discover(ctx: CommandContext) -> Dict[str, PluginFinding]:
    """Run all discovery plugins and aggregate findings."""

    logger = ctx.logger or logging.getLogger(__name__)
    findings: Dict[str, PluginFinding] = {}
    plugin_counts: Dict[str, int] = {}
    for plugin in _DISCOVERY_PLUGINS:
        if not plugins_json.enabled(plugin):
            uni_write("plugin.skipped_disabled", ctx.run_id, plugin=plugin)
            continue
        try:
            module = _load_plugin(plugin)
            discover_fn = getattr(module, "discover", None)
            if discover_fn is None:
                continue
            start = time.perf_counter()
            payload = discover_fn(ctx)
            elapsed_ms = int((time.perf_counter() - start) * 1000)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("discover.failed", extra={"plugin": plugin})
            finding = PluginFinding(plugin=plugin, records=[], errors=[str(exc)])
            elapsed_ms = 0
        else:
            finding = _normalise_finding(plugin, payload)
        findings[plugin] = finding
        plugin_counts[plugin] = finding.count()
        uni_write(
            "bus.discover.plugin",
            ctx.run_id,
            plugin=plugin,
            count=finding.count(),
            errors=len(finding.errors),
            ms=elapsed_ms,
        )
    ctx.findings = findings
    uni_write(
        "bus.discover.done",
        ctx.run_id,
        counts={name: count for name, count in plugin_counts.items()},
    )
    return findings


def plan(ctx: CommandContext, findings: Dict[str, PluginFinding]):
    """Convert findings into action cards."""

    mapping = {name: _finding_to_mapping(finding) for name, finding in findings.items()}
    cards = build_cards_from_findings(mapping)
    ctx.cards = {card.id: card for card in cards}
    uni_write("bus.plan.cards", ctx.run_id, count=len(cards))
    return cards


def _normalise_apply_result(payload) -> ApplyResult:
    if isinstance(payload, ApplyResult):
        return payload
    if isinstance(payload, dict):
        ok = bool(payload.get("ok"))
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        errors = payload.get("errors") or []
        notes = payload.get("notes") or []
        ms = int(payload.get("ms") or 0)
        return ApplyResult(ok=ok, data=data, errors=list(errors), notes=list(notes), ms=ms)
    if isinstance(payload, tuple) and payload:
        ok = bool(payload[0])
        return ApplyResult(ok=ok)
    return ApplyResult(ok=bool(payload))


def apply(ctx: CommandContext, card_id: str) -> ApplyResult:
    """Apply the action card by invoking the responsible plugin."""

    logger = ctx.logger or logging.getLogger(__name__)
    card = ctx.get_card(card_id)
    if card is None:
        return ApplyResult(ok=False, errors=[f"Unknown card {card_id}"])

    approval_token = approvals.request_approval(card)
    if approval_token is None or not approvals.can_apply(card):
        return ApplyResult(ok=False, errors=["Approval denied"])

    snapshot_path = create_snapshot(ctx.run_id)
    module_name = card.proposed_by_plugin
    try:
        module = _load_plugin(module_name)
        apply_fn = getattr(module, "apply", None)
        if apply_fn is None:
            return ApplyResult(ok=False, errors=["Plugin missing apply()"])
        start = time.perf_counter()
        payload = apply_fn(ctx, card_id, approval_token)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("apply.failed", extra={"card_id": card_id, "plugin": module_name})
        elapsed_ms = 0
        result = ApplyResult(ok=False, errors=[str(exc)])
    else:
        result = _normalise_apply_result(payload)
        if result.ms == 0:
            result.ms = elapsed_ms
        if snapshot_path and "snapshot" not in result.data:
            result.data.setdefault("snapshot", str(snapshot_path))
        if result.ok:
            card.state = "applied"
    write_audit(
        ctx.run_id,
        plugin=module_name,
        capability=card.kind,
        scopes=[card.kind],
        outcome="ok" if result.ok else "error",
        ms=result.ms,
        notes="; ".join(result.errors or result.notes),
    )
    uni_write(
        "bus.apply.result",
        ctx.run_id,
        card_id=card_id,
        ok=result.ok,
        ms=result.ms,
        errors=result.errors,
    )
    return result


def run_master_index(ctx: CommandContext):
    """Back-compat shim for the master index orchestration."""

    findings = discover(ctx)
    cards = plan(ctx, findings)
    results: List[Tuple[str, ApplyResult]] = []
    if not ctx.dry_run:
        for card in cards:
            if card.kind != "index.markdown":
                continue
            result = apply(ctx, card.id)
            results.append((card.id, result))
    ctx.extras["apply_results"] = results
    return {
        "findings": findings,
        "cards": cards,
        "apply_results": results,
    }
