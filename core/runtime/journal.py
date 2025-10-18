from __future__ import annotations

import json
import threading
import time
import uuid
import hashlib
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional


def _atomic_append(path: Path, lines: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = ""
    if path.exists():
        existing = path.read_text(encoding="utf-8")
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", dir=str(path.parent)) as tf:
        if existing:
            tf.write(existing)
            if not existing.endswith("\n"):
                tf.write("\n")
        for line in lines:
            tf.write(line.rstrip("\n") + "\n")
        tmp_name = tf.name
    Path(tmp_name).replace(path)


def _json_hash(obj: Dict[str, Any]) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class JournalManager:
    """Append-only journal + audit chain."""

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._journal_path = data_dir / "journal.log"
        self._audit_path = data_dir / "audit.log"
        self._lock = threading.Lock()
        self._last_journal_hash = ""
        self._last_audit_hash = ""
        self._idempotency: Dict[str, str] = {}
        self._journal_index: Dict[str, Dict[str, Any]] = {}
        self._recover()

    @property
    def journal_path(self) -> Path:
        return self._journal_path

    @property
    def audit_path(self) -> Path:
        return self._audit_path

    def _load_lines(self, path: Path) -> List[Dict[str, Any]]:
        if not path.exists():
            return []
        out: List[Dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def _recover(self) -> None:
        with self._lock:
            journal_entries = self._load_lines(self._journal_path)
            audit_entries = self._load_lines(self._audit_path)
            committed = {a.get("journal_id") for a in audit_entries if a.get("result") == "commit"}
            rolled_back = {a.get("journal_id") for a in audit_entries if a.get("result") in {"rollback", "replay"}}
            self._journal_index = {}
            self._idempotency = {}
            self._last_journal_hash = ""
            for entry in journal_entries:
                jid = str(entry.get("journal_id"))
                if not jid:
                    continue
                self._journal_index[jid] = entry
                self._last_journal_hash = _json_hash(entry)
                self._idempotency[str(entry.get("idempotency_key"))] = "pending"
            self._last_audit_hash = ""
            for entry in audit_entries:
                self._last_audit_hash = entry.get("hash", "")
                jid = str(entry.get("journal_id"))
                if jid and entry.get("result") == "commit":
                    self._idempotency[str(self._journal_index.get(jid, {}).get("idempotency_key"))] = "committed"
                elif jid:
                    self._idempotency[str(self._journal_index.get(jid, {}).get("idempotency_key"))] = "rolled_back"
            pending = {
                jid: entry
                for jid, entry in self._journal_index.items()
                if jid not in committed and jid not in rolled_back
            }
            for jid, entry in pending.items():
                self._record_audit_locked(jid, "rollback", detail="recovered_pending")
                self._idempotency[str(entry.get("idempotency_key"))] = "rolled_back"

    def prepare(
        self,
        *,
        run_id: str,
        actor: str,
        intent: str,
        idempotency_key: str,
        inputs_hash: str,
        proposal_hash: str,
        policy_version: str,
    ) -> Dict[str, Any]:
        with self._lock:
            existing_status = self._idempotency.get(idempotency_key)
            if existing_status == "committed":
                raise ValueError("idempotency_key_already_committed")
            journal_id = str(uuid.uuid4())
            entry = {
                "journal_id": journal_id,
                "run_id": run_id,
                "actor": actor,
                "intent": intent,
                "inputs_hash": inputs_hash,
                "proposal_hash": proposal_hash,
                "policy_version": policy_version,
                "idempotency_key": idempotency_key,
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "prev_hash": self._last_journal_hash,
            }
            digest = _json_hash(entry)
            _atomic_append(self._journal_path, [json.dumps(entry, separators=(",", ":"))])
            self._last_journal_hash = digest
            self._journal_index[journal_id] = entry
            self._idempotency[idempotency_key] = "pending"
            return entry

    def commit(self, journal_id: str, *, result: str = "commit") -> Dict[str, Any]:
        if result not in {"commit", "rollback", "replay"}:
            raise ValueError("invalid_result")
        with self._lock:
            return self._record_audit_locked(journal_id, result)

    def _record_audit_locked(self, journal_id: str, result: str, detail: Optional[str] = None) -> Dict[str, Any]:
        record = {
            "journal_id": journal_id,
            "result": result,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "prev_hash": self._last_audit_hash,
        }
        if detail:
            record["detail"] = detail
        record_hash = _json_hash(record)
        record["hash"] = record_hash
        _atomic_append(self._audit_path, [json.dumps(record, separators=(",", ":"))])
        self._last_audit_hash = record_hash
        entry = self._journal_index.get(journal_id)
        if entry:
            self._idempotency[str(entry.get("idempotency_key"))] = "committed" if result == "commit" else "rolled_back"
        return record

    def status_for_idempotency(self, key: str) -> Optional[str]:
        return self._idempotency.get(key)

    def as_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "journal_path": str(self._journal_path),
                "audit_path": str(self._audit_path),
                "idempotency": dict(self._idempotency),
            }
