from __future__ import annotations

import os
import re
import shutil
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional

from .unilog import write as log_event

_RUN_DIR_PATTERN = re.compile(r"^run_[^_]+_(\d{8}_\d{6})$")
_MASTER_INDEX_PATTERN = re.compile(r"^master_index_(\d{8}T\d{6}Z)$")
_TARGET_LABELS = ["reports/", "docs/master_index_reports/"]
_LOG_FILES = [
    Path("reports/all.log"),
    Path("reports/audit.log"),
    Path("reports/policy.log"),
    Path("reports/security.log"),
]


@dataclass
class RetentionCandidate:
    path: Path
    timestamp: datetime
    target: str
    kind: str = "dir"
    protected: bool = False


@dataclass
class RetentionReport:
    keep_count: int
    dry_run: bool
    targets: List[str] = field(default_factory=lambda: list(_TARGET_LABELS))
    kept_paths: List[Path] = field(default_factory=list)
    planned_prune_paths: List[Path] = field(default_factory=list)
    pruned_paths: List[Path] = field(default_factory=list)
    planned_truncations: List[Path] = field(default_factory=list)
    truncated_files: List[Path] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    max_log_lines: int = 0

    def summary_line(self) -> str:
        prune_count = len(self.planned_prune_paths)
        return (
            f"Keeping: {self.keep_count} • Pruning: {prune_count} • "
            f"Targets: {', '.join(self.targets)}"
        )


def retention_enabled() -> bool:
    return _env_bool("RETENTION_ENABLE", default=True)


def prune_old_runs(
    *,
    keep_count: Optional[int] = None,
    dry_run: bool,
    current_run_id: Optional[str] = None,
    verbose: bool = False,
) -> RetentionReport:
    keep_value = keep_count if keep_count is not None else _env_int("LOG_RETENTION_RUNS", 20)
    keep_value = max(0, keep_value)
    max_log_lines = _env_int("UNIFIED_MAX_LINES", 25_000)

    report = RetentionReport(keep_count=keep_value, dry_run=dry_run, max_log_lines=max_log_lines)

    candidates = _collect_candidates(current_run_id)
    kept, prune_candidates = _plan_candidates(candidates, keep_value)
    report.kept_paths.extend(kept)
    report.planned_prune_paths.extend(candidate.path for candidate in prune_candidates)

    log_event(
        "retention.scan",
        {
            "keep_count": keep_value,
            "prune_count": len(report.planned_prune_paths),
            "keep_paths": _string_list(report.kept_paths, limit=50),
            "prune_paths": _string_list(report.planned_prune_paths, limit=50),
            "dry_run": dry_run,
        },
    )

    if verbose:
        mode = "[dry-run]" if dry_run else "[run]"
        print(f"{mode} Retention plan: keep {len(report.kept_paths)}, prune {len(report.planned_prune_paths)}")

    for candidate in prune_candidates:
        path = candidate.path
        if not path.exists():
            continue
        if dry_run:
            if verbose:
                print(f"[dry-run] Would delete {path}")
            continue
        try:
            if candidate.kind == "dir":
                shutil.rmtree(path)
            else:
                path.unlink()
        except OSError as exc:
            message = f"Failed to delete {path}: {exc}"
            report.errors.append(message)
            log_event("retention.error", {"path": str(path), "error": str(exc)})
            if verbose:
                print(message)
        else:
            report.pruned_paths.append(path)
            log_event("retention.prune", {"path": str(path), "kind": candidate.kind})
            if verbose:
                print(f"Deleted {path}")

    planned_truncations, truncated_files = _truncate_logs(max_log_lines, dry_run, verbose, report)
    report.planned_truncations.extend(planned_truncations)
    report.truncated_files.extend(truncated_files)

    log_event(
        "retention.summary",
        {
            "kept_dirs": len(report.kept_paths),
            "pruned_dirs": len(report.pruned_paths) if not dry_run else 0,
            "truncated_files": len(report.truncated_files),
            "dry_run": dry_run,
        },
    )

    if dry_run and verbose and report.planned_prune_paths:
        print("Dry-run complete. No files were deleted.")
    return report


def _collect_candidates(current_run_id: Optional[str]) -> List[RetentionCandidate]:
    current_dir_name = f"run_{current_run_id}" if current_run_id else None
    current_timestamp = _timestamp_from_run_id(current_run_id) if current_run_id else None

    candidates: List[RetentionCandidate] = []
    candidates.extend(_report_run_candidates(current_dir_name))
    candidates.extend(_master_index_candidates(current_timestamp))
    return candidates


def _report_run_candidates(current_dir_name: Optional[str]) -> List[RetentionCandidate]:
    base = Path("reports")
    if not base.exists():
        return []
    items: List[RetentionCandidate] = []
    for entry in base.iterdir():
        if not entry.is_dir():
            continue
        match = _RUN_DIR_PATTERN.match(entry.name)
        if not match:
            continue
        timestamp = _parse_timestamp(match.group(1), "%Y%m%d_%H%M%S")
        if timestamp is None:
            continue
        protected = bool(current_dir_name and entry.name == current_dir_name)
        items.append(
            RetentionCandidate(
                path=entry,
                timestamp=timestamp,
                target="reports/",
                protected=protected,
            )
        )
    return items


def _master_index_candidates(current_timestamp: Optional[datetime]) -> List[RetentionCandidate]:
    base = Path("docs/master_index_reports")
    if not base.exists():
        return []
    items: List[RetentionCandidate] = []
    for entry in base.iterdir():
        if not entry.is_dir():
            continue
        match = _MASTER_INDEX_PATTERN.match(entry.name)
        if not match:
            continue
        timestamp = _parse_timestamp(match.group(1), "%Y%m%dT%H%M%SZ")
        if timestamp is None:
            continue
        protected = False
        if current_timestamp is not None:
            delta = abs((timestamp - current_timestamp).total_seconds())
            if delta < 90:
                protected = True
        items.append(
            RetentionCandidate(
                path=entry,
                timestamp=timestamp,
                target="docs/master_index_reports/",
                protected=protected,
            )
        )
    return items


def _plan_candidates(
    candidates: Iterable[RetentionCandidate], keep_count: int
) -> tuple[List[Path], List[RetentionCandidate]]:
    grouped: dict[str, List[RetentionCandidate]] = {}
    for candidate in candidates:
        grouped.setdefault(candidate.target, []).append(candidate)

    kept_paths: List[Path] = []
    prune_candidates: List[RetentionCandidate] = []

    for target, items in grouped.items():
        items.sort(key=lambda cand: (cand.timestamp, cand.path.name), reverse=True)
        for index, candidate in enumerate(items):
            if index < keep_count or candidate.protected:
                kept_paths.append(candidate.path)
            else:
                prune_candidates.append(candidate)
    return kept_paths, prune_candidates


def _truncate_logs(
    max_lines: int,
    dry_run: bool,
    verbose: bool,
    report: RetentionReport,
) -> tuple[List[Path], List[Path]]:
    if max_lines <= 0:
        return [], []

    planned: List[Path] = []
    truncated: List[Path] = []
    for path in _LOG_FILES:
        if not path.exists():
            continue
        try:
            line_count, tail = _tail_lines(path, max_lines, keep_tail=not dry_run)
        except OSError as exc:
            message = f"Failed to read {path}: {exc}"
            report.errors.append(message)
            log_event("retention.error", {"path": str(path), "error": str(exc)})
            if verbose:
                print(message)
            continue
        if line_count <= max_lines:
            continue
        planned.append(path)
        if dry_run:
            if verbose:
                print(
                    f"[dry-run] Would truncate {path} to last {max_lines} lines (had {line_count})"
                )
            continue
        assert tail is not None
        try:
            path.write_text("".join(tail), encoding="utf-8")
        except OSError as exc:
            message = f"Failed to truncate {path}: {exc}"
            report.errors.append(message)
            log_event("retention.error", {"path": str(path), "error": str(exc)})
            if verbose:
                print(message)
            continue
        truncated.append(path)
        log_event("retention.truncate", {"path": str(path), "kept_lines": len(tail)})
        if verbose:
            print(f"Truncated {path} to {len(tail)} lines (was {line_count})")
    return planned, truncated


def _tail_lines(path: Path, max_lines: int, *, keep_tail: bool) -> tuple[int, List[str] | None]:
    buffer = deque(maxlen=max_lines) if keep_tail else None
    line_count = 0
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line_count += 1
            if buffer is not None:
                buffer.append(line)
    if buffer is None:
        return line_count, None
    return line_count, list(buffer)


def _parse_timestamp(value: str, fmt: str) -> Optional[datetime]:
    try:
        dt = datetime.strptime(value, fmt)
    except ValueError:
        return None
    return dt.replace(tzinfo=timezone.utc)


def _timestamp_from_run_id(run_id: Optional[str]) -> Optional[datetime]:
    if not run_id:
        return None
    parts = run_id.split("_")
    if len(parts) < 3:
        return None
    timestamp_text = "_".join(parts[-2:])
    return _parse_timestamp(timestamp_text, "%Y%m%d_%H%M%S")


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _string_list(paths: Iterable[Path], *, limit: int) -> List[str]:
    items = [str(path) for path in paths]
    if len(items) > limit:
        return items[:limit]
    return items
