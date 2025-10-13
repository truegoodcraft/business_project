"""Lightweight CLI entrypoints for streamlined workflows."""

from __future__ import annotations

import os
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

from core.action_cards.model import ActionCard, DiffEntry
from core.bus import command_bus
from core.bus.models import CommandContext
from core.conn_broker import ConnectionBroker
from tgc.bootstrap import bootstrap_controller
from tgc.util.serialization import safe_serialize
from tgc.util.stage import stage, stage_done

PromptFn = Callable[[str], str]
PrintFn = Callable[..., None]

_SAFE_RISKS = {"low", "info", "informational", "none"}

_SERVICE_LABELS = {
    "drive": "Google Drive",
    "sheets": "Sheets",
    "notion": "Notion",
}


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


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return default


def _env_int(name: str, default: Optional[int]) -> Optional[int]:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value


def _normalise_limit(value: Optional[int]) -> Optional[int]:
    if value is None:
        return None
    if value <= 0:
        return None
    return value


def _resolve_discovery_limits(fast_mode: bool) -> Dict[str, Optional[int]]:
    max_files_default = 250 if fast_mode else None
    max_pages_default = 20 if fast_mode else None
    page_size_default = 100 if fast_mode else None
    timeout_default = 45 if fast_mode else None

    max_files = _normalise_limit(_env_int("DISCOVERY_MAX_FILES", max_files_default))
    max_pages = _normalise_limit(_env_int("NOTION_MAX_PAGES", max_pages_default))
    page_size = _normalise_limit(_env_int("DRIVE_PAGE_SIZE", page_size_default))
    timeout_sec = _env_int("DISCOVERY_TIMEOUT_SEC", timeout_default)
    timeout_sec = timeout_sec if timeout_sec and timeout_sec > 0 else None

    return {
        "fast": fast_mode,
        "max_files": max_files,
        "max_pages": max_pages,
        "page_size": page_size,
        "timeout_sec": timeout_sec,
    }


def _resolve_discovery_options(
    *, fast_flag: bool, disable_drive: bool, disable_notion: bool, disable_sheets: bool
) -> Dict[str, object]:
    fast_env = _env_bool("DISCOVERY_FAST", False)
    fast_mode = bool(fast_flag or fast_env)
    enabled = {
        "drive": _env_bool("DISCOVERY_DRIVE_ENABLED", True) and not disable_drive,
        "notion": _env_bool("DISCOVERY_NOTION_ENABLED", True) and not disable_notion,
        "sheets": _env_bool("DISCOVERY_SHEETS_ENABLED", True) and not disable_sheets,
    }
    limits = _resolve_discovery_limits(fast_mode)
    return {"fast": fast_mode, "enabled": enabled, "limits": limits}


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


def _connection_summary(results: Dict[str, Dict[str, object]], enabled: Dict[str, bool]) -> str:
    pieces: List[str] = []
    for service in ("drive", "sheets", "notion"):
        if not enabled.get(service, True):
            continue
        label = _SERVICE_LABELS.get(service, service.title())
        ok = bool(results.get(service, {}).get("ok"))
        icon = "✓" if ok else "⚠"
        pieces.append(f"{icon} {label}")
    return f"Connections: {' '.join(pieces)}" if pieces else ""


def _format_fast_limits_line(limits: Dict[str, Optional[int]]) -> str:
    if not limits.get("fast"):
        return ""
    max_files = limits.get("max_files")
    max_pages = limits.get("max_pages")
    timeout = limits.get("timeout_sec")
    parts = [
        f"max_files={max_files if max_files is not None else '∞'}",
        f"max_pages={max_pages if max_pages is not None else '∞'}",
        f"timeout={f'{timeout}s' if timeout is not None else '∞'}",
    ]
    return "Fast discovery is ON: " + ", ".join(parts)


def _run_handshake(
    ctx: CommandContext, discovery_options: Dict[str, object], output: PrintFn
) -> Dict[str, Dict[str, object]]:
    broker = ctx.extras.get("conn_broker") if isinstance(ctx.extras, dict) else None
    results: Dict[str, Dict[str, object]] = {}
    enabled: Dict[str, bool] = discovery_options.get("enabled", {})  # type: ignore[arg-type]
    for service in ("drive", "sheets", "notion"):
        if not enabled.get(service, True):
            continue
        label = _SERVICE_LABELS.get(service, service.title())
        if broker is None:
            results[service] = {"service": service, "ok": False, "detail": "broker_unavailable"}
            output(f"⚠ {label} probe unavailable (broker missing)")
            continue
        result = broker.probe(service)
        results[service] = result
        if result.get("ok"):
            meta = result.get("metadata", {}) if isinstance(result, dict) else {}
            if service == "drive":
                root = meta.get("root") if isinstance(meta, dict) else None
                output(f"✓ {label} connected (root={root or 'n/a'})")
            elif service == "sheets":
                inventory_id = meta.get("inventory_id") if isinstance(meta, dict) else None
                output(f"✓ {label} connected (inventory_id={inventory_id or 'n/a'})")
            elif service == "notion":
                root = meta.get("root") if isinstance(meta, dict) else None
                pages = None
                if isinstance(meta, dict):
                    for key in ("pages", "title_len", "count"):
                        if meta.get(key) is not None:
                            pages = meta.get(key)
                            break
                pages_text = pages if pages is not None else 0
                output(f"✓ {label} connected (root={root or 'n/a'}, pages: {pages_text} base)")
        else:
            detail = result.get("detail") if isinstance(result, dict) else None
            output(f"⚠ {label} probe failed: {detail or 'probe failed'}")
    return results


def _prompt_discovery_action(
    prompt: PromptFn,
    output: PrintFn,
    *,
    discovery_options: Dict[str, object],
    handshake_results: Dict[str, Dict[str, object]],
) -> str:
    enabled: Dict[str, bool] = discovery_options.get("enabled", {})  # type: ignore[arg-type]
    limits: Dict[str, Optional[int]] = discovery_options.get("limits", {})  # type: ignore[arg-type]
    summary_line = _connection_summary(handshake_results, enabled)
    if summary_line:
        output(summary_line)
    fast_line = _format_fast_limits_line(limits)
    if fast_line:
        output(fast_line)
    if limits.get("fast"):
        while True:
            choice = prompt(
                "[Enter]=Run fast discovery   (f)=Full crawl   (s)=Skip discovery   (q)=Quit\n> "
            ).strip().lower()
            if choice in {"", "\n"}:
                return "fast"
            if choice == "f":
                return "full"
            if choice == "s":
                return "skip"
            if choice == "q":
                return "quit"
            output("Unknown selection. Use Enter, f, s, or q.")
    return "full"


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
    fast: bool = False,
    disable_drive: bool = False,
    disable_notion: bool = False,
    disable_sheets: bool = False,
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
    broker = ConnectionBroker(controller)
    context.extras["conn_broker"] = broker

    discovery_options = _resolve_discovery_options(
        fast_flag=fast,
        disable_drive=disable_drive,
        disable_notion=disable_notion,
        disable_sheets=disable_sheets,
    )
    context.options["discovery"] = discovery_options

    step = stage("Base-layer handshake")
    handshake_results = _run_handshake(context, discovery_options, output)
    stage_done(step)
    context.extras["handshake"] = handshake_results

    action = _prompt_discovery_action(
        prompt,
        output,
        discovery_options=discovery_options,
        handshake_results=handshake_results,
    )
    if action == "quit":
        output("Aborted.")
        return
    findings: Dict[str, object]
    if action == "skip":
        findings = {}
        context.findings = {}
        output("Discovery skipped.")
    else:
        if action == "full" and discovery_options.get("fast"):
            discovery_options["fast"] = False
            discovery_options["limits"] = _resolve_discovery_limits(False)
            context.options["discovery"] = discovery_options
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
