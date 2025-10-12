"""Master Index controller for generating Notion and Drive indexes."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Iterable, List, Optional, Sequence, Tuple

from .notion.api import NotionAPIError

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


class MasterIndexController:
    """Generate Markdown indexes for Notion pages and Google Drive files."""

    def __init__(self, controller: "Controller") -> None:
        self.controller = controller

    # ------------------------------------------------------------------
    # Public entry point

    def run_master_index(self, dry_run: bool) -> Dict[str, object]:
        ready, detail = self._adapters_ready()
        if not ready:
            message = (
                "Master Index unavailable: run 'Discover & Audit' and verify Notion + Drive are ready."
            )
            print(message)
            if detail:
                print(detail)
            summary = MasterIndexSummary(status="unavailable", dry_run=dry_run, message=detail)
            self._append_log(summary)
            return summary.to_dict()
        ready, _details = self._adapters_ready()
        if not ready:
            print(
                "Master Index unavailable: run 'Discover & Audit' and verify Notion + Drive are ready."
            )
            return MasterIndexSummary(status="unavailable", dry_run=dry_run).to_dict()

        notion_module = self._notion_module()
        drive_module = self._drive_module()
        if notion_module is None or drive_module is None:
            notion_errors = ["Notion module unavailable"] if notion_module is None else None
            drive_errors = ["Google Drive module unavailable"] if drive_module is None else None
            message = "Required modules unavailable; re-run Discover & Audit after configuration."
            summary = MasterIndexSummary(
                status="error",
                dry_run=dry_run,
                notion_errors=notion_errors,
                drive_errors=drive_errors,
                message=message,
            )
            print(message)
            self._append_log(summary)
            )
            return summary.to_dict()

        notion_roots = self._notion_root_ids(notion_module)
        drive_roots = self._drive_root_ids(drive_module)

        generated_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        notion_records, notion_errors = collect_notion_pages(
            notion_module,
            notion_roots,
            max_depth=notion_module.config.max_depth,
            page_size=notion_module.config.page_size,
        )
        drive_records, drive_errors = collect_drive_files(
            drive_module,
            drive_roots,
            mime_whitelist=list(drive_module.config.mime_whitelist) or None,
            max_depth=drive_module.config.max_depth,
            page_size=drive_module.config.page_size,
        )

        notion_records.sort(key=lambda item: ((item.get("title") or "").casefold(), item.get("url") or ""))
        drive_records.sort(key=lambda item: ((item.get("path_or_link") or "").casefold(), item.get("name") or ""))

        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        output_dir = Path("reports") / f"master_index_{timestamp}"
        notion_path = output_dir / "notion_pages.md"
        drive_path = output_dir / "drive_files.md"

        notion_markdown = render_markdown(notion_records, "Master Index — Notion Pages", NOTION_COLUMNS, generated_at)
        drive_markdown = render_markdown(drive_records, "Master Index — Drive Files", DRIVE_COLUMNS, generated_at)

        notion_errors = notion_errors or []
        drive_errors = drive_errors or []

        if dry_run:
            print(f"[dry-run] Would write Notion index to: {notion_path}")
            print(f"[dry-run] Would write Drive index to: {drive_path}")
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

        status = "ok"
        if notion_errors or drive_errors:
            status = "error"

        summary = MasterIndexSummary(
            status=status,
            output_dir.mkdir(parents=True, exist_ok=True)
            notion_path.write_text(notion_markdown, encoding="utf-8")
            drive_path.write_text(drive_markdown, encoding="utf-8")

        summary = MasterIndexSummary(
            status="ok",
            dry_run=dry_run,
            notion_count=len(notion_records),
            drive_count=len(drive_records),
            output_dir=output_dir,
            notion_output=None if dry_run else notion_path,
            drive_output=None if dry_run else drive_path,
            notion_errors=notion_errors or None,
            drive_errors=drive_errors or None,
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
        message = """Required adapters not ready: Notion ({}) Drive ({})""".format(
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
        timestamp = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        line = (
            f"{timestamp} module=master_index status={summary.status} "
            f"dry_run={summary.dry_run} notion={summary.notion_count} "
            f"drive={summary.drive_count}"
        )
        if summary.output_dir:
            line += f" output={summary.output_dir}"
        if summary.message:
            line += f" message={summary.message}"
            f"{timestamp} module=master_index dry_run={summary.dry_run} "
            f"notion={summary.notion_count} drive={summary.drive_count}"
        )
        if summary.output_dir:
            line += f" output={summary.output_dir}"
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")


# ----------------------------------------------------------------------
# Notion helpers


def collect_notion_pages(
    notion_module: "NotionAccessModule",
    root_ids: Sequence[str],
    *,
    max_depth: int = 0,
    page_size: int = 100,
    limit: int = MAX_NOTION_ITEMS,
) -> Tuple[List[Dict[str, str]], List[str]]:
    from .notion.module import NotionAccessModule

    if not isinstance(notion_module, NotionAccessModule):
        return [], ["Notion module unavailable"]
    client, error = notion_module._build_client()  # type: ignore[attr-defined]
    if not client:
        return [], [error or "Notion client unavailable"]

    queue: deque[Tuple[str, int, List[str]]] = deque()
    for root in root_ids:
        if root:
            queue.append((root, 0, []))

    visited: set[str] = set()
    records: List[Dict[str, str]] = []
    errors: List[str] = []
    depth_limit = max_depth if max_depth and max_depth > 0 else None

    while queue and len(records) < limit:
        page_id, depth, ancestors = queue.popleft()
        if page_id in visited:
            continue
        visited.add(page_id)
        try:
            page = client.pages_retrieve(page_id)
        except NotionAPIError as exc:
            errors.append(f"Page {page_id}: {exc.message}")
            continue

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

        if len(records) >= limit:
            break

        if depth_limit is not None and depth >= depth_limit:
            continue

        next_cursor: Optional[str] = None
        while True:
            try:
                children = client.blocks_children_list(
                    page_id,
                    page_size=min(page_size, 100),
                    start_cursor=next_cursor,
                )
            except NotionAPIError as exc:
                errors.append(f"Children {page_id}: {exc.message}")
                break

            for block in children.get("results", []):
                if not isinstance(block, dict):
                    continue
                block_type = block.get("type")
                child_id = block.get("id")
                if block_type == "child_page" and child_id:
                    next_path = ancestors + [_sanitize_segment(title or "(untitled)")]
                    queue.append((child_id, depth + 1, next_path))
                elif block_type == "link_to_page":
                    target = block.get("link_to_page", {})
                    if isinstance(target, dict) and target.get("type") == "page_id":
                        target_id = target.get("page_id")
                        if target_id:
                            next_path = ancestors + [_sanitize_segment(title or "(untitled)")]
                            queue.append((target_id, depth + 1, next_path))
            if not children.get("has_more"):
                break
            next_cursor = children.get("next_cursor")
            if not next_cursor:
                break

    return records[:limit], errors


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
) -> Tuple[List[Dict[str, str]], List[str]]:
    from .modules.google_drive import GoogleDriveModule

    if not isinstance(drive_module, GoogleDriveModule):
        return [], ["Google Drive module unavailable"]

    service, error = drive_module.ensure_service()
    if not service:
        return [], [error or "Google Drive service unavailable"]

    whitelist = {value for value in mime_whitelist or [] if value}
    depth_limit = max_depth if max_depth and max_depth > 0 else None
    size = page_size if page_size and page_size > 0 else 200

    queue: deque[Tuple[str, int, List[str]]] = deque()
    for root in root_ids:
        if root:
            queue.append((root, 0, []))

    visited: set[str] = set()
    records: List[Dict[str, str]] = []
    errors: List[str] = []
    shortcut_cache: Dict[str, Dict[str, object]] = {}

    while queue and len(records) < limit:
        file_id, depth, ancestors = queue.popleft()
        if not file_id or file_id in visited:
            continue
        visited.add(file_id)
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
            if len(records) >= limit:
                break

        if mime_type == "application/vnd.google-apps.folder":
            if depth_limit is not None and depth >= depth_limit:
                continue
            query = f"'{file_id}' in parents and trashed = false"
            page_token: Optional[str] = None
            while True:
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
                for child in response.get("files", []):
                    child_id = child.get("id")
                    if child_id:
                        queue.append((child_id, depth + 1, path_segments))
                page_token = response.get("nextPageToken")
                if not page_token:
                    break

    return records[:limit], errors


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
