"""Writer plugin that produces Master Index markdown reports."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from core.bus.models import ApplyResult, CommandContext, HealthStatus, RollbackResult
from tgc.master_index_controller import NOTION_COLUMNS, render_markdown
from tgc.reporting import write_drive_files_markdown


def propose(ctx: CommandContext, input_data) -> List[Dict[str, object]]:  # pragma: no cover - optional hook
    _ = ctx, input_data
    return []


def apply(ctx: CommandContext, card_id: str, approval_token: str) -> ApplyResult:
    _ = approval_token
    card = ctx.get_card(card_id)
    if card is None:
        return ApplyResult(ok=False, errors=[f"Unknown card {card_id}"])

    data = card.data or {}
    output_dir = Path(data.get("output_dir") or "docs/master_index_reports/unknown_run")
    generated_at = data.get("generated_at") or ""

    notion = data.get("notion", {})
    drive = data.get("drive", {})

    notion_records = notion.get("records") or []
    drive_records = drive.get("records") or []

    notion_errors: List[str] = list(notion.get("errors") or [])
    drive_errors: List[str] = list(drive.get("errors") or [])

    output_dir.mkdir(parents=True, exist_ok=True)

    notion_path = output_dir / "notion_pages.md"
    drive_paths: List[Path] = []

    try:
        notion_markdown = render_markdown(notion_records, "Master Index — Notion Pages", NOTION_COLUMNS, generated_at)
        notion_path.write_text(notion_markdown, encoding="utf-8")
    except OSError as exc:
        notion_errors.append(f"Failed to write Notion index: {exc}")

    try:
        drive_paths = write_drive_files_markdown(output_dir, drive_records)
    except OSError as exc:
        drive_errors.append(f"Failed to write Drive index: {exc}")

    errors = notion_errors + drive_errors
    ok = not errors

    payload = {
        "output_dir": str(output_dir),
        "notion_output": str(notion_path),
        "drive_outputs": [str(path) for path in drive_paths],
        "notion_errors": notion_errors,
        "drive_errors": drive_errors,
        "notion_count": len(notion_records),
        "drive_count": len(drive_records),
        "message": drive.get("message") or notion.get("message"),
    }

    return ApplyResult(ok=ok, data=payload, errors=errors)


def rollback(ctx: CommandContext, op_id: str) -> RollbackResult:
    _ = ctx, op_id
    return RollbackResult(ok=True, notes=["Rollback not implemented for markdown writer"])


def health(ctx: CommandContext) -> HealthStatus:
    _ = ctx
    return HealthStatus(ok=True, notes=["Markdown writer ready"])
