"""Entry point for the workflow controller CLI."""

from __future__ import annotations

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

import argparse
import logging
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Dict, Optional

from tgc.actions.master_index import MasterIndexAction
from tgc.bootstrap import bootstrap_controller
from tgc.health import format_health_banner, format_health_table, system_health
from tgc.menu import run_cli
from tgc.organization import configure_profile_interactive
from tgc.master_index_controller import MasterIndexController, TraversalLimits
from tgc.util.serialization import safe_serialize

from core import policy_engine
from core.audit import write_audit
from core.capabilities import REGISTRY, meta, resolve
from core.config import load_core_config, plugin_env_whitelist
from core.isolate import run_isolated
from core.permissions import require
from core.plugin_api import Context
from core.plugin_manager import load_plugins
from core.policy_log import log_policy
from core import retention
from core.runtime import get_runtime_limits, set_runtime_limits
from core.safelog import logger
from core.system_check import system_check as _system_check

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


POLICY_PLACEHOLDER = os.getenv("POLICY_PLACEHOLDER_ENABLED", "true").lower() == "true"  # logs only


def _policy_trace(raw_text: str, command: str, args: dict) -> None:
    if POLICY_PLACEHOLDER:
        dec = policy_engine.evaluate(raw_text, command, args)
        log_policy(raw_text, dec)


def _limits() -> Dict[str, object]:
    return get_runtime_limits()


def _format_capabilities_table() -> str:
    headers = ("Capability", "Plugin", "Scopes", "Network")
    rows = []
    for name in sorted(REGISTRY.keys()):
        info = REGISTRY[name]
        scopes = ", ".join(info.get("scopes") or [])
        network = str(bool(info.get("network", False))).lower()
        rows.append((name, info.get("plugin", ""), scopes, network))

    widths = [len(h) for h in headers]
    for row in rows:
        for idx, value in enumerate(row):
            widths[idx] = max(widths[idx], len(value))

    def _fmt(row: tuple[str, str, str, str]) -> str:
        return "  ".join(value.ljust(widths[idx]) for idx, value in enumerate(row))

    lines = [_fmt(headers), "  ".join("-" * w for w in widths)]
    lines.extend(_fmt(row) for row in rows)
    return "\n".join(lines)


def _write_capabilities_doc(table: str) -> None:
    docs_dir = Path("docs")
    docs_dir.mkdir(parents=True, exist_ok=True)
    path = docs_dir / "capabilities.md"
    content = "# Capabilities\n\n```\n" + table + "\n```\n"
    path.write_text(content, encoding="utf-8")


def run_cap(cap_name: str, **params):
    m = meta(cap_name)
    plugin = m["plugin"]
    scopes = m["scopes"]
    require(plugin, scopes)  # enforce consent

    # SAFE MODE: block networked capabilities if OFFLINE_SAFE_MODE=true and manifest marks network=true
    safe_mode = (os.getenv("OFFLINE_SAFE_MODE", "false").lower() == "true")
    if safe_mode and m.get("network", False):
        raise RuntimeError(f"SAFE MODE: capability '{cap_name}' requires network and is blocked.")

    run_id = time.strftime("%Y%m%dT%H%M%SZ")
    ctx = Context(run_id=run_id, config=load_core_config(), limits=_limits(), logger=logger)

    use_subproc = (os.getenv("PLUGIN_SUBPROCESS", "false").lower() == "true")
    timeout_s = int(os.getenv("PLUGIN_TIMEOUT_S", "60"))

    t0 = time.perf_counter()
    try:
        if use_subproc:
            payload = {"run_id": ctx.run_id, "limits": ctx.limits, "params": params}
            env_keys = plugin_env_whitelist(plugin)
            rc, out, err = run_isolated(plugin, cap_name, payload, env_keys, timeout_s=timeout_s)
            if rc != 0:
                write_audit(run_id, plugin, cap_name, scopes, "error", int((time.perf_counter()-t0)*1000), f"rc={rc}; {err[:300]}")
                raise RuntimeError(f"Plugin subprocess failed (rc={rc}): {err}")
            import json
            res = json.loads(out or "{}")
            ok = bool(res.get("ok"))
            data, notes = res.get("data"), res.get("notes")
            write_audit(run_id, plugin, cap_name, scopes, "ok" if ok else "error", int((time.perf_counter()-t0)*1000))
            return type("Result", (), {"ok": ok, "data": data, "notes": notes})
        else:
            fn = resolve(cap_name)
            res = fn(ctx, **params)
            write_audit(run_id, plugin, cap_name, scopes, "ok" if res.ok else "error", int((time.perf_counter()-t0)*1000))
            return res
    except Exception as e:
        write_audit(run_id, plugin, cap_name, scopes, "error", int((time.perf_counter()-t0)*1000), notes=str(e)[:300])
        raise


def system_check() -> None:
    _system_check()


def main() -> None:
    parser = argparse.ArgumentParser(description="Workflow controller")
    parser.add_argument("--menu-only", action="store_true", help="Always show the interactive menu")
    parser.add_argument("--action", help="Run a specific action ID without entering the menu")
    parser.add_argument("--apply", action="store_true", help="Apply changes when running --action")
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print a connector functionality report and exit",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run integration system checks and print a compact summary",
    )
    parser.add_argument(
        "--init-org",
        action="store_true",
        help="Interactively configure organization details and update the reference page",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Fetch the latest repository changes (use with --apply to run the pull)",
    )
    parser.add_argument(
        "--print-index",
        action="store_true",
        help="Build the Master Index in memory and print it as JSON",
    )
    parser.add_argument(
        "--max-seconds",
        type=float,
        help="Stop traversal after this many seconds",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        help="Stop traversal after collecting this many pages/files",
    )
    parser.add_argument(
        "--max-requests",
        type=int,
        help="Stop traversal after this many API requests",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        help="Stop traversal after this depth",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        help="Stop Sheets reads after this many rows",
    )
    parser.add_argument(
        "--prune-only",
        action="store_true",
        help="Prune old run artifacts and exit",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview retention deletions without removing files (use with --prune-only)",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--quiet", action="store_true", help="Suppress informational logging")
    parser.add_argument(
        "--debug-capabilities",
        action="store_true",
        help="Print capabilities registry details and exit",
    )
    args = parser.parse_args()

    level = logging.INFO
    if args.debug:
        level = logging.DEBUG
    if args.quiet:
        level = logging.WARNING
    logging.getLogger().setLevel(level)

    if args.prune_only:
        report = retention.prune_old_runs(
            dry_run=args.dry_run,
            verbose=True,
        )
        print(report.summary_line())
        if report.planned_prune_paths:
            targets = report.planned_prune_paths if args.dry_run else report.pruned_paths
            if not targets and args.dry_run:
                targets = report.planned_prune_paths
            if targets:
                label = "Would remove" if args.dry_run else "Removed"
                for path in targets:
                    print(f"- {label}: {path}")
        if report.planned_truncations:
            if args.dry_run:
                print(
                    f"- Would truncate logs to last {report.max_log_lines} lines: "
                    + ", ".join(str(path) for path in report.planned_truncations)
                )
            elif report.truncated_files:
                print(
                    f"- Truncated logs to last {report.max_log_lines} lines: "
                    + ", ".join(str(path) for path in report.truncated_files)
                )
        if report.errors:
            print("Errors encountered:")
            for message in report.errors:
                print(f"- {message}")
        if args.dry_run:
            print("Dry-run complete. No files were deleted.")
        return

    if args.init_org:
        configure_profile_interactive()
        return

    checks, _ = system_health()
    banner = format_health_banner(checks)
    if banner:
        print(banner)

    if args.check:
        print("> " + format_health_table(checks))
        return

    controller = bootstrap_controller()
    load_plugins()

    if args.debug_capabilities:
        table = _format_capabilities_table()
        print(table)
        _write_capabilities_doc(table)
        return

    def _positive(value: Optional[float]) -> Optional[float]:
        if value is None:
            return None
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        return numeric if numeric > 0 else None

    limit_kwargs: Dict[str, float | int] = {}
    runtime_limits: Dict[str, float | int] = {}
    seconds_value = _positive(args.max_seconds)
    if seconds_value is not None:
        limit_kwargs["max_seconds"] = seconds_value
        runtime_limits["max_seconds"] = seconds_value
    pages_value = _positive(args.max_pages)
    if pages_value is not None:
        limit_kwargs["max_pages"] = int(pages_value)
    requests_value = _positive(args.max_requests)
    if requests_value is not None:
        limit_kwargs["max_requests"] = int(requests_value)
    depth_value = _positive(args.max_depth)
    if depth_value is not None:
        limit_kwargs["max_depth"] = int(depth_value)
    rows_value = _positive(args.max_rows)
    if rows_value is not None:
        runtime_limits["max_rows"] = int(rows_value)
    controller.runtime_limits = runtime_limits
    set_runtime_limits(runtime_limits)
    traversal_limits = TraversalLimits(**limit_kwargs) if limit_kwargs else None

    if args.update:
        _policy_trace("cli flag: --update", command="update", args={"apply": bool(args.apply)})
        action_id = "U"
        plan_text = controller.build_plan(action_id)
        print("=== PLAN ===")
        print(plan_text)
        result = controller.run_action(action_id, apply=args.apply)
        print("\n=== RESULT ===")
        print(result.summary())
        print(f"Reports stored in: {controller.reports_root}")
        return

    if args.status:
        _policy_trace("cli flag: --status", command="status", args={})
        print("=== ORGANIZATION ===")
        for line in controller.organization_summary():
            print(f"- {line}")
        print()
        print("=== CONNECTOR STATUS ===")
        for entry in controller.adapter_status_report():
            implementation = "Implemented" if entry["implemented"] else "Placeholder"
            configuration = "Configured" if entry["configured"] else "Missing configuration"
            print(f"- {entry['key']}: {implementation} · {configuration}")
            notes = entry.get("notes")
            if notes:
                print(f"    notes: {notes}")
            capabilities = entry.get("capabilities") or []
            for capability in capabilities:
                print(f"    capability: {capability}")
            inventory = entry.get("inventory_access")
            if isinstance(inventory, dict):
                status = inventory.get("status")
                if status:
                    print(f"    inventory status: {status}")
                detail = inventory.get("detail")
                if detail:
                    print(f"      detail: {detail}")
                preview = inventory.get("preview_sample")
                if isinstance(preview, list):
                    print(f"      preview rows: {len(preview)}")
        print()
        return

    if args.print_index:
        _policy_trace("cli flag: --print-index", command="print-index", args=limit_kwargs)
        master = MasterIndexController(controller)
        snapshot = master.build_index_snapshot(limits=traversal_limits)
        print(safe_serialize(snapshot))
        return

    if args.action and not args.menu_only:
        _policy_trace(
            f"cli action: {args.action}",
            command="action",
            args={
                "action_id": args.action,
                "apply": bool(args.apply),
                "limits": limit_kwargs if limit_kwargs else None,
            },
        )
        action_id = args.action
        if action_id not in controller.actions:
            raise SystemExit(f"Unknown action '{action_id}'. Use --menu-only to list actions.")
        action_obj = controller.get_action(action_id)
        action_options = (
            dict(limit_kwargs)
            if limit_kwargs and isinstance(action_obj, MasterIndexAction)
            else None
        )
        plan_text = controller.build_plan(action_id)
        print("=== PLAN ===")
        print(plan_text)
        result = controller.run_action(action_id, apply=args.apply, options=action_options)
        print("\n=== RESULT ===")
        print(result.summary())
        print(f"Reports stored in: {controller.reports_root}")
        return

    _policy_trace("cli menu: run_cli", command="menu", args={})
    run_cli(controller)


def _run_main():
    return main()


if __name__ == "__main__":
    try:
        code = _run_main() or 0
        sys.exit(code)
    except SystemExit as e:
        print(f"[tgc] SystemExit: code={e.code}")
        raise
    except Exception:
        print("[tgc] Uncaught exception in top-level:")
        traceback.print_exc()
        sys.exit(1)
