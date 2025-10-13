"""Alpha Core CLI entrypoints."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import UTC, datetime
from typing import Dict, List, Optional

from core.bus.models import CommandContext
from core.conn_broker import ConnectionBroker
from core.plugins_alpha import discover_alpha_plugins as _discover_alpha_plugins
from tgc.bootstrap import bootstrap_controller
from tgc.bootstrap_fs import ensure_first_run


logger = logging.getLogger(__name__)


def _mk_context(controller, run_id: str, *, dry_run: bool = False) -> CommandContext:
    return CommandContext(
        controller=controller,
        run_id=run_id,
        dry_run=dry_run,
        limits={},
        options={},
        logger=None,
    )


def _effective_config(args) -> Dict[str, object]:
    return {
        "fast": bool(getattr(args, "fast", False)),
        "timeout_sec": getattr(args, "timeout", None),
        "max_files": getattr(args, "max_files", None),
        "max_pages": getattr(args, "max_pages", None),
        "page_size": getattr(args, "page_size", None),
    }


def _plugin_display_name(plugin) -> str:
    plugin_id = getattr(plugin, "id", "")
    module_name = getattr(plugin.__class__, "__module__", "")
    if isinstance(plugin_id, str) and plugin_id.startswith("plugins"):
        return plugin_id
    if module_name:
        return module_name
    if plugin_id:
        return plugin_id
    return plugin.__class__.__name__


def _summarize_probe_result(result: object) -> Dict[str, Optional[str]]:
    summary: Dict[str, Optional[str]] = {"status": "OK", "note": None, "detail": None}
    if not isinstance(result, dict):
        summary.update({"status": "WARN", "note": "unexpected probe response"})
        return summary
    ok_value = result.get("ok")
    detail = str(result.get("detail", "") or "").strip()
    hint = str(result.get("hint", "") or "").strip() or None
    if ok_value in (True, None):
        summary.update({"detail": detail or None})
        return summary
    if detail in {"creds_path_missing", "missing_credentials", "client_unavailable"}:
        summary.update({"status": "ERROR", "note": "see log", "detail": detail or None})
        return summary
    if detail == "not_configured":
        note = "no SHEET_INVENTORY_ID" if hint and "SHEET_INVENTORY_ID" in hint else "not configured"
        summary.update({"status": "WARN", "note": note, "detail": detail})
        return summary
    note = hint or detail or None
    summary.update({"status": "WARN", "note": note, "detail": detail or None})
    return summary


def _start_full_crawl(context: CommandContext, effective_options: Dict[str, object]):
    from tgc.master_index_controller import run_master_index as _run_master_index

    context.options.update({k: v for k, v in effective_options.items() if v is not None or k == "fast"})
    return _run_master_index(context, options=effective_options)


def alpha_boot(args):
    output = print
    bootstrap = ensure_first_run()
    output("=== TGC Alpha Boot ===")
    parts = [
        f"env_created={bootstrap['env_created']}",
        f"creds_present={bootstrap['creds_present']}",
    ]
    if bootstrap.get("creds_project"):
        parts.append(f"project={bootstrap['creds_project']}")
    if bootstrap.get("creds_email"):
        parts.append(f"email={bootstrap['creds_email']}")
    output(f"Setup: {' '.join(parts)}")
    hint = bootstrap.get("hint")
    if hint:
        lines = str(hint).splitlines()
        if lines:
            output(f"Hint: {lines[0]}")
            indent = " " * len("Hint: ")
            for line in lines[1:]:
                output(f"{indent}{line}")
    controller = bootstrap_controller()
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    context = _mk_context(controller, run_id, dry_run=bool(getattr(args, "dry_run", False)))
    broker = ConnectionBroker(controller)
    context.extras["conn_broker"] = broker

    plugins_instances = _discover_alpha_plugins()
    plugin_names: List[str] = []
    plugin_summaries: List[Dict[str, object]] = []
    services: Dict[str, dict] = {}
    for plugin in plugins_instances:
        display_name = _plugin_display_name(plugin)
        plugin_names.append(display_name)
        summary: Dict[str, object] = {"plugin": display_name, "status": "OK", "note": None}
        try:
            description = plugin.describe() or {}
        except Exception:
            logger.exception("alpha.plugin.describe_failed", extra={"plugin": display_name})
            summary.update({"status": "ERROR", "note": "see log", "detail": "describe_failed"})
            plugin_summaries.append(summary)
            continue
        services_list = [svc for svc in description.get("services", []) if isinstance(svc, str)]
        pending_services = [svc for svc in services_list if svc not in services]
        try:
            probe_result = plugin.probe(broker)
        except Exception:
            logger.exception("alpha.plugin.probe_failed", extra={"plugin": display_name})
            summary.update({"status": "ERROR", "note": "see log", "detail": "probe_failed"})
            plugin_summaries.append(summary)
            continue
        probe_summary = _summarize_probe_result(probe_result)
        summary.update(probe_summary)
        if summary.get("status") != "OK":
            logger.warning(
                "alpha.plugin.probe_status",
                extra={
                    "plugin": display_name,
                    "status": summary.get("status"),
                    "detail": summary.get("detail") or summary.get("note"),
                },
            )
        if isinstance(probe_result, dict):
            summary["probe"] = probe_result
            service_name = probe_result.get("service")
            if isinstance(service_name, str) and service_name not in services:
                services[service_name] = probe_result
                if service_name in pending_services:
                    pending_services.remove(service_name)
        else:
            summary["probe"] = None
        for svc in pending_services:
            services[svc] = broker.probe(svc)
        plugin_summaries.append(summary)

    output("Services:")
    if plugin_summaries:
        for summary in plugin_summaries:
            line = f"  - {summary['plugin']}: {summary['status']}"
            note = summary.get("note")
            if note:
                line += f" ({note})"
            output(line)
    else:
        output("  - (no plugins discovered)")

    effective = _effective_config(args)

    if getattr(args, "json", False):
        summary = {
            "run_id": run_id,
            "mode": "alpha",
            "services": services,
            "plugins": plugin_names,
            "plugin_status": plugin_summaries,
            "effective": effective,
        }
        output(json.dumps(summary, indent=2, sort_keys=True))

    if getattr(args, "crawl", False):
        output("\nStarting full crawl/index...")
        _start_full_crawl(context, effective)


def _wire_alpha(subparsers):
    alpha = subparsers.add_parser("alpha", help="Alpha boot: setup, probe, list plugins; crawl only when requested")
    alpha.add_argument("--fast", action="store_true")
    alpha.add_argument("--crawl", action="store_true")
    alpha.add_argument("--timeout", type=int, default=None)
    alpha.add_argument("--max-files", type=int, default=None)
    alpha.add_argument("--max-pages", type=int, default=None)
    alpha.add_argument("--page-size", type=int, default=None)
    alpha.add_argument("--dry-run", action="store_true")
    alpha.add_argument("--json", action="store_true")
    alpha.set_defaults(func=alpha_boot)


def setup_cmd(args):
    status = ensure_first_run()
    print("Setup complete.")
    for key, value in status.items():
        print(f"  {key}: {value}")


def _wire_setup(subparsers):
    setup_parser = subparsers.add_parser(
        "setup", help="Create folders and .env, check credentials presence"
    )
    setup_parser.set_defaults(func=setup_cmd)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Alpha Core controller")
    subparsers = parser.add_subparsers(dest="command")
    _wire_setup(subparsers)
    _wire_alpha(subparsers)
    parser.set_defaults(func=alpha_boot)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 0
    result = func(args)
    return 0 if result is None else int(result)


__all__ = ["alpha_boot", "build_parser", "main"]
