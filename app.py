"""Entry point for the workflow controller CLI."""

from __future__ import annotations

import argparse

from tgc.bootstrap import bootstrap_controller
from tgc.menu import run_cli
from tgc.organization import configure_profile_interactive
from tgc.master_index_controller import MasterIndexController
from tgc.util.serialization import safe_serialize


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
    args = parser.parse_args()

    if args.init_org:
        configure_profile_interactive()
        return

    controller = bootstrap_controller()

    if args.update:
        action_id = "0"
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
        snapshot = master.build_index_snapshot()
        print(safe_serialize(snapshot))
        return

    if args.action and not args.menu_only:
        action_id = args.action
        if action_id not in controller.actions:
            raise SystemExit(f"Unknown action '{action_id}'. Use --menu-only to list actions.")
        plan_text = controller.build_plan(action_id)
        print("=== PLAN ===")
        print(plan_text)
        result = controller.run_action(action_id, apply=args.apply)
        print("\n=== RESULT ===")
        print(result.summary())
        print(f"Reports stored in: {controller.reports_root}")
        return

    run_cli(controller)


if __name__ == "__main__":
    main()
