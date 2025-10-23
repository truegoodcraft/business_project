from __future__ import annotations

import json
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from core.adapters.fs.executor import LocalFSExecutor
from core.domain.bundles import build_bundle
from core.settings.reader import load_reader_settings


def _utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _norm_paths(roots: Iterable[str]) -> List[str]:
    result = []
    for root in roots:
        try:
            result.append(str(Path(root).resolve()))
        except Exception:
            continue
    return result


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _ndjson_append(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, separators=(",", ":")))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


@dataclass
class ItemResult:
    item: Dict[str, Any]
    status: str
    resolved_path: Optional[str] = None
    reason: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "item": self.item,
            "status": self.status,
        }
        if self.resolved_path is not None:
            data["resolved_path"] = self.resolved_path
        if self.reason:
            data["reason"] = self.reason
        if self.warnings:
            data["warnings"] = list(self.warnings)
        return data


@dataclass
class BatchPreview:
    op: str
    results: List[ItemResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"op": self.op, "results": [item.to_dict() for item in self.results]}


class Journal:
    def __init__(self, path: Path):
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, payload: Dict[str, Any]) -> None:
        payload = dict(payload)
        payload.setdefault("ts", _utc_now())
        _ndjson_append(self._path, payload)


class PlanEngine:
    def __init__(self):
        self._data_root = Path("data")
        self._journal_root = self._data_root / "journal"
        self._tmp_root = self._data_root / "tmp" / "bundles"
        self._jobs_path = self._data_root / "jobs.json"
        self._audit_path = self._data_root / "audit.log"
        self._idempo_path = self._data_root / "idempo.jsonl"
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._jobs_lock = threading.Lock()
        self._idempo: Dict[str, str] = {}
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._load_jobs()
        self._load_idempo()
        self._fs_executor = LocalFSExecutor(self._current_roots())

    # region helpers
    def _current_roots(self) -> List[str]:
        settings = load_reader_settings()
        roots = settings.get("local_roots", []) if isinstance(settings, dict) else []
        if not isinstance(roots, list):
            return []
        return _norm_paths([str(item) for item in roots if isinstance(item, str)])

    def _reload_executor(self) -> None:
        self._fs_executor = LocalFSExecutor(self._current_roots())

    def _load_jobs(self) -> None:
        try:
            data = json.loads(self._jobs_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self._jobs = data
        except FileNotFoundError:
            self._jobs = {}
        except json.JSONDecodeError:
            self._jobs = {}

    def _persist_jobs(self) -> None:
        self._jobs_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._jobs_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._jobs, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self._jobs_path)

    def _load_idempo(self) -> None:
        try:
            with self._idempo_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    try:
                        obj = json.loads(line.strip())
                        if not isinstance(obj, dict):
                            continue
                        key = obj.get("key")
                        job_id = obj.get("job_id")
                        if isinstance(key, str) and isinstance(job_id, str):
                            self._idempo[key] = job_id
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            self._idempo = {}

    def _record_idempo(self, key: str, job_id: str) -> None:
        if not key:
            return
        self._idempo[key] = job_id
        _ndjson_append(self._idempo_path, {"key": key, "job_id": job_id, "ts": _utc_now()})

    def _update_job(self, job_id: str, **updates: Any) -> None:
        with self._jobs_lock:
            job = self._jobs.setdefault(job_id, {})
            job.update(updates)
            self._persist_jobs()

    def _update_progress(self, job_id: str, done: int) -> None:
        with self._jobs_lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            total = job.get("progress", {}).get("total", 0)
            job["progress"] = {"done": done, "total": total}
            self._persist_jobs()

    # endregion

    # region preview
    def preview(self, batches: List[Dict[str, Any]]) -> Dict[str, Any]:
        self._reload_executor()
        batch_results: List[BatchPreview] = []
        total = ok = deny = error = 0

        for batch in batches:
            op = str(batch.get("op") or "").strip()
            items = batch.get("items")
            constraint = batch.get("constraints") if isinstance(batch.get("constraints"), dict) else {}
            if not isinstance(items, list):
                items = []
            if len(items) > 500:
                raise ValueError("batch_limit_exceeded")
            scope = constraint.get("scope") if isinstance(constraint, dict) else None
            if scope not in ("local_only", None):
                results = [
                    ItemResult(
                        item=item if isinstance(item, dict) else {},
                        status="DENY",
                        reason="unsupported_scope",
                    )
                    for item in items
                ]
                batch_results.append(BatchPreview(op=op, results=results))
                deny += len(results)
                total += len(results)
                continue

            if op in ("rename.batch", "move.batch"):
                results = []
                for item in items:
                    if not isinstance(item, dict):
                        results.append(ItemResult(item={}, status="ERROR", reason="invalid_item"))
                        error += 1
                        total += 1
                        continue
                    old_raw = item.get("old_path")
                    new_raw = item.get("new_path")
                    if not isinstance(old_raw, str) or not isinstance(new_raw, str) or not old_raw or not new_raw:
                        results.append(ItemResult(item=item, status="DENY", reason="missing_paths"))
                        deny += 1
                        total += 1
                        continue
                    old_path = Path(str(old_raw))
                    new_path = Path(str(new_raw))
                    if not old_path.exists():
                        results.append(ItemResult(item=item, status="ERROR", reason="missing_source"))
                        error += 1
                        total += 1
                        continue
                    warnings: List[str] = []
                    if not self._fs_executor.is_allowed(old_path) or not self._fs_executor.is_allowed(new_path):
                        results.append(ItemResult(item=item, status="DENY", reason="out_of_scope"))
                        deny += 1
                        total += 1
                        continue
                    collision_mode = constraint.get("collision", "append-1") if isinstance(constraint, dict) else "append-1"
                    collision = self._fs_executor.collision_resolve(new_path, collision_mode)
                    if not self._fs_executor.same_drive(old_path, collision.resolved_path):
                        warnings.append("cross_drive_copy_quarantine")
                    results.append(
                        ItemResult(
                            item=item,
                            status="OK",
                            resolved_path=str(collision.resolved_path),
                            warnings=warnings,
                        )
                    )
                    ok += 1
                    total += 1
                batch_results.append(BatchPreview(op=op, results=results))
                continue

            if op == "bundle.create":
                results = []
                target_raw = batch.get("target_path")
                target_path = Path(str(target_raw)) if isinstance(target_raw, str) and target_raw else None
                mode = str(batch.get("mode") or "zip_bundle")
                if not target_path:
                    for item in items:
                        results.append(ItemResult(item=item if isinstance(item, dict) else {}, status="ERROR", reason="missing_target"))
                        error += 1
                        total += 1
                    batch_results.append(BatchPreview(op=op, results=results))
                    continue
                if not self._fs_executor.is_allowed(target_path):
                    for item in items:
                        results.append(ItemResult(item=item if isinstance(item, dict) else {}, status="DENY", reason="out_of_scope"))
                        deny += 1
                        total += 1
                    batch_results.append(BatchPreview(op=op, results=results))
                    continue
                collision_mode = constraint.get("collision", "append-1") if isinstance(constraint, dict) else "append-1"
                collision = self._fs_executor.collision_resolve(target_path, collision_mode)
                for item in items:
                    if not isinstance(item, dict):
                        results.append(ItemResult(item={}, status="ERROR", reason="invalid_item"))
                        error += 1
                        total += 1
                        continue
                    path_hint = item.get("path") or item.get("source_path") or item.get("old_path")
                    if not isinstance(path_hint, str) or not path_hint:
                        results.append(ItemResult(item=item, status="ERROR", reason="missing_input_path"))
                        error += 1
                        total += 1
                        continue
                    source_path = Path(str(path_hint))
                    if not source_path.exists():
                        results.append(ItemResult(item=item, status="ERROR", reason="missing_source"))
                        error += 1
                        total += 1
                        continue
                    if not self._fs_executor.is_allowed(source_path):
                        results.append(ItemResult(item=item, status="DENY", reason="out_of_scope"))
                        deny += 1
                        total += 1
                        continue
                    warnings: List[str] = []
                    results.append(
                        ItemResult(
                            item=item,
                            status="OK",
                            resolved_path=str(collision.resolved_path),
                            warnings=warnings,
                        )
                    )
                    ok += 1
                    total += 1
                batch_results.append(BatchPreview(op=op, results=results))
                continue

            # unknown op
            results = [
                ItemResult(
                    item=item if isinstance(item, dict) else {},
                    status="DENY",
                    reason="unsupported_op",
                )
                for item in items
            ]
            batch_results.append(BatchPreview(op=op, results=results))
            deny += len(results)
            total += len(results)

        summary = {"total": total, "ok": ok, "deny": deny, "error": error}
        return {"summary": summary, "batches": [batch.to_dict() for batch in batch_results]}

    # endregion

    # region execution
    def execute(self, batches: List[Dict[str, Any]], *, label: Optional[str] = None) -> Dict[str, Any]:
        # idempotency check
        duplicate_job: Optional[str] = None
        for batch in batches:
            key = str(batch.get("idempotency_key") or "").strip()
            if not key:
                continue
            existing = self._idempo.get(key)
            if existing:
                if duplicate_job and duplicate_job != existing:
                    raise ValueError("idempotency_conflict")
                duplicate_job = existing
        if duplicate_job:
            return {"job_id": duplicate_job, "accepted": False, "duplicate": True}

        preview = self.preview(batches)
        job_id = uuid.uuid4().hex
        total = _safe_int(preview.get("summary", {}).get("total"), 0)
        job_record = {
            "job_id": job_id,
            "status": "running",
            "progress": {"done": 0, "total": total},
            "errors": [],
            "started_at": _utc_now(),
            "finished_at": None,
            "label": label,
            "journal": str(self._journal_root / f"{job_id}.ndjson"),
        }
        with self._jobs_lock:
            self._jobs[job_id] = job_record
            self._persist_jobs()

        for batch in batches:
            key = str(batch.get("idempotency_key") or "").strip()
            if key:
                self._record_idempo(key, job_id)

        self._executor.submit(self._run_job, job_id, batches, preview)
        return {"job_id": job_id, "accepted": True}

    def _run_job(self, job_id: str, batches: List[Dict[str, Any]], preview: Dict[str, Any]) -> None:
        journal_path = self._journal_root / f"{job_id}.ndjson"
        journal = Journal(journal_path)
        journal.record({"type": "prepare", "job_id": job_id, "batches": len(batches)})
        done = 0
        rollback_map: List[Dict[str, Any]] = []
        errors: List[str] = []
        try:
            for batch, preview_batch in zip(batches, preview.get("batches", [])):
                op = batch.get("op")
                if op in ("rename.batch", "move.batch"):
                    constraint = batch.get("constraints") if isinstance(batch.get("constraints"), dict) else {}
                    collision_mode = constraint.get("collision", "append-1") if isinstance(constraint, dict) else "append-1"
                    for item_result in preview_batch.get("results", []):
                        status = item_result.get("status")
                        if status != "OK":
                            continue
                        item = item_result.get("item", {})
                        src = Path(str(item.get("old_path")))
                        dest = Path(str(item_result.get("resolved_path")))
                        final_path, meta = self._fs_executor.rename_or_move(
                            src, dest, collision_mode=collision_mode
                        )
                        rollback_entry = {
                            "op": "move",
                            "src": str(final_path),
                            "dest": str(src),
                        }
                        rollback_map.append(rollback_entry)
                        done += 1
                        self._update_progress(job_id, done)
                        journal.record({"type": "step", "op": op, "src": str(src), "dest": str(final_path)})
                elif op == "bundle.create":
                    preview_results = [
                        res
                        for res in preview_batch.get("results", [])
                        if isinstance(res, dict) and res.get("status") == "OK"
                    ]
                    target_candidate = None
                    if preview_results:
                        rp = preview_results[0].get("resolved_path")
                        if rp:
                            target_candidate = Path(str(rp))
                    if not target_candidate:
                        fallback = batch.get("target_path")
                        target_candidate = (
                            Path(str(fallback)) if isinstance(fallback, str) and fallback else None
                        )
                    if not target_candidate:
                        continue
                    inputs: List[str] = []
                    for item in batch.get("items", []):
                        if isinstance(item, dict):
                            source = item.get("path") or item.get("source_path") or item.get("old_path")
                            if source:
                                inputs.append(str(source))
                    if not inputs:
                        raise RuntimeError("bundle_missing_inputs")
                    tmp_dir = self._tmp_root / job_id
                    tmp_path = tmp_dir / f"bundle-{uuid.uuid4().hex}.tmp"
                    mode = str(batch.get("mode") or "zip_bundle")
                    result = build_bundle(mode, inputs, tmp_path)
                    target = target_candidate
                    target.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(tmp_path, target)
                    manifest_path = Path(str(target) + ".bundle.json")
                    manifest = {
                        "inputs": inputs,
                        "mode": batch.get("mode"),
                        "meta": batch.get("meta", {}),
                        "bytes": result.get("bytes_written"),
                        "warnings": result.get("warnings", []),
                    }
                    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
                    rollback_map.append({"op": "remove", "path": str(target)})
                    done += 1
                    self._update_progress(job_id, done)
                    journal.record({"type": "step", "op": op, "target": str(target), "inputs": inputs})
                else:
                    continue
        except Exception as exc:  # pragma: no cover - unexpected failure
            errors.append(str(exc))
            journal.record({"type": "error", "error": str(exc)})
            status = "failed"
        else:
            status = "done"
        finally:
            finished = _utc_now()
            with self._jobs_lock:
                job = self._jobs.get(job_id, {})
                total_expected = job.get("progress", {}).get("total", done)
                job.update(
                    {
                        "status": status,
                        "progress": {"done": done, "total": total_expected},
                        "errors": errors,
                        "finished_at": finished,
                        "journal": str(journal_path),
                        "rollback": rollback_map,
                    }
                )
                self._persist_jobs()
            journal.record({"type": "finalize", "status": status, "errors": errors, "rollback": rollback_map})
            self._append_audit(job_id, batches, status, errors, finished)

    def _append_audit(
        self,
        job_id: str,
        batches: List[Dict[str, Any]],
        status: str,
        errors: List[str],
        finished_at: str,
    ) -> None:
        prev_hash = ""
        if self._audit_path.exists():
            try:
                last_line = self._audit_path.read_text(encoding="utf-8").strip().splitlines()[-1]
                obj = json.loads(last_line)
                prev_hash = obj.get("hash") or ""
            except Exception:
                prev_hash = ""
        payload = {
            "job_id": job_id,
            "status": status,
            "finished_at": finished_at,
            "batches": [batch.get("meta", {}).get("hash") for batch in batches],
            "errors": errors,
            "prev_hash": prev_hash,
        }
        blob = json.dumps(payload, sort_keys=True).encode("utf-8")
        import hashlib

        payload["hash"] = hashlib.sha256(blob).hexdigest()
        _ndjson_append(self._audit_path, payload)

    # endregion

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._jobs_lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None

    def list_jobs(self) -> List[Dict[str, Any]]:
        with self._jobs_lock:
            return [dict(job) for job in self._jobs.values()]

    def audit_log(self) -> str:
        if not self._audit_path.exists():
            return ""
        return self._audit_path.read_text(encoding="utf-8")


ENGINE = PlanEngine()

