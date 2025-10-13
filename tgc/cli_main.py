"""Alpha Core CLI entrypoints."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from typing import Dict, List, Optional

from core.bus.models import CommandContext
from core.conn_broker import ConnectionBroker
from core.plugins_alpha import discover_alpha_plugins as _discover_alpha_plugins
from tgc.bootstrap import bootstrap_controller


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


def _print_status(output, run_id: str, services: Dict[str, dict], plugins: List[str], effective: Dict[str, object]):
    ok = sum(1 for v in services.values() if isinstance(v, dict) and v.get("ok"))
    total = len(services)
    output(
        f"[run:{run_id}] mode=alpha fast={bool(effective.get('fast'))} "
        f"timeout_sec={effective.get('timeout_sec')} max_files={effective.get('max_files')} "
        f"max_pages={effective.get('max_pages')} page_size={effective.get('page_size')}"
    )
    output(f"Services: {ok}/{total} reachable")
    for service, result in sorted(services.items()):
        badge = "OK" if isinstance(result, dict) and result.get("ok") else "FAIL"
        detail = ""
        if isinstance(result, dict):
            info = result.get("detail")
            if info:
                detail = f" ({info})"
        output(f"  - {service}: {badge}{detail}")
    output(f"Plugins enabled: {len(plugins)}")
    for plugin in sorted(plugins):
        output(f"  - {plugin}")


def _start_full_crawl(context: CommandContext, effective_options: Dict[str, object]):
    from tgc.master_index_controller import run_master_index as _run_master_index

    context.options.update({k: v for k, v in effective_options.items() if v is not None or k == "fast"})
    return _run_master_index(context, options=effective_options)


def alpha_boot(args):
    output = print
    controller = bootstrap_controller()
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    context = _mk_context(controller, run_id, dry_run=bool(getattr(args, "dry_run", False)))
    broker = ConnectionBroker(controller)
    context.extras["conn_broker"] = broker

    plugins_instances = _discover_alpha_plugins()
    plugin_names = [getattr(plugin, "name", getattr(plugin, "id", "plugin")) for plugin in plugins_instances]

    services: Dict[str, dict] = {}
    for plugin in plugins_instances:
        try:
            description = plugin.describe() or {}
        except Exception as exc:
            services[f"plugin:{getattr(plugin, 'id', 'unknown')}"] = {"ok": False, "detail": str(exc)}
            continue
        for svc in description.get("services", []):
            if svc not in services:
                services[svc] = broker.probe(svc)
        try:
            plugin.probe(broker)
        except Exception as exc:
            services[f"plugin:{getattr(plugin, 'id', 'unknown')}"] = {"ok": False, "detail": str(exc)}

    effective = _effective_config(args)
    _print_status(output, run_id, services, plugin_names, effective)

    if getattr(args, "json", False):
        summary = {
            "run_id": run_id,
            "mode": "alpha",
            "services": services,
            "plugins": plugin_names,
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Alpha Core controller")
    subparsers = parser.add_subparsers(dest="command")
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
