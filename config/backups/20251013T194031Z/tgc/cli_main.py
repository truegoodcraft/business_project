"""Lightweight CLI entrypoints for streamlined workflows."""

from __future__ import annotations

import os
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, List, Optional, Sequence

from core.action_cards.model import ActionCard, DiffEntry
from core.bus import command_bus
from core.bus.models import CommandContext
from tgc.bootstrap import bootstrap_controller
from tgc.util.serialization import safe_serialize
from tgc.util.stage import stage, stage_done

PromptFn = Callable[[str], str]
PrintFn = Callable[..., None]

_SAFE_RISKS = {"low", "info", "informational", "none"}


def _select_env_file(dev: bool) -> str:
    if not dev and os.getenv("TGC_ENV", "").strip().lower() != "dev":
        return os.getenv("TGC_ENV_FILE", ".env")
    candidate = os.getenv("TGC_DEV_ENV_FILE", "config/dev.env")
    if os.path.exists(candidate):
        return candidate
    return os.getenv("TGC_ENV_FILE", ".env")


def _build_context(controller, *, run_id: Optional[str] = None) -> CommandContext:
    if run_id is None:
        run_id = datetime.now(UTC).strftime("go_%Y%m%dT%H%M%SZ")
    return CommandContext(
        controller=controller,
        run_id=run_id,
        dry_run=False,
        limits={},
        options={},
        logger=None,
    )


def _is_destructive(card: ActionCard) -> bool:
    risk = (card.risk or "").strip().lower()
    if risk and risk not in _SAFE_RISKS:
        return True
    for entry in card.diff:
        if isinstance(entry, DiffEntry):
            if entry.after is None and entry.before is not None:
                return True
    return False


def _split_cards(cards: Sequence[ActionCard]) -> tuple[List[ActionCard], List[ActionCard]]:
    safe: List[ActionCard] = []
    confirm: List[ActionCard] = []
    for card in cards:
        (confirm if _is_destructive(card) else safe).append(card)
    return safe, confirm


def _print_card(card: ActionCard, output: PrintFn) -> None:
    output("\n--- Proposal Detail ---")
    output(f"ID: {card.id}")
    output(f"Kind: {card.kind}")
    output(f"Title: {card.title}")
    output(f"Plugin: {card.proposed_by_plugin}")
    output(f"Risk: {card.risk}")
    output(f"Summary: {card.summary}")
    if card.diff:
        output("Diffs:")
        for diff in card.diff:
            output(f"  - {diff.path}: {diff.before!r} → {diff.after!r}")
    if card.data:
        try:
            output("Data:")
            output(safe_serialize(card.data))
        except Exception:  # pragma: no cover - defensive
            output(str(card.data))


def _confirm_destructive(prompt: PromptFn, output: PrintFn, destructive: Sequence[ActionCard]) -> bool:
    if not destructive:
        return True
    output(f"{len(destructive)} destructive action(s) require confirmation.")
    answer = prompt("Type DELETE to confirm destructive operations: ").strip()
    if answer != "DELETE":
        output("Destructive operations cancelled.")
        return False
    pin = os.getenv("TGC_DELETE_PIN")
    if pin:
        entered = prompt("Enter PIN: ").strip()
        if entered != pin:
            output("Invalid PIN. Destructive operations aborted.")
            return False
    return True


def _format_menu(total: int, safe: int, confirm: int) -> str:
    return (
        f"Found {total} proposals ({safe} safe, {confirm} needs confirmation)\n"
        "[Enter]=Apply {safe} safe   (a)=Apply all   (v #)=View   (s)=Skip   (q)=Quit\n> "
    )


def _ensure_config_version(output: PrintFn) -> None:
    expected = os.getenv("TGC_CONFIG_VERSION")
    actual = os.getenv("CONFIG_VERSION")
    if expected and actual and expected != actual:
        output(
            "Configuration version mismatch detected. Run 'tgc upgrade --check' to review updates."
        )


def backup_config(*, output_fn: Optional[PrintFn] = None) -> str:
    """Create a zip backup of key configuration files."""

    output = output_fn or print
    timestamp = datetime.now(UTC).strftime("config_%Y%m%dT%H%M%SZ")
    backup_dir = Path("config/backups") / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    archive_path = backup_dir / "config.zip"
    targets = [
        Path(".env"),
        Path("organization_profile.json"),
        Path("config/plugins.json"),
    ]
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in targets:
            if path.exists():
                archive.write(path, arcname=path.name)
    output(f"Config backup written to {archive_path}")
    return str(archive_path)


def cmd_go(
    dev: bool = False,
    *,
    input_fn: Optional[PromptFn] = None,
    output_fn: Optional[PrintFn] = None,
) -> None:
    prompt = input_fn or input
    output = output_fn or print

    _ensure_config_version(output)

    env_file = _select_env_file(dev)
    step = stage("Bootstrap controller")
    controller = bootstrap_controller(env_file)
    stage_done(step)

    context = _build_context(controller)
    step = stage("Discover changes")
    findings = command_bus.discover(context)
    stage_done(step)

    step = stage("Plan proposals")
    cards = command_bus.plan(context, findings)
    stage_done(step)

    safe_cards, confirm_cards = _split_cards(cards)
    total = len(cards)
    safe_count = len(safe_cards)
    confirm_count = len(confirm_cards)

    while True:
        choice = prompt(_format_menu(total, safe_count, confirm_count)).strip().lower()
        if choice in {"", "\n"}:
            to_apply = list(safe_cards)
            break
        if choice == "a":
            if not _confirm_destructive(prompt, output, confirm_cards):
                return
            to_apply = list(cards)
            break
        if choice.startswith("v"):
            parts = choice.split()
            if len(parts) == 2 and parts[1].isdigit():
                idx = int(parts[1]) - 1
                if 0 <= idx < len(cards):
                    _print_card(cards[idx], output)
                    continue
            output("Use 'v #' to view a proposal (e.g. v 1).")
            continue
        if choice == "s":
            output("No proposals applied.")
            return
        if choice == "q":
            output("Aborted.")
            return
        output("Unknown selection. Use Enter, a, v #, s, or q.")

    if not to_apply:
        output("No safe proposals to apply.")
        return

    base_run_id = context.run_id
    for index, card in enumerate(to_apply, start=1):
        op_id = f"{base_run_id}-{index:02d}"
        context.run_id = op_id
        output(f"\nApplying {card.title} ({card.id})…")
        result = command_bus.apply(context, card.id)
        snapshot_path = result.data.get("snapshot") if isinstance(result.data, dict) else None
        output(f"op_id={op_id} snapshot={snapshot_path or 'n/a'}")
        if result.ok:
            output("✓ Applied")
        else:
            errs = "; ".join(result.errors) if result.errors else "Unknown error"
            output(f"✗ Failed: {errs}")

    output("\nAll requested proposals processed.")
