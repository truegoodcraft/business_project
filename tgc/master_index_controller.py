"""Master Index controller for generating Notion and Drive indexes."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
import logging
import time
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from .notion.api import NotionAPIError
from .util.stage import stage, stage_done
from .util.watchdog import with_watchdog

try:  # Optional Google dependencies are managed by the Drive module
    from googleapiclient.errors import HttpError
except Exception:  # pragma: no cover - fallback when Google libs absent
    HttpError = Exception  # type: ignore


MAX_NOTION_ITEMS = 5_000
MAX_DRIVE_ITEMS = 5_000
NOTION_COLUMNS = ["title", "page_id", "url", "parent", "last_edited"]
DRIVE_COLUMNS = ["name", "file_id", "path_or_link", "mimeType", "modifiedTime", "size"]


def _sanitize_segment(text: str) -> str:
    cleaned = (text or "").strip()
    cleaned = cleaned.replace("/", "／").replace("|", "¦")
    return cleaned or "(untitled)"
logger = logging.getLogger(__name__)


_ticker_enabled = False
_ticker = {"requests": 0, "pages": 0, "blocks": 0, "last": 0.0}


def _reset_ticker() -> None:
    _ticker["requests"] = 0
    _ticker["pages"] = 0
    _ticker["blocks"] = 0
    _ticker["last"] = 0.0


def _tick(force: bool = False) -> None:
    if not _ticker_enabled:
        return
    now = time.perf_counter()
    if not force and (now - _ticker["last"]) < 0.25:
        return
    _ticker["last"] = now
    sys.stdout.write(
        f"\rCollecting pages ({_ticker['pages']}) • blocks ({_ticker['blocks']}) • requests ({_ticker['requests']})"
    )
    sys.stdout.flush()


def _start_ticker() -> None:
    global _ticker_enabled
    _reset_ticker()
    _ticker_enabled = True
    _tick(force=True)


def _stop_ticker() -> None:
    global _ticker_enabled
    if _ticker_enabled:
        sys.stdout.write("\n")
        sys.stdout.flush()
    _ticker_enabled = False


def _notion_sort_key(item: Dict[str, str]) -> Tuple[str, str]:
    return ((item.get("title") or "").casefold(), item.get("url") or "")


def _drive_sort_key(item: Dict[str, str]) -> Tuple[str, str]:
    return ((item.get("path_or_link") or "").casefold(), item.get("name") or "")


@dataclass
class MasterIndexSummary:
    """Lightweight summary returned to the caller."""

    status: str
    dry_run: bool
    notion_count: int = 0
    drive_count: int = 0
    output_dir: Optional[Path] = None
    notion_output: Optional[Path] = None
    drive_output: Optional[Path] = None
    notion_errors: Optional[List[str]] = None
    drive_errors: Optional[List[str]] = None
    message: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "status": self.status,
            "dry_run": self.dry_run,
            "notion_count": self.notion_count,
            "drive_count": self.drive_count,
            "output_dir": str(self.output_dir) if self.output_dir else None,
            "notion_output": str(self.notion_output) if self.notion_output else None,
            "drive_output": str(self.drive_output) if self.drive_output else None,
            "notion_errors": list(self.notion_errors or []),
            "drive_errors": list(self.drive_errors or []),
            "message": self.message,
        }


@dataclass
class MasterIndexData:
    """In-memory representation of the assembled Master Index."""

    status: str
    dry_run: bool
    generated_at: str
    notion_records: List[Dict[str, str]] = field(default_factory=list)
    drive_records: List[Dict[str, str]] = field(default_factory=list)
    notion_errors: List[str] = field(default_factory=list)
    drive_errors: List[str] = field(default_factory=list)
    notion_roots: List[str] = field(default_factory=list)
    drive_roots: List[str] = field(default_factory=list)
    notion_elapsed: float = 0.0
    drive_elapsed: float = 0.0
    message: Optional[str] = None

    def snapshot(self) -> Dict[str, object]:
        return {
            "status": self.status,
            "dry_run": self.dry_run,
            "generated_at": self.generated_at,
            "message": self.message,
            "notion": {
                "roots": list(self.notion_roots),
                "count": len(self.notion_records),
                "elapsed_seconds": self.notion_elapsed,
                "errors": list(self.notion_errors),
                "records": self.notion_records,
            },
            "drive": {
                "roots": list(self.drive_roots),
                "count": len(self.drive_records),
                "elapsed_seconds": self.drive_elapsed,
                "errors": list(self.drive_errors),
                "records": self.drive_records,
            },
        }


@dataclass
class TraversalLimits:
    """Optional limits that can short-circuit traversal."""

    max_seconds: Optional[float] = None
    max_pages: Optional[int] = None
    max_requests: Optional[int] = None
    max_depth: Optional[int] = None


@dataclass
class TraversalResult:
    """Outcome from a traversal helper."""

    records: List[Dict[str, str]]
    errors: List[str]
    partial: bool = False
    reason: Optional[str] = None


class MasterIndexController:
    """Generate Markdown indexes for Notion pages and Google Drive files."""

    def __init__(self, controller: "Controller") -> None:
        self.controller = controller

    # ------------------------------------------------------------------
    # Public entry point

    def build_index_snapshot(
        self, *, limits: Optional[TraversalLimits] = None
    ) -> Dict[str, object]:
        """Collect the live Master Index data without writing to disk."""

        data = self._collect_master_index(placeholders=False, limits=limits)
        return data.snapshot()

    def _collect_master_index(
        self, *, placeholders: bool, limits: Optional[TraversalLimits] = None
    ) -> MasterIndexData:
        traversal_limits = limits or TraversalLimits()
        ready, detail = self._adapters_ready()
        generated_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        if not ready:
            message = (
                "Master Index unavailable: run 'Discover & Audit' and verify Notion + Drive are ready."
            )
            print(message, flush=True)
            if detail:
                print(detail, flush=True)
            return MasterIndexData(
                status="unavailable",
                dry_run=placeholders,
                generated_at=generated_at,
                message=detail or message,
            )

        notion_module = self._notion_module()
        drive_module = self._drive_module()
        if notion_module is None or drive_module is None:
            notion_errors = ["Notion module unavailable"] if notion_module is None else []
            drive_errors = ["Google Drive module unavailable"] if drive_module is None else []
            message = "Required modules unavailable; re-run Discover & Audit after configuration."
            print(message, flush=True)
            return MasterIndexData(
                status="error",
                dry_run=placeholders,
                generated_at=generated_at,
                notion_errors=notion_errors,
                drive_errors=drive_errors,
                message=message,
            )

        notion_roots = self._notion_root_ids(notion_module)
        drive_roots = self._drive_root_ids(drive_module)

        notion_start = time.perf_counter()
        if notion_roots:
            print(
                f"Collecting Notion pages from {len(notion_roots)} root(s)...",
                flush=True,
            )
        else:
            print("No Notion roots configured; skipping page traversal.", flush=True)
        if placeholders and notion_roots:
            print(
                "[dry-run] Skipping Notion API calls and generating placeholder rows.",
                flush=True,
            )
            notion_records = [
                {
                    "title": f"(dry-run placeholder for root {root[:8]}…)",
                    "page_id": root,
                    "url": "",
                    "parent": "/",
                    "last_edited": "",
                }
                for root in notion_roots
            ]
            notion_errors: List[str] = []
            notion_partial = False
            notion_reason: Optional[str] = None
        else:
            notion_result = collect_notion_pages(
                notion_module,
                notion_roots,
                max_depth=notion_module.config.max_depth,
                page_size=notion_module.config.page_size,
                limits=traversal_limits,
            )
            notion_records = notion_result.records
            notion_errors = notion_result.errors
            notion_partial = notion_result.partial
            notion_reason = notion_result.reason
        notion_elapsed = time.perf_counter() - notion_start
        print(
            "Collected {} Notion page(s) in {:.1f}s".format(
                len(notion_records), notion_elapsed
            ),
            flush=True,
        )

        drive_start = time.perf_counter()
        if drive_roots:
            print(
                f"Collecting Drive files from {len(drive_roots)} root(s)...",
                flush=True,
            )
        else:
            print("No Drive roots configured; skipping file traversal.", flush=True)
        progress_enabled = logging.getLogger().isEnabledFor(logging.INFO)
        drive_stage: Optional[float] = None
        if placeholders and drive_roots:
            print(
                "[dry-run] Skipping Drive API calls and generating placeholder rows.",
                flush=True,
            )
            drive_records = [
                {
                    "name": f"(dry-run placeholder for root {root[:8]}…)",
                    "file_id": root,
                    "path_or_link": "/",
                    "mimeType": "",
                    "modifiedTime": "",
                    "size": "",
                }
                for root in drive_roots
            ]
            drive_errors: List[str] = []
            drive_partial = False
            drive_reason: Optional[str] = None
        else:
            if drive_roots and progress_enabled:
                drive_stage = stage("Drive → list files")
            drive_records = []
            drive_errors = []
            drive_partial = False
            drive_reason = None
            try:
                drive_result = collect_drive_files(
                    drive_module,
                    drive_roots,
                    mime_whitelist=list(drive_module.config.mime_whitelist) or None,
                    max_depth=drive_module.config.max_depth,
                    page_size=drive_module.config.page_size,
                    limits=traversal_limits,
                )
                drive_records = drive_result.records
                drive_errors = drive_result.errors
                drive_partial = drive_result.partial
                drive_reason = drive_result.reason
            finally:
                if drive_stage is not None:
                    stage_done(drive_stage, f"(files: {len(drive_records)})")
        drive_elapsed = time.perf_counter() - drive_start
        print(
            "Collected {} Drive file(s) in {:.1f}s".format(
                len(drive_records), drive_elapsed
            ),
            flush=True,
        )

        notion_records.sort(key=_notion_sort_key)
        drive_records.sort(key=_drive_sort_key)

        partial_messages: List[str] = []
        if notion_partial:
            partial_messages.append(notion_reason or "Notion traversal stopped early.")
        if drive_partial:
            partial_messages.append(drive_reason or "Drive traversal stopped early.")

        status = "partial" if partial_messages else "ok"
        message = "\n".join(partial_messages) if partial_messages else None

        return MasterIndexData(
            status=status,
            dry_run=placeholders,
            generated_at=generated_at,
            notion_records=notion_records,
            drive_records=drive_records,
            notion_errors=notion_errors,
            drive_errors=drive_errors,
            notion_roots=notion_roots,
            drive_roots=drive_roots,
            notion_elapsed=notion_elapsed,
            drive_elapsed=drive_elapsed,
            message=message,
        )

    def run_master_index(
        self, dry_run: bool, *, limits: Optional[TraversalLimits] = None
    ) -> Dict[str, object]:
        data = self._collect_master_index(placeholders=dry_run, limits=limits)
        if data.status == "unavailable":
            summary = MasterIndexSummary(status="unavailable", dry_run=dry_run, message=data.message)
            self._append_log(summary)
            return summary.to_dict()

        if data.status == "error":
            summary = MasterIndexSummary(
                status="error",
                dry_run=dry_run,
                notion_count=len(data.notion_records),
                drive_count=len(data.drive_records),
                notion_errors=data.notion_errors or None,
                drive_errors=data.drive_errors or None,
                message=data.message,
            )
            self._append_log(summary)
            return summary.to_dict()

        notion_records = list(data.notion_records)
        drive_records = list(data.drive_records)

        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        output_dir = Path("docs") / "master_index_reports" / f"master_index_{timestamp}"
        notion_path = output_dir / "notion_pages.md"
        drive_path = output_dir / "drive_files.md"

        notion_markdown = render_markdown(
            notion_records, "Master Index — Notion Pages", NOTION_COLUMNS, data.generated_at
        )
        drive_markdown = render_markdown(
            drive_records, "Master Index — Drive Files", DRIVE_COLUMNS, data.generated_at
        )

        notion_errors = list(data.notion_errors)
        drive_errors = list(data.drive_errors)

        if dry_run:
            print(f"[dry-run] Would write Notion index to: {notion_path}", flush=True)
            print(f"[dry-run] Would write Drive index to: {drive_path}", flush=True)
        else:
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                message = f"Unable to prepare report directory {output_dir}: {exc}"
                notion_errors.append(message)
                drive_errors.append(message)
            else:
                try:
                    notion_path.write_text(notion_markdown, encoding="utf-8")
                except OSError as exc:
                    notion_errors.append(f"Failed to write Notion index: {exc}")
                try:
                    drive_path.write_text(drive_markdown, encoding="utf-8")
                except OSError as exc:
                    drive_errors.append(f"Failed to write Drive index: {exc}")

        status = "partial" if data.status == "partial" else "ok"
        if status != "partial" and (notion_errors or drive_errors):
            status = "error"

        summary = MasterIndexSummary(
            status=status,
            dry_run=dry_run,
            notion_count=len(notion_records),
            drive_count=len(drive_records),
            output_dir=output_dir,
            notion_output=None if dry_run else notion_path,
            drive_output=None if dry_run else drive_path,
            notion_errors=notion_errors or None,
            drive_errors=drive_errors or None,
            message=data.message,
        )
        self._append_log(summary)
        return summary.to_dict()

    # ------------------------------------------------------------------
    # Helpers

    def _adapters_ready(self) -> Tuple[bool, Optional[str]]:
        statuses = self.controller.adapter_status()
        notion_ready = statuses.get("notion", False)
        drive_ready = statuses.get("drive", False)
        if notion_ready and drive_ready:
            return True, None
        message = "Required adapters not ready: Notion ({}) · Drive ({})".format(
            "ready" if notion_ready else "not ready",
            "ready" if drive_ready else "not ready",
        )
        return False, message

    def _notion_module(self) -> Optional["NotionAccessModule"]:
        module_obj = self.controller.get_module("notion_access")
        from .notion import NotionAccessModule

        if isinstance(module_obj, NotionAccessModule):
            return module_obj
        return None

    def _drive_module(self) -> Optional["GoogleDriveModule"]:
        module_obj = self.controller.get_module("drive")
        from .modules import GoogleDriveModule

        if isinstance(module_obj, GoogleDriveModule):
            return module_obj
        return None

    def _notion_root_ids(self, notion_module: "NotionAccessModule") -> List[str]:
        root_ids = [value for value in notion_module.config.root_ids if value]
        deduped: List[str] = []
        seen: set[str] = set()
        for value in root_ids:
            if value not in seen:
                deduped.append(value)
                seen.add(value)
        return deduped

    def _drive_root_ids(self, drive_module: "GoogleDriveModule") -> List[str]:
        roots = [value for value in drive_module.root_ids() if value]
        if roots:
            deduped: List[str] = []
            seen: set[str] = set()
            for value in roots:
                if value not in seen:
                    deduped.append(value)
                    seen.add(value)
            return deduped
        fallback = self.controller.config.drive.fallback_root_id
        return [fallback] if fallback else []

    def _append_log(self, summary: MasterIndexSummary) -> None:
        log_dir = Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "controller.log"
        timestamp = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        line = (
            f"{timestamp} module=master_index status={summary.status} "
            f"dry_run={summary.dry_run} notion={summary.notion_count} "
            f"drive={summary.drive_count}"
        )
        if summary.output_dir:
            line += f" output={summary.output_dir}"
        if summary.message:
            line += f" message={summary.message}"
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")


# ----------------------------------------------------------------------
# Notion helpers


@with_watchdog(45)
def collect_notion_pages(
    notion_module: "NotionAccessModule",
    root_ids: Sequence[str],
    *,
    max_depth: int = 0,
    page_size: int = 100,
    limit: int = MAX_NOTION_ITEMS,
    limits: Optional[TraversalLimits] = None,
) -> TraversalResult:
    from .notion.module import NotionAccessModule

    root_id_list = list(root_ids)
    timer_start = time.perf_counter()
    if logging.getLogger().isEnabledFor(logging.DEBUG):
        logging.debug("notion.list_pages.start", extra={"root_ids": root_id_list})
    try:
        if not isinstance(notion_module, NotionAccessModule):
            return [], ["Notion module unavailable"]
        client, error = notion_module._build_client()  # type: ignore[attr-defined]
        if not client:
            return [], [error or "Notion client unavailable"]

        queue: deque[Tuple[str, int, List[str]]] = deque()
        for root in root_id_list:
            if root:
                queue.append((root, 0, []))

        if queue:
            _start_ticker()

        visited: set[str] = set()
        records: List[Dict[str, str]] = []
        errors: List[str] = []
        depth_limit = max_depth if max_depth and max_depth > 0 else None
        start_time = time.perf_counter()
        processed = 0
        progress_interval = 100
        traversal_limits = limits or TraversalLimits()
        stats: dict[str, int | float] = {
            "requests": 0,
            "pages": 0,
            "blocks": 0,
            "started": time.perf_counter(),
        }
        stop_reason: Optional[str] = None

        def set_stop(reason: str) -> None:
            nonlocal stop_reason
            if not stop_reason:
                stop_reason = reason

        def check_limits() -> bool:
            if stop_reason:
                return True
            if (
                traversal_limits.max_seconds
                and (time.perf_counter() - float(stats["started"])) > traversal_limits.max_seconds
            ):
                set_stop(
                    f"Reached Notion max seconds ({traversal_limits.max_seconds})."
                )
                return True
            if (
                traversal_limits.max_requests is not None
                and traversal_limits.max_requests > 0
                and int(stats["requests"]) >= traversal_limits.max_requests
            ):
                set_stop(
                    f"Reached Notion max requests ({traversal_limits.max_requests})."
                )
                return True
            if (
                traversal_limits.max_pages is not None
                and traversal_limits.max_pages > 0
                and int(stats["pages"]) >= traversal_limits.max_pages
            ):
                set_stop(f"Reached Notion max pages ({traversal_limits.max_pages}).")
                return True
            return False

        def log_progress(force: bool = False) -> None:
            requests = int(stats["requests"])
            if requests and requests % 50 == 0:
                force = True
            if force and logger.isEnabledFor(logging.DEBUG):
                elapsed = time.perf_counter() - float(stats["started"])
                logger.debug(
                    "notion.traversal.progress",
                    extra={
                        "requests": requests,
                        "pages": int(stats["pages"]),
                        "blocks": int(stats["blocks"]),
                        "s": int(elapsed),
                    },
                )

        def page_done() -> None:
            nonlocal stop_reason
            stats["pages"] += 1
            if _ticker_enabled:
                _ticker["pages"] += 1
                _tick(force=True)
            log_progress(force=True)
            check_limits()

        try:
            while queue and len(records) < limit and not stop_reason:
                page_id, depth, ancestors = queue.popleft()
                if page_id in visited:
                    continue
                visited.add(page_id)
                if (
                    traversal_limits.max_depth is not None
                    and traversal_limits.max_depth > -1
                    and depth > traversal_limits.max_depth
                ):
                    set_stop(f"Reached Notion max depth ({traversal_limits.max_depth}).")
                    break
                if check_limits():
                    break
                try:
                    page = client.pages_retrieve(page_id)
                except NotionAPIError as exc:
                    if exc.status in {400, 404} or exc.code == "object_not_found":
                        handled = _handle_database_root(
                            client,
                            page_id,
                            depth,
                            ancestors,
                            queue,
                            records,
                            errors,
                            limit,
                            depth_limit,
                            page_size,
                            stats,
                            log_progress,
                            page_done,
                            traversal_limits,
                            check_limits,
                            set_stop,
                        )
                        if handled:
                            continue
                    errors.append(f"Page {page_id}: {exc.message}")
                    continue
                finally:
                    stats["requests"] += 1
                    if _ticker_enabled:
                        _ticker["requests"] += 1
                        _tick()
                    log_progress()
                    check_limits()
                    if stop_reason:
                        break

                title = _extract_page_title(page)
                parent_path = "/" + "/".join(ancestors) if ancestors else "/"
                records.append(
                    {
                        "title": title or "(untitled)",
                        "page_id": page.get("id", page_id),
                        "url": page.get("url", ""),
                        "parent": parent_path,
                        "last_edited": page.get("last_edited_time", ""),
                    }
                )
                processed += 1
                if (
                    processed % progress_interval == 0
                    and logger.isEnabledFor(logging.DEBUG)
                ):
                    elapsed = time.perf_counter() - start_time
                    logger.debug(
                        "notion.traversal.pages",
                        extra={
                            "processed": processed,
                            "queue": len(queue),
                            "elapsed": round(elapsed, 1),
                        },
                    )

                if len(records) >= limit:
                    page_done()
                    break

                if depth_limit is not None and depth >= depth_limit:
                    page_done()
                    continue

                next_cursor: Optional[str] = None
                seen_cursors: set[str] = set()
                while True:
                    if check_limits():
                        break
                    try:
                        children = client.blocks_children_list(
                            page_id,
                            page_size=100,
                            start_cursor=next_cursor,
                        )
                    except NotionAPIError as exc:
                        errors.append(f"Children {page_id}: {exc.message}")
                        break
                    finally:
                        stats["requests"] += 1
                        if _ticker_enabled:
                            _ticker["requests"] += 1
                            _tick()
                        log_progress()
                        check_limits()
                        if stop_reason:
                            break

                    results = children.get("results", [])
                    count = len(results)
                    stats["blocks"] += count
                    if _ticker_enabled:
                        _ticker["blocks"] += count
                        _tick()

                    for block in results:
                        if not isinstance(block, dict):
                            continue
                        block_type = block.get("type")
                        child_id = block.get("id")
                        if block_type == "child_page" and child_id:
                            next_path = ancestors + [_sanitize_segment(title or "(untitled)")]
                            if (
                                traversal_limits.max_depth is not None
                                and traversal_limits.max_depth > -1
                                and depth + 1 > traversal_limits.max_depth
                            ):
                                set_stop(
                                    f"Reached Notion max depth ({traversal_limits.max_depth})."
                                )
                                break
                            queue.append((child_id, depth + 1, next_path))
                        elif block_type == "link_to_page":
                            target = block.get("link_to_page", {})
                            if isinstance(target, dict) and target.get("type") == "page_id":
                                target_id = target.get("page_id")
                                if target_id and target_id not in visited:
                                    next_path = ancestors + [_sanitize_segment(title or "(untitled)")]
                                    if (
                                        traversal_limits.max_depth is not None
                                        and traversal_limits.max_depth > -1
                                        and depth + 1 > traversal_limits.max_depth
                                    ):
                                        set_stop(
                                            f"Reached Notion max depth ({traversal_limits.max_depth})."
                                        )
                                        break
                                    queue.append((target_id, depth + 1, next_path))
                    if not children.get("has_more"):
                        break
                    cursor_value = children.get("next_cursor")
                    if not cursor_value:
                        break
                    if cursor_value in seen_cursors:
                        errors.append(
                            f"Page {page_id}: detected repeated pagination cursor; aborting traversal."
                        )
                        break
                    seen_cursors.add(cursor_value)
                    next_cursor = cursor_value
                    if check_limits():
                        break
                page_done()
                if stop_reason:
                    break
        except Exception:
            logger.exception("notion traversal failed", extra={"root_ids": root_id_list})
            raise

        partial = bool(stop_reason)
        return TraversalResult(records=records[:limit], errors=errors, partial=partial, reason=stop_reason)
    finally:
        _stop_ticker()
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            logging.debug(
                "notion.list_pages.done",
                extra={"ms": int((time.perf_counter() - timer_start) * 1000)},
            )


def _handle_database_root(
    client: "NotionAPIClient",
    database_id: str,
    depth: int,
    ancestors: List[str],
    queue: "deque[Tuple[str, int, List[str]]]",
    records: List[Dict[str, str]],
    errors: List[str],
    limit: int,
    depth_limit: Optional[int],
    page_size: int,
    stats: dict[str, int | float],
    log_progress: Callable[..., None],
    page_done: Callable[[], None],
    limits: TraversalLimits,
    check_limits: Callable[[], bool],
    set_stop: Callable[[str], None],
) -> bool:
    from .notion.api import NotionAPIError as _NotionAPIError

    try:
        database = client.databases_retrieve(database_id)
    except _NotionAPIError as exc:
        if exc.status in {400, 404} or exc.code == "object_not_found":
            return False
        errors.append(f"Database {database_id}: {exc.message}")
        return True
    except Exception as exc:  # pragma: no cover - defensive network guard
        logger.exception("database traversal failed", extra={"database_id": database_id})
        raise
    finally:
        stats["requests"] += 1
        if _ticker_enabled:
            _ticker["requests"] += 1
            _tick()
        log_progress()
        if check_limits():
            return True

    title = _join_rich_text(database.get("title", [])) if isinstance(database, dict) else ""
    database_title = title or "(untitled)"
    records.append(
        {
            "title": database_title,
            "page_id": database.get("id", database_id) if isinstance(database, dict) else database_id,
            "url": database.get("url", "") if isinstance(database, dict) else "",
            "parent": "/" + "/".join(ancestors) if ancestors else "/",
            "last_edited": database.get("last_edited_time", "") if isinstance(database, dict) else "",
        }
    )

    if len(records) >= limit:
        page_done()
        return True

    if depth_limit is not None and depth >= depth_limit:
        page_done()
        return True

    base_path = ancestors + [_sanitize_segment(database_title)] if database_title else list(ancestors)

    next_cursor: Optional[str] = None
    seen_cursors: set[str] = set()
    while True:
        try:
            response = client.databases_query(
                database_id,
                page_size=min(page_size, 100),
                start_cursor=next_cursor,
            )
        except _NotionAPIError as exc:
            errors.append(f"Database {database_id}: {exc.message}")
            break
        except Exception as exc:  # pragma: no cover - defensive network guard
            logger.exception(
                "database query traversal failed", extra={"database_id": database_id}
            )
            raise
        finally:
            stats["requests"] += 1
            if _ticker_enabled:
                _ticker["requests"] += 1
                _tick()
            log_progress()
            if check_limits():
                break

        for item in response.get("results", []):
            if not isinstance(item, dict):
                continue
            child_id = item.get("id")
            if not child_id:
                continue
            if (
                limits.max_depth is not None
                and limits.max_depth > -1
                and depth + 1 > limits.max_depth
            ):
                set_stop(f"Reached Notion max depth ({limits.max_depth}).")
                break
            queue.append((child_id, depth + 1, base_path))

        if not response.get("has_more"):
            break
        next_cursor = response.get("next_cursor")
        if not next_cursor:
            break
        if next_cursor in seen_cursors:
            errors.append(
                f"Database {database_id}: detected repeated pagination cursor; aborting traversal."
            )
            break
        seen_cursors.add(next_cursor)

    page_done()
    return True


def _extract_page_title(page: Dict[str, object]) -> str:
    properties = page.get("properties")
    if isinstance(properties, dict):
        for value in properties.values():
            if isinstance(value, dict) and value.get("type") == "title":
                title_value = value.get("title")
                if isinstance(title_value, list):
                    return _join_rich_text(title_value)
    if isinstance(page.get("title"), list):
        return _join_rich_text(page.get("title"))
    return ""


def _join_rich_text(rich_text: Iterable[Dict[str, object]]) -> str:
    parts: List[str] = []
    for item in rich_text:
        if isinstance(item, dict):
            parts.append(str(item.get("plain_text", "")))
    return "".join(parts)


# ----------------------------------------------------------------------
# Google Drive helpers



def collect_drive_files(
    drive_module: "GoogleDriveModule",
    root_ids: Sequence[str],
    *,
    mime_whitelist: Optional[Sequence[str]] = None,
    max_depth: int = 0,
    page_size: int = 200,
    limit: int = MAX_DRIVE_ITEMS,
    limits: Optional[TraversalLimits] = None,
) -> TraversalResult:
    from .modules.google_drive import GoogleDriveModule

    root_id_list = list(root_ids)
    timer_start = time.perf_counter()
    if logging.getLogger().isEnabledFor(logging.DEBUG):
        logging.debug("drive.list_files.start", extra={"root_ids": root_id_list})
    try:
        if not isinstance(drive_module, GoogleDriveModule):
            return TraversalResult(records=[], errors=["Google Drive module unavailable"])

        service, error = drive_module.ensure_service()
        if not service:
            return TraversalResult(records=[], errors=[error or "Google Drive service unavailable"])

        whitelist = {value for value in mime_whitelist or [] if value}
        depth_limit = max_depth if max_depth and max_depth > 0 else None
        size = page_size if page_size and page_size > 0 else 200
        traversal_limits = limits or TraversalLimits()

        queue: deque[Tuple[str, int, List[str]]] = deque()
        for root in root_id_list:
            if root:
                queue.append((root, 0, []))

        visited: set[str] = set()
        records: List[Dict[str, str]] = []
        errors: List[str] = []
        shortcut_cache: Dict[str, Dict[str, object]] = {}
        start_time = time.perf_counter()
        processed = 0
        progress_interval = 100
        stats: dict[str, int | float] = {
            "requests": 0,
            "pages": 0,
            "started": time.perf_counter(),
        }
        stop_reason: Optional[str] = None

        def set_stop(reason: str) -> None:
            nonlocal stop_reason
            if not stop_reason:
                stop_reason = reason

        def check_limits() -> bool:
            if stop_reason:
                return True
            if (
                traversal_limits.max_seconds
                and (time.perf_counter() - float(stats["started"])) > traversal_limits.max_seconds
            ):
                set_stop(f"Reached Drive max seconds ({traversal_limits.max_seconds}).")
                return True
            if (
                traversal_limits.max_requests is not None
                and traversal_limits.max_requests > 0
                and int(stats["requests"]) >= traversal_limits.max_requests
            ):
                set_stop(f"Reached Drive max requests ({traversal_limits.max_requests}).")
                return True
            if (
                traversal_limits.max_pages is not None
                and traversal_limits.max_pages > 0
                and int(stats["pages"]) >= traversal_limits.max_pages
            ):
                set_stop(f"Reached Drive max pages ({traversal_limits.max_pages}).")
                return True
            return False

        while queue and len(records) < limit and not stop_reason:
            file_id, depth, ancestors = queue.popleft()
            if not file_id or file_id in visited:
                continue
            visited.add(file_id)
            if (
                traversal_limits.max_depth is not None
                and traversal_limits.max_depth > -1
                and depth > traversal_limits.max_depth
            ):
                set_stop(f"Reached Drive max depth ({traversal_limits.max_depth}).")
                break
            if check_limits():
                break
            try:
                metadata = (
                    service.files()
                    .get(
                        fileId=file_id,
                        fields="id,name,mimeType,parents,modifiedTime,size,webViewLink,shortcutDetails,trashed",
                        supportsAllDrives=True,
                    )
                    .execute()
                )
            except Exception as exc:  # pragma: no cover - network dependent
                errors.append(_format_drive_error(file_id, exc))
                continue
            finally:
                stats["requests"] += 1
                if check_limits():
                    break

            if metadata.get("trashed"):
                continue

            name = metadata.get("name") or "(untitled)"
            path_segments = ancestors + [_sanitize_segment(name)]
            path_value = "/".join(segment for segment in path_segments if segment)

            shortcut_details = metadata.get("shortcutDetails")
            path_or_link = path_value
            if isinstance(shortcut_details, dict):
                target_id = shortcut_details.get("targetId")
                if target_id:
                    target = _resolve_shortcut(service, target_id, shortcut_cache, errors)
                    if target:
                        metadata.setdefault("mimeType", target.get("mimeType"))
                        metadata.setdefault("modifiedTime", target.get("modifiedTime"))
                        metadata.setdefault("size", target.get("size"))
                        metadata.setdefault("webViewLink", target.get("webViewLink"))
                        target_label = target.get("webViewLink") or target.get("name") or target_id
                    else:
                        target_label = target_id
                    path_or_link = f"{path_value} → {target_label}"
                    if target_id not in visited:
                        queue.append((target_id, depth, ancestors))

            mime_type = metadata.get("mimeType") or ""
            include_record = True
            if whitelist and mime_type != "application/vnd.google-apps.folder":
                include_record = mime_type in whitelist

            if include_record:
                size_value = metadata.get("size")
                size_text = "" if size_value in (None, "") else str(size_value)
                modified = metadata.get("modifiedTime") or ""
                records.append(
                    {
                        "name": name,
                        "file_id": metadata.get("id", file_id),
                        "path_or_link": path_or_link,
                        "mimeType": mime_type,
                        "modifiedTime": modified,
                        "size": size_text,
                    }
                )
                stats["pages"] += 1
                check_limits()
                if len(records) >= limit:
                    break
                processed += 1
                if processed % progress_interval == 0:
                    elapsed = time.perf_counter() - start_time
                    print(
                        "  Processed {} Drive file(s) so far (queue: {}, elapsed: {:.1f}s)".format(
                            processed,
                            len(queue),
                            elapsed,
                        ),
                        flush=True,
                    )

            if mime_type == "application/vnd.google-apps.folder":
                if depth_limit is not None and depth >= depth_limit:
                    continue
                query = f"'{file_id}' in parents and trashed = false"
                page_token: Optional[str] = None
                seen_tokens: set[str] = set()
                while True:
                    if check_limits():
                        break
                    try:
                        response = (
                            service.files()
                            .list(
                                q=query,
                                includeItemsFromAllDrives=drive_module.config.include_shared_drives,
                                supportsAllDrives=True,
                                corpora="allDrives"
                                if drive_module.config.include_shared_drives
                                else "default",
                                pageSize=size,
                                pageToken=page_token,
                                fields="nextPageToken, files(id)",
                            )
                            .execute()
                        )
                    except Exception as exc:  # pragma: no cover - network dependent
                        errors.append(_format_drive_error(file_id, exc))
                        break
                    finally:
                        stats["requests"] += 1
                        if check_limits():
                            break
                    for child in response.get("files", []):
                        child_id = child.get("id")
                        if child_id:
                            if (
                                traversal_limits.max_depth is not None
                                and traversal_limits.max_depth > -1
                                and depth + 1 > traversal_limits.max_depth
                            ):
                                set_stop(f"Reached Drive max depth ({traversal_limits.max_depth}).")
                                break
                            queue.append((child_id, depth + 1, path_segments))
                    token = response.get("nextPageToken")
                    if not token:
                        break
                    if token in seen_tokens:
                        errors.append(
                            f"Drive {file_id}: detected repeated pagination token; aborting traversal."
                        )
                        break
                    seen_tokens.add(token)
                    page_token = token
                    if check_limits():
                        break

        partial = bool(stop_reason)
        return TraversalResult(records=records[:limit], errors=errors, partial=partial, reason=stop_reason)
    finally:
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            logging.debug(
                "drive.list_files.done",
                extra={"ms": int((time.perf_counter() - timer_start) * 1000)},
            )

def _resolve_shortcut(
    service: object,
    target_id: str,
    cache: Dict[str, Dict[str, object]],
    errors: List[str],
) -> Dict[str, object]:
    if target_id in cache:
        return cache[target_id]
    try:
        target = (
            service.files()
            .get(
                fileId=target_id,
                fields="id,name,mimeType,modifiedTime,size,webViewLink,trashed",
                supportsAllDrives=True,
            )
            .execute()
        )
    except Exception as exc:  # pragma: no cover - network dependent
        errors.append(_format_drive_error(target_id, exc))
        target = {}
    cache[target_id] = target
    return target


def _format_drive_error(file_id: str, exc: Exception) -> str:
    if isinstance(exc, HttpError):  # pragma: no cover - depends on google client
        message = getattr(exc, "error_details", None) or getattr(exc, "reason", "")
        return f"Drive {file_id}: {message or exc}"
    return f"Drive {file_id}: {exc}"


# ----------------------------------------------------------------------
# Markdown helpers


def render_markdown(
    records: Sequence[Dict[str, object]],
    title: str,
    columns: Sequence[str],
    generated_at: str,
) -> str:
    lines = [f"# {title}", f"Generated: {generated_at}", f"Total: {len(records)}", ""]
    header = "| " + " | ".join(columns) + " |"
    separator = "|" + "|".join(["---"] * len(columns)) + "|"
    lines.append(header)
    lines.append(separator)
    for record in records:
        row: List[str] = []
        for column in columns:
            value = record.get(column, "")
            if value is None:
                value = ""
            text = str(value).replace("|", r"\|").replace("\n", " ").strip()
            row.append(text)
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n"


if TYPE_CHECKING:  # pragma: no cover - typing only
    from .controller import Controller
    from .modules import GoogleDriveModule
    from .notion import NotionAccessModule
    from .notion.api import NotionAPIClient
