"""Entry point for the workflow controller CLI."""

from __future__ import annotations

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

import argparse
import logging
import sys
import time
import traceback
from typing import Dict, Optional

from tgc.actions.master_index import MasterIndexAction
from tgc.bootstrap import bootstrap_controller
from tgc.health import format_health_banner, format_health_table, system_health
from tgc.menu import run_cli
from tgc.organization import configure_profile_interactive
from tgc.master_index_controller import MasterIndexController, TraversalLimits
from tgc.util.serialization import safe_serialize

from core.audit import write_audit
from core.capabilities import meta as capability_meta
from core.plugin_manager import load_plugins
from core.runtime import generate_run_id, get_runtime_limits, run_capability, set_runtime_limits
from core.safelog import logger
from core.system_check import system_check as _system_check

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def _run_id() -> str:
    return generate_run_id()


def _limits() -> Dict[str, object]:
    return get_runtime_limits()


def run_cap(cap_name: str, **params):
    run_id = generate_run_id()
    plugin = "unknown"
    scopes: list[str] = []
    start = time.perf_counter()
    outcome = "success"
    try:
        meta = capability_meta(cap_name)
        plugin = str(meta.get("plugin", "unknown"))
        meta_scopes = meta.get("scopes") or []
        scopes = [str(scope) for scope in meta_scopes]
        return run_capability(cap_name, run_id=run_id, **params)
    except Exception:
        outcome = "failure"
        raise
    finally:
        duration_ms = (time.perf_counter() - start) * 1000.0
        try:
            write_audit(
                run_id=run_id,
                plugin=plugin,
                capability=cap_name,
                scopes=scopes,
                outcome=outcome,
                ms=duration_ms,
            )
        except Exception as audit_error:  # pragma: no cover - defensive
            logger.warning("Failed to write audit log: %s", audit_error)


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
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--quiet", action="store_true", help="Suppress informational logging")
    args = parser.parse_args()

    level = logging.INFO
    if args.debug:
        level = logging.DEBUG
    if args.quiet:
        level = logging.WARNING
    logging.getLogger().setLevel(level)

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
        master = MasterIndexController(controller)
        snapshot = master.build_index_snapshot(limits=traversal_limits)
        print(safe_serialize(snapshot))
        return

    if args.action and not args.menu_only:
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
