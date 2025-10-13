"""CLI menu for the workflow controller."""

from __future__ import annotations

from typing import Callable, Dict, Iterable, List, Optional

from core import brand, retention
from core.consent_cli import current_consents, grant_scopes, list_scopes, revoke_scopes
from core.menu_render import render_root, render_submenu
from core.menu_spec import LEGACY_SHIMS, SUBMENUS
from core.system_check import system_check as _plugin_system_check
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
        render_root(quiet=True)
        choice = input().strip()
        loop_index += 1
        if choice == "?":
            for line in _format_help_lines(debug=debug):
                print(line)
            print()
            continue
        if choice.lower() in {"q", "quit", "exit"}:
            print("Goodbye!")
            return
        if _dispatch_legacy(controller, choice):
            continue
        if choice in SUBMENUS:
            while True:
                render_submenu(choice)
                sub_choice = input().strip()
                if sub_choice == "?":
                    for line in _format_help_lines(debug=debug):
                        print(line)
                    print()
                    continue
                if sub_choice.lower() in {"q", "quit", "exit"}:
                    print("Goodbye!")
                    return
                if sub_choice == "0":
                    break
                submenu_keys = {item_key for item_key, _label, _handler in SUBMENUS.get(choice, [])}
                if sub_choice in submenu_keys:
                    try:
                        _dispatch_by_path(controller, choice, sub_choice)
                    except RuntimeError as exc:
                        print(str(exc))
                    except KeyError:
                        print("Invalid selection.")
                else:
                    print("Invalid selection.")
        else:
            print("Invalid selection.")


def _dispatch_by_path(controller: Controller, section_key: str, item_key: str):
    items = SUBMENUS.get(section_key, [])
    for key, _label, handler_name in items:
        if key == item_key:
            handler = HANDLERS.get(handler_name)
            if handler is None:
                raise RuntimeError(f"Handler missing: {handler_name}")
            return handler(controller)
    raise KeyError(f"No such menu item {section_key}.{item_key}")


def _dispatch_legacy(controller: Controller, input_key: str) -> bool:
    mapping = LEGACY_SHIMS.get(input_key)
    if not mapping:
        return False
    section_key, item_key = mapping
    _dispatch_by_path(controller, section_key, item_key)
    return True


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
}
