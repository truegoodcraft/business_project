"""CLI menu for the workflow controller."""

from __future__ import annotations

from typing import Callable, Dict, Iterable, List, Optional

from core import brand, retention, unilog
from core.consent_cli import current_consents, grant_scopes, list_scopes, revoke_scopes
from core.menu_render import (
    render_controller_tools_menu,
    render_data_ops_menu,
    render_main_menu,
    render_status_plugins_overview,
)
from core.menu_spec import LEGACY_ACTIONS
from core.runtime_state import boot_sequence
from core.system_check import system_check as _plugin_system_check
from core.plugin_manager import CORE_VERSION
from core.plugins_hub import run_plugins_hub
from .controller import Controller
from .health import format_health_table, system_health
from .integration_support import service_account_email, sheets_share_hint
from .master_index_controller import MasterIndexController
from .util.serialization import safe_serialize


def _format_banner(*, debug: bool = False) -> str:
    title = f"{brand.NAME} — Controller Menu"
    if debug:
        title += " (debug)"
    return "\n".join([title, f"made by: {brand.VENDOR}"])


def _format_help_lines(*, debug: bool = False) -> Iterable[str]:
    yield _format_banner(debug=debug)
    yield f"tagline: {brand.TAGLINE}"
    yield "Common flags: --quiet, --debug, --max-seconds, --max-items, --max-requests"
    yield "Press a number, letter action ID, or 'q' to quit."


def run_cli(controller: Controller, *, quiet: bool = False, debug: bool = False) -> None:
    """Display an interactive menu for manual operation."""

    if not quiet:
        print(_format_banner(debug=debug))
        print(f"tagline: {brand.TAGLINE}")
        print()

    org = controller.organization
    print(f"Organization: {org.display_name()}")
    if org.has_custom_short_code():
        print(f"Short code: {org.short_code} · SKU example: {org.sku_example()}")
    else:
        print("Short code: XXX (placeholder) · Run `python app.py --init-org` to customize.")
    print("Press a menu key to continue. Type '?' for help.\n")

    loop_index = 0
    while True:
        if loop_index:
            print()
        render_main_menu(quiet=True)
        choice = input().strip()
        loop_index += 1
        if choice == "?":
            for line in _format_help_lines(debug=debug):
                print(line)
            print()
            continue
        if choice.lower() in {"q", "quit", "exit"}:
            unilog.write("menu.main.select", None, choice="q")
            print("Goodbye!")
            return
        if choice in {"1", "2", "3", "4"}:
            unilog.write("menu.main.select", None, choice=choice)
            if choice == "1":
                status_payload = boot_sequence()
                render_status_plugins_overview(status_payload)
                input("Press Enter to return to the main menu...")
                continue
            if choice == "2":
                if _handle_data_operations(controller, debug=debug):
                    return
                continue
            if choice == "3":
                _open_plugins_hub(controller)
                continue
            if choice == "4":
                if _handle_controller_config(controller, debug=debug):
                    return
                continue
        if _dispatch_legacy(controller, choice):
            continue
        print("Invalid selection.")


def _dispatch_legacy(controller: Controller, input_key: str) -> bool:
    handler_name = LEGACY_ACTIONS.get(input_key)
    if not handler_name:
        return False
    handler = HANDLERS.get(handler_name)
    if handler is None:
        raise RuntimeError(f"Handler missing: {handler_name}")
    handler(controller)
    return True


DATA_OPS_ACTIONS: Dict[str, str] = {
    "12": "action_build_master_index",
    "15": "action_build_sheets_index",
    "2": "action_import_gmail",
    "3": "action_import_csv",
    "4": "action_sync_metrics",
    "5": "action_link_drive_pdfs",
    "6": "action_contacts_vendors",
}


CONTROLLER_TOOLS_ACTIONS: Dict[str, str] = {
    "1": "action_system_check",
    "2": "action_logs_reports",
    "3": "action_prune_old_runs",
    "4": "action_update_repo",
    "5": "action_manage_consents",
    "6": "action_about_versions",
}


def _prompt_mode() -> Optional[str]:
    while True:
        answer = input("Run mode [d=dry-run, a=apply, c=cancel]: ").strip().lower()
        if answer in {"d", "dry", "dry-run"}:
            return "dry"
        if answer in {"a", "apply"}:
            return "apply"
        if answer in {"c", "cancel"}:
            return None
        print("Invalid selection. Use d, a, or c.")


def _manage_plugin_scopes(_: Controller) -> None:
    def _format_scope_list(values: List[str]) -> str:
        return ", ".join(values) if values else "(none)"

    def _parse_scopes(raw: str) -> List[str]:
        return [scope for scope in raw.replace(",", " ").split() if scope]

    while True:
        available = list_scopes()
        granted = current_consents()
        if not available:
            print("No capabilities are registered; nothing to manage.")
        else:
            print("Current plugin consent state:")
            for plugin in sorted(available):
                granted_scopes = granted.get(plugin, [])
                print(
                    f"- {plugin}: granted {_format_scope_list(granted_scopes)} | "
                    f"available {_format_scope_list(available[plugin])}"
                )
        action = input("Choose action [g=grant, r=revoke, v=view, q=quit]: ").strip().lower()
        if action in {"q", "quit"}:
            break
        if action in {"v", "view", ""}:
            continue
        if action in {"g", "grant"}:
            plugin = input("Plugin to grant scopes for: ").strip()
            if plugin not in available:
                print(f"Unknown plugin '{plugin}'.")
                continue
            print(
                "Available scopes: "
                + _format_scope_list(available.get(plugin, []))
            )
            scope_input = input("Scopes to grant (comma or space separated): ").strip()
            scopes = _parse_scopes(scope_input)
            if not scopes:
                print("No scopes provided.")
                continue
            grant_scopes(plugin, scopes)
            print(f"Granted scopes {', '.join(scopes)} to {plugin}.")
            continue
        if action in {"r", "revoke"}:
            plugin = input("Plugin to revoke scopes from: ").strip()
            plugin_granted = granted.get(plugin, [])
            if not plugin_granted:
                print(f"No granted scopes recorded for '{plugin}'.")
                continue
            print("Granted scopes: " + _format_scope_list(plugin_granted))
            scope_input = input("Scopes to revoke (comma or space separated): ").strip()
            scopes = _parse_scopes(scope_input)
            if not scopes:
                print("No scopes provided.")
                continue
            revoke_scopes(plugin, scopes)
            print(f"Revoked scopes {', '.join(scopes)} from {plugin}.")
            continue
        print("Invalid selection. Use g, r, v, or q.")


def _open_plugins_hub(_: Controller) -> None:
    run_plugins_hub()


def _handle_data_operations(controller: Controller, *, debug: bool = False) -> bool:
    while True:
        render_data_ops_menu()
        sub_choice = input().strip()
        if sub_choice == "?":
            for line in _format_help_lines(debug=debug):
                print(line)
            print()
            continue
        if sub_choice.lower() in {"q", "quit", "exit"}:
            unilog.write("menu.main.select", None, choice="q")
            print("Goodbye!")
            return True
        if sub_choice.lower() == "b":
            break
        if not sub_choice:
            print("Invalid selection.")
            continue
        unilog.write("menu.sub.select", None, submenu="data_ops", choice=sub_choice)
        handler_name = DATA_OPS_ACTIONS.get(sub_choice)
        if not handler_name:
            print("Invalid selection.")
            continue
        handler = HANDLERS.get(handler_name)
        if handler is None:
            print(f"Handler missing: {handler_name}")
            continue
        try:
            handler(controller)
        except RuntimeError as exc:
            print(str(exc))
    return False


def _handle_controller_config(controller: Controller, *, debug: bool = False) -> bool:
    while True:
        render_controller_tools_menu()
        sub_choice = input().strip()
        if sub_choice == "?":
            for line in _format_help_lines(debug=debug):
                print(line)
            print()
            continue
        if sub_choice.lower() in {"q", "quit", "exit"}:
            unilog.write("menu.main.select", None, choice="q")
            print("Goodbye!")
            return True
        if sub_choice.lower() == "b":
            break
        handler_name = CONTROLLER_TOOLS_ACTIONS.get(sub_choice)
        if not handler_name:
            print("Invalid selection.")
            continue
        handler = HANDLERS.get(handler_name)
        if handler is None:
            print(f"Handler missing: {handler_name}")
            continue
        try:
            handler(controller)
        except RuntimeError as exc:
            print(str(exc))
    return False


def _prune_old_runs(_: Controller) -> None:
    while True:
        answer = input("Preview only? (y/n): ").strip().lower()
        if answer in {"", "y", "yes"}:
            dry_run = True
            break
        if answer in {"n", "no"}:
            dry_run = False
            break
        print("Invalid selection. Use y or n.")

    report = retention.prune_old_runs(dry_run=dry_run, verbose=True)
    print(report.summary_line())

    paths = report.planned_prune_paths if dry_run else report.pruned_paths
    if dry_run and not paths:
        paths = report.planned_prune_paths
    if paths:
        label = "Would remove" if dry_run else "Removed"
        for path in paths:
            print(f"- {label}: {path}")

    if report.planned_truncations:
        if dry_run:
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

    if dry_run:
        print("Dry-run complete. No files were deleted.")


def _print_master_index_snapshot(controller: Controller) -> None:
    master = MasterIndexController(controller)
    snapshot = master.build_index_snapshot()
    print(safe_serialize(snapshot))


def _run_system_check(_: Controller) -> None:
    _plugin_system_check()
    checks, _ = system_health()
    print(format_health_table(checks))


def _inspect_sheets_debug(controller: Controller) -> None:
    adapter = controller.adapters.get("sheets")
    if adapter is None:
        print("Sheets adapter is not available.")
        return
    is_configured = getattr(adapter, "is_configured", lambda: False)
    if not is_configured():
        message = getattr(adapter, "missing_configuration_message", lambda: None)()
        if message:
            print(message)
        else:
            print("Sheets adapter is not configured.")
        return
    try:
        metadata = getattr(adapter, "inventory_metadata")()
    except Exception as exc:
        print(f"Failed to load spreadsheet metadata: {exc}")
        hint = _sheets_share_message(controller, adapter)
        if hint:
            print(hint)
        return
    title = metadata.get("title") or "(untitled)"
    spreadsheet_id = metadata.get("spreadsheetId")
    print(f"Spreadsheet: {title} ({spreadsheet_id})")
    sheets = metadata.get("sheets")
    if isinstance(sheets, Iterable):
        rows: List[str] = []
        for entry in sheets:
            if not isinstance(entry, dict):
                continue
            sheet_name = entry.get("title") or "(untitled)"
            dims: List[str] = []
            if isinstance(entry.get("rowCount"), int):
                dims.append(f"rows={entry['rowCount']}")
            if isinstance(entry.get("columnCount"), int):
                dims.append(f"cols={entry['columnCount']}")
            suffix = f" ({', '.join(dims)})" if dims else ""
            rows.append(f"- {sheet_name}{suffix}")
        if rows:
            print("Tabs:")
            for line in rows:
                print(line)
        else:
            print("Tabs: none visible")
    else:
        print("Tabs: unavailable")

    limits = dict(getattr(controller, "runtime_limits", {}) or {})
    max_rows = limits.get("max_rows")
    if not isinstance(max_rows, int) or max_rows <= 0:
        max_rows = 10
        limits["max_rows"] = max_rows
    try:
        preview = getattr(adapter, "read_inventory_preview")(max_rows=max_rows, limits=limits)
    except Exception as exc:
        print(f"Failed to read preview: {exc}")
        hint = _sheets_share_message(controller, adapter)
        if hint:
            print(hint)
        return
    values = preview.get("values")
    if not isinstance(values, list):
        print("No preview values returned.")
    else:
        print(f"Preview ({len(values)} row(s)):")
        for row in values:
            cells = [str(cell) for cell in row] if isinstance(row, list) else [str(row)]
            print(" | ".join(cells))
    if preview.get("truncated"):
        reason = preview.get("reason") or "limit"
        print(f"… truncated due to {reason}.")


def _sheets_share_message(controller: Controller, adapter: object) -> Optional[str]:
    email: Optional[str] = None
    if hasattr(adapter, "service_account_email"):
        try:
            email = adapter.service_account_email()  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover - defensive
            email = None
    if not email:
        drive_module = controller.get_module("drive")
        drive_config = getattr(drive_module, "config", None)
        if drive_config is not None:
            try:
                email = service_account_email(drive_config)  # type: ignore[arg-type]
            except Exception:  # pragma: no cover - defensive
                email = None
    return sheets_share_hint(email)


def _run_controller_action(controller: Controller, action_id: str) -> None:
    if action_id not in controller.actions:
        print("Action not available. Try another selection.")
        return
    plan_text = controller.build_plan(action_id)
    print("\n=== PLAN ===")
    print(plan_text)
    mode = _prompt_mode()
    if mode is None:
        print("Cancelled.\n")
        return
    apply = mode == "apply"
    result = controller.run_action(action_id, apply=apply)
    print("\n=== RESULT ===")
    print(result.summary())
    print(f"Reports stored in: {controller.reports_root}\n")


def action_system_check(controller: Controller) -> None:
    _run_system_check(controller)


def action_discover_audit(controller: Controller) -> None:
    _run_controller_action(controller, "1")


def action_plugins_hub(controller: Controller) -> None:
    _open_plugins_hub(controller)


def action_build_master_index(controller: Controller) -> None:
    _run_controller_action(controller, "12")


def action_build_sheets_index(controller: Controller) -> None:
    _inspect_sheets_debug(controller)


def action_import_gmail(controller: Controller) -> None:
    _run_controller_action(controller, "2")


def action_import_csv(controller: Controller) -> None:
    _run_controller_action(controller, "3")


def action_sync_metrics(controller: Controller) -> None:
    _run_controller_action(controller, "4")


def action_link_drive_pdfs(controller: Controller) -> None:
    _run_controller_action(controller, "5")


def action_contacts_vendors(controller: Controller) -> None:
    _run_controller_action(controller, "6")


def action_wave(controller: Controller) -> None:
    _run_controller_action(controller, "9")


def action_settings_ids(controller: Controller) -> None:
    _run_controller_action(controller, "7")


def action_logs_reports(controller: Controller) -> None:
    _run_controller_action(controller, "8")


def action_update_repo(controller: Controller) -> None:
    _run_controller_action(controller, "U")


def action_prune_old_runs(controller: Controller) -> None:
    _prune_old_runs(controller)


def action_manage_consents(controller: Controller) -> None:
    _manage_plugin_scopes(controller)


def action_about_versions(controller: Controller) -> None:
    status_payload = boot_sequence()
    core_block = status_payload.get("core", {}) or {}
    plugin_block = status_payload.get("plugins", {}) or {}
    summary = plugin_block.get("summary", {}) or {}
    items = plugin_block.get("items", []) or []

    print(f"{brand.NAME} core version: {CORE_VERSION}")
    ready_flag = bool(core_block.get("ready"))
    print(f"Core ready: {ready_flag}")
    log_path = core_block.get("logging", {}).get("path")
    if log_path:
        print(f"Unified log path: {log_path}")
    print()

    total_plugins = summary.get("total", len(items))
    enabled_plugins = summary.get("enabled", total_plugins)
    ok_plugins = summary.get("ok", 0)
    print(
        "Plugins OK: {ok}/{enabled} (total discovered: {total})".format(
            ok=ok_plugins,
            enabled=enabled_plugins,
            total=total_plugins,
        )
    )
    if not items:
        print("No plugins discovered.")
    else:
        print("Discovered plugins:")
        for item in sorted(items, key=lambda it: str(it.get("name"))):
            name = item.get("name") or "(unknown)"
            version = item.get("version") or "?"
            enabled = "enabled" if item.get("enabled") else "disabled"
            health = (item.get("health", {}) or {}).get("status") or "unknown"
            print(f"- {name}@{version} — {enabled}, health={health}")
    print()
    print("Manage plugin configuration via option 3 (Plugins Hub).")


HANDLERS: Dict[str, Callable[[Controller], None]] = {
    "action_system_check": action_system_check,
    "action_discover_audit": action_discover_audit,
    "action_plugins_hub": action_plugins_hub,
    "action_build_master_index": action_build_master_index,
    "action_build_sheets_index": action_build_sheets_index,
    "action_import_gmail": action_import_gmail,
    "action_import_csv": action_import_csv,
    "action_sync_metrics": action_sync_metrics,
    "action_link_drive_pdfs": action_link_drive_pdfs,
    "action_contacts_vendors": action_contacts_vendors,
    "action_wave": action_wave,
    "action_settings_ids": action_settings_ids,
    "action_logs_reports": action_logs_reports,
    "action_update_repo": action_update_repo,
    "action_prune_old_runs": action_prune_old_runs,
    "action_manage_consents": action_manage_consents,
    "action_about_versions": action_about_versions,
}
