"""Entry point for the True Good Craft controller CLI."""

from __future__ import annotations

import argparse

from tgc.bootstrap import bootstrap_controller
from tgc.menu import run_cli


def main() -> None:
    parser = argparse.ArgumentParser(description="True Good Craft controller")
    parser.add_argument("--menu-only", action="store_true", help="Always show the interactive menu")
    parser.add_argument("--action", help="Run a specific action ID without entering the menu")
    parser.add_argument("--apply", action="store_true", help="Apply changes when running --action")
    args = parser.parse_args()

    controller = bootstrap_controller()

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
