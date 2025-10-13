"""CLI menu for the workflow controller."""

from __future__ import annotations

from typing import Callable, Dict, Iterable, List, Optional

from core.consent_cli import current_consents, grant_scopes, list_scopes, revoke_scopes
from core.system_check import system_check as _plugin_system_check
from .controller import Controller
from .master_index_controller import MasterIndexController
from .health import format_health_table, system_health
from .integration_support import service_account_email, sheets_share_hint
from .util.serialization import safe_serialize


def run_cli(controller: Controller) -> None:
    """Display an interactive menu for manual operation."""

    print("True Good Craft — Controller Menu")
    org = controller.organization
    print(f"{org.display_name()} — Controller Menu")
    if org.has_custom_short_code():
        print(f"Short code: {org.short_code} · SKU example: {org.sku_example()}")
    else:
        print("Short code: XXX (placeholder) · Run `python app.py --init-org` to customize.")
    print("Type the menu number to continue, or 'q' to quit.\n")

    advanced_options: Dict[str, tuple[str, str, Callable[[Controller], None]]] = {
        "0": (
            "System Check",
            "Validate credentials and show READY/MISSING status",
            _run_system_check,
        ),
        "13": (
            "Print Master Index (debug)",
            "Build the Master Index snapshot and dump it as JSON",
            _print_master_index_snapshot,
        ),
        "14": (
            "Inspect Sheets (debug)",
            "List sheet tabs and read a limited preview",
            _inspect_sheets_debug,
        ),
        "15": (
            "Manage Plugin Scopes (grant/revoke/view)",
            "Review and update stored plugin consents",
            _manage_plugin_scopes,
        ),
    }

    while True:
        for key, (name, description, _) in advanced_options.items():
            print(f"{key}) {name} — {description}")
        for action in controller.available_actions():
            print(f"{action.id}) {action.name} — {action.description}")
        choice = input("Select an option (or q to quit): ").strip()
        if choice.lower() in {"q", "quit", "exit"}:
            print("Goodbye!")
            return
        if choice in advanced_options:
            name, _, handler = advanced_options[choice]
            print(f"\n=== {name.upper()} ===")
            handler(controller)
            print()
            continue
        if choice not in controller.actions:
            print("Invalid choice. Try again.\n")
            continue
        plan_text = controller.build_plan(choice)
        print("\n=== PLAN ===")
        print(plan_text)
        mode = _prompt_mode()
        if mode is None:
            print("Cancelled.\n")
            continue
        apply = mode == "apply"
        result = controller.run_action(choice, apply=apply)
        print("\n=== RESULT ===")
        print(result.summary())
        print(f"Reports stored in: {controller.reports_root}\n")


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
