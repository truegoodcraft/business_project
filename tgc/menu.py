"""CLI menu for the workflow controller."""

from __future__ import annotations

from typing import Callable, Dict, Optional

from .controller import Controller
from .master_index_controller import MasterIndexController
from .health import format_health_table, system_health
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
        )
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
            handler = advanced_options[choice][2]
            print("\n=== MASTER INDEX SNAPSHOT ===")
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


def _print_master_index_snapshot(controller: Controller) -> None:
    master = MasterIndexController(controller)
    snapshot = master.build_index_snapshot()
    print(safe_serialize(snapshot))


def _run_system_check(_: Controller) -> None:
    checks, _ = system_health()
    print(format_health_table(checks))
