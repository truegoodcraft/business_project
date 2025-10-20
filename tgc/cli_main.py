"""Alpha Core CLI entrypoints."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import UTC, datetime
from typing import Dict, List, Optional

from core.bus.models import CommandContext
from core.domain.broker import Broker
from core.capabilities import registry
from core.plugins_alpha import discover_alpha_plugins as _discover_alpha_plugins
from core.secrets import Secrets
from core.settings.reader import load_reader_settings
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


def _start_full_crawl(context: CommandContext, effective_options: Dict[str, object]):
    from tgc.master_index_controller import run_master_index as _run_master_index

    context.options.update({k: v for k, v in effective_options.items() if v is not None or k == "fast"})
    return _run_master_index(context, options=effective_options)


def serve_cmd(args):
    from core.api.http import LICENSE_NAME, LICENSE_URL, build_app
    import uvicorn

    app, token = build_app()
    host = "127.0.0.1"
    port = int(getattr(args, "port", 8765) or 8765)
    print(f"Serving on http://{host}:{port}")
    print(f"Session token (also saved to data/session_token.txt): {token}")
    print(
        f"License: {LICENSE_NAME} — {LICENSE_URL} — commercial use requires permission (Truegoodcraft@gmail.com)"
    )
    uvicorn.run(app, host=host, port=port, log_level="warning")


def _wire_serve(subparsers):
    parser = subparsers.add_parser("serve", help="Start Alpha Core HTTP server on localhost")
    parser.add_argument("--port", type=int, default=8765)
    parser.set_defaults(func=serve_cmd)


def secrets_set_cmd(args):
    from core.secrets import Secrets, SecretError

    plugin = args.plugin
    key = args.key
    print(
        f"Enter secret value for {plugin}:{key} (input hidden not supported in PowerShell here):"
    )
    value = input().strip()
    try:
        Secrets.set(plugin, key, value)
        print("Saved.")
    except SecretError as e:
        print(f"Error: {e}")


def _wire_secrets(subparsers):
    sp = subparsers.add_parser("secrets", help="Manage local secrets (write-only)")
    sub = sp.add_subparsers()
    pset = sub.add_parser("set", help="Set a secret from stdin")
    pset.add_argument("--plugin", required=True)
    pset.add_argument("--key", required=True)
    pset.set_defaults(func=secrets_set_cmd)


def config_status_cmd(args):
    import json
    from core.config.tracker import snapshot

    print(json.dumps(snapshot(), indent=2))


def config_clear_cmd(args):
    import json
    from core.config.tracker import clear_secrets, clear_saved_data

    res = {}
    if args.what in ("secrets", "all"):
        res["secrets"] = clear_secrets()
    if args.what in ("data", "all"):
        res["data"] = clear_saved_data(keep_settings=True)
    print(json.dumps(res, indent=2))


def config_settings_ro_cmd(args):
    import json
    from core.config.tracker import set_settings_readonly

    print(json.dumps(set_settings_readonly(args.plugin, ro=not args.unlock), indent=2))


def _wire_config(subparsers):
    sp = subparsers.add_parser("config", help="Config transparency & maintenance")
    sub = sp.add_subparsers()
    p1 = sub.add_parser("status", help="Show managed paths & file sizes")
    p1.set_defaults(func=config_status_cmd)
    p2 = sub.add_parser("clear", help="Clear secrets and/or saved data")
    p2.add_argument("--what", choices=["secrets", "data", "all"], required=True)
    p2.set_defaults(func=config_clear_cmd)
    p3 = sub.add_parser("settings-ro", help="Toggle read-only on a plugin settings file")
    p3.add_argument("--plugin", required=True)
    p3.add_argument("--unlock", action="store_true")
    p3.set_defaults(func=config_settings_ro_cmd)


def alpha_boot(args):
    import os

    os.environ.setdefault("TGC_SHOW_INTEGRATION_HINTS", "0")
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
    broker = Broker(
        Secrets,
        lambda name: logging.getLogger(f"plugins.{name}" if name else "plugins"),
        registry,
        load_reader_settings,
    )
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
        try:
            if hasattr(plugin, "register_broker"):
                plugin.register_broker(broker)
        except Exception:
            logger.exception("alpha.plugin.register_failed", extra={"plugin": display_name})
            summary.update({"status": "ERROR", "note": "see log", "detail": "register_failed"})
            plugin_summaries.append(summary)
            continue
        service_results: Dict[str, Dict[str, object]] = {}
        for svc in services_list:
            if svc not in services:
                services[svc] = broker.probe(svc)
            service_results[svc] = services[svc]
        summary["services"] = service_results
        failing = [res for res in service_results.values() if not res.get("ok")]
        if failing:
            first = failing[0]
            summary.update(
                {
                    "status": "WARN" if first.get("detail") not in {"missing_credentials", "creds_path_missing"} else "ERROR",
                    "note": first.get("hint") or first.get("detail"),
                    "detail": first.get("detail"),
                }
            )
            logger.warning(
                "alpha.plugin.probe_status",
                extra={
                    "plugin": display_name,
                    "status": summary.get("status"),
                    "detail": summary.get("detail") or summary.get("note"),
                },
            )
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

    output(f"Plugins enabled: {len(plugin_names)}")
    for name in plugin_names:
        output(f"  - {name}")

    effective = _effective_config(args)

    output(f"[run:{run_id}] mode=alpha")

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

    if getattr(args, "serve", False):
        serve_cmd(args)
        return


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
    alpha.add_argument("--serve", action="store_true", help="After boot, start HTTP server on localhost")
    alpha.add_argument("--port", type=int, default=8765)
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
    _wire_serve(subparsers)
    _wire_secrets(subparsers)
    _wire_config(subparsers)
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


__all__ = ["alpha_boot", "build_parser", "main", "serve_cmd"]
