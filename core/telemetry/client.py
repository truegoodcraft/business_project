from __future__ import annotations

import json
import logging
import platform
import threading
import time
import uuid
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from core.appdata.paths import state_dir
from core.config.manager import load_config
from core.version import VERSION

_log = logging.getLogger(__name__)

SCHEMA_VERSION = "1.0"
TELEMETRY_ENDPOINT = "https://lighthouse.buscore.ca/telemetry/v1/events"
MAX_QUEUE_EVENTS = 100
MAX_DEAD_LETTER_EVENTS = 100
MAX_ATTEMPTS = 3
REQUEST_TIMEOUT_SECONDS = 2.0
RETRY_DELAYS_SECONDS = (1.0, 5.0, 30.0)

EVENT_CATEGORIES: dict[str, tuple[str, ...]] = {
    "installation_release": (
        "installation_first_launch", "version_first_seen",
        "update_check_startup", "update_check_manual", "update_staged", "update_failure",
    ),
    "workflow_milestone": (
        "first_stock_recorded", "first_contact_created", "first_recipe_created",
        "first_manufacturing_run_completed", "first_job_completed",
        "first_invoice_issued", "first_finance_entry_recorded",
        "first_backup_exported", "restore_attempted",
        "restore_completed", "import_completed", "import_failed",
    ),
    "reliability": (
        "startup_failure", "backup_failure", "restore_failure",
        "unhandled_application_error", "migration_failure",
    ),
}
ALLOWED_EVENT_NAMES = frozenset(name for names in EVENT_CATEGORIES.values() for name in names)
MILESTONE_EVENT_NAMES = frozenset(
    ("installation_first_launch", "version_first_seen")
    + tuple(name for name in EVENT_CATEGORIES["workflow_milestone"] if name.startswith("first_"))
)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _timestamp_from_epoch(value: float) -> str:
    return datetime.fromtimestamp(value, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _os_category() -> str:
    system = platform.system().strip().lower()
    if system == "windows":
        return "windows"
    if system == "linux":
        return "linux"
    if system == "darwin":
        return "macos"
    return "other"


def _read_json(path: Path, default: Any) -> Any:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value
    except Exception:
        return default


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, separators=(",", ":")), encoding="utf-8")
    tmp.replace(path)


@dataclass(frozen=True)
class DeliveryResult:
    status: int | None
    acknowledged_event_ids: frozenset[str] = frozenset()
    error_category: str | None = None


def _delivery_result(status: int, raw: bytes) -> DeliveryResult:
    body: Any = None
    try:
        body = json.loads(raw.decode("utf-8")) if raw else None
    except (UnicodeDecodeError, json.JSONDecodeError):
        body = None
    acknowledged = frozenset(
        str(value)
        for value in (body.get("acknowledged_event_ids", []) if isinstance(body, dict) else [])
        if isinstance(value, str)
    )
    error = body.get("error") if isinstance(body, dict) and isinstance(body.get("error"), str) else None
    return DeliveryResult(status=status, acknowledged_event_ids=acknowledged, error_category=error)


def _default_sender(payload: dict[str, Any]) -> DeliveryResult:
    request = urllib.request.Request(
        TELEMETRY_ENDPOINT,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": f"BUS-Core/{VERSION}",
        },
    )
    try:
        # B310 is a false positive here: Request receives the immutable, audited
        # HTTPS-only TELEMETRY_ENDPOINT above rather than user-controlled input.
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:  # nosec B310
            return _delivery_result(int(response.status), response.read(MAX_QUEUE_EVENTS * 1024))
    except urllib.error.HTTPError as exc:
        return _delivery_result(int(exc.code), exc.read(MAX_QUEUE_EVENTS * 1024))


class TelemetryClient:
    """Local queue and strict payload constructor.

    The public emit API accepts only an allowlisted event name. No arbitrary
    properties or business objects can enter serialized telemetry.
    """

    def __init__(
        self,
        *,
        state_path: Path | None = None,
        queue_path: Path | None = None,
        dead_letter_path: Path | None = None,
        sender: Callable[[dict[str, Any]], DeliveryResult | int | dict[str, Any]] | None = None,
        enabled_getter: Callable[[], bool] | None = None,
        channel_getter: Callable[[], str] | None = None,
        now: Callable[[], float] | None = None,
        uuid_factory: Callable[[], uuid.UUID] | None = None,
        start_background: bool = True,
    ) -> None:
        root = state_dir()
        self.state_path = state_path or (root / "telemetry_state.json")
        self.queue_path = queue_path or (root / "telemetry_queue.json")
        self.dead_letter_path = dead_letter_path or (root / "telemetry_dead_letter.json")
        self.sender = sender or _default_sender
        self.enabled_getter = enabled_getter or self._configured_enabled
        self.channel_getter = channel_getter or (lambda: load_config().updates.channel)
        self.now = now or time.time
        self.uuid_factory = uuid_factory or uuid.uuid4
        self.start_background = start_background
        self._lock = threading.RLock()
        self._worker: threading.Thread | None = None

    @staticmethod
    def _configured_enabled() -> bool:
        cfg = load_config().telemetry
        return bool(cfg.enabled and cfg.disclosure_acknowledged)

    def _state(self) -> dict[str, Any]:
        raw = _read_json(self.state_path, {})
        if not isinstance(raw, dict):
            raw = {}
        milestones = raw.get("milestones")
        raw["milestones"] = milestones if isinstance(milestones, list) else []
        for key in ("acknowledged_count", "rejected_count", "dead_letter_count"):
            try:
                raw[key] = max(0, int(raw.get(key, 0) or 0))
            except (TypeError, ValueError):
                raw[key] = 0
        raw["last_successful_delivery_at"] = raw.get("last_successful_delivery_at")
        raw["last_status"] = raw.get("last_status")
        raw["last_error_category"] = raw.get("last_error_category")
        return raw

    def _queue(self) -> list[dict[str, Any]]:
        raw = _read_json(self.queue_path, [])
        return raw if isinstance(raw, list) else []

    def _dead_letters(self) -> list[dict[str, Any]]:
        raw = _read_json(self.dead_letter_path, [])
        return raw if isinstance(raw, list) else []

    def _deduplication_key(self, event_name: str, should_deduplicate: bool) -> str | None:
        if not should_deduplicate:
            return None
        if event_name == "version_first_seen":
            return f"{event_name}:{VERSION}"
        return event_name

    @staticmethod
    def _queued_deduplication_key(item: dict[str, Any]) -> str | None:
        explicit = item.get("deduplication_key")
        if isinstance(explicit, str) and explicit:
            return explicit
        payload = item.get("payload")
        if not isinstance(payload, dict):
            return None
        event_name = payload.get("event_name")
        if event_name == "version_first_seen":
            context = payload.get("context")
            version = context.get("app_version") if isinstance(context, dict) else None
            return f"{event_name}:{version}" if isinstance(version, str) and version else None
        if isinstance(event_name, str) and event_name in MILESTONE_EVENT_NAMES:
            return event_name
        return None

    def build_payload(self, event_name: str) -> dict[str, Any]:
        if event_name not in ALLOWED_EVENT_NAMES:
            raise ValueError("event name is not allowlisted")
        channel = self.channel_getter()
        if channel not in {"stable", "test", "partner-3dque", "lts-1.1", "security-hotfix"}:
            channel = "stable"
        return {
            "schema_version": SCHEMA_VERSION,
            "event_id": str(self.uuid_factory()),
            "event_name": event_name,
            "client_ts": _utc_timestamp(),
            "context": {
                "app_version": VERSION,
                "release_channel": channel,
                "os_category": _os_category(),
            },
        }

    def emit(self, event_name: str, *, deduplicate: bool | None = None) -> bool:
        if event_name not in ALLOWED_EVENT_NAMES or not self.enabled_getter():
            return False
        should_deduplicate = event_name in MILESTONE_EVENT_NAMES if deduplicate is None else deduplicate
        try:
            with self._lock:
                state = self._state()
                milestones = set(str(value) for value in state.get("milestones", []))
                deduplication_key = self._deduplication_key(event_name, should_deduplicate)
                queue = self._queue()
                pending_keys = {
                    key
                    for item in queue
                    if (key := self._queued_deduplication_key(item)) is not None
                }
                if deduplication_key and (deduplication_key in milestones or deduplication_key in pending_keys):
                    return False
                queue.append({
                    "payload": self.build_payload(event_name),
                    "attempts": 0,
                    "next_attempt_at": self.now(),
                    "deduplication_key": deduplication_key,
                })
                if len(queue) > MAX_QUEUE_EVENTS:
                    overflow = queue[:-MAX_QUEUE_EVENTS]
                    queue = queue[-MAX_QUEUE_EVENTS:]
                    dead_letters = self._dead_letters()
                    for dropped in overflow:
                        dead_letters.append(self._dead_letter_record(dropped, None, "queue_overflow"))
                    _write_json(self.dead_letter_path, dead_letters[-MAX_DEAD_LETTER_EVENTS:])
                    state["dead_letter_count"] += len(overflow)
                    state["last_error_category"] = "queue_overflow"
                    _write_json(self.state_path, state)
                _write_json(self.queue_path, queue)
        except Exception:
            _log.debug("telemetry queue write skipped", exc_info=True)
            return False
        if self.start_background:
            self._start_worker()
        return True

    def _start_worker(self) -> None:
        with self._lock:
            if self._worker is not None and self._worker.is_alive():
                return
            self._worker = threading.Thread(target=self.flush, name="buscore-telemetry", daemon=True)
            self._worker.start()

    def flush(self, *, max_events: int = 10) -> int:
        if not self.enabled_getter():
            return 0
        processed = 0
        for _ in range(max_events):
            with self._lock:
                queue = self._queue()
                index = next(
                    (i for i, item in enumerate(queue) if float(item.get("next_attempt_at", 0)) <= self.now()),
                    None,
                )
                if index is None:
                    break
                item = dict(queue[index])
            delivery = DeliveryResult(status=None, error_category="transport_error")
            try:
                delivery = self._normalize_delivery_result(self.sender(dict(item.get("payload") or {})))
            except Exception:
                delivery = DeliveryResult(status=None, error_category="transport_error")
            with self._lock:
                queue = self._queue()
                event_id = (item.get("payload") or {}).get("event_id")
                current_index = next(
                    (i for i, queued in enumerate(queue) if (queued.get("payload") or {}).get("event_id") == event_id),
                    None,
                )
                if current_index is None:
                    continue
                state = self._state()
                state["last_status"] = delivery.status
                acknowledged = (
                    delivery.status is not None
                    and 200 <= delivery.status < 300
                    and event_id in delivery.acknowledged_event_ids
                )
                if acknowledged:
                    queue.pop(current_index)
                    state["acknowledged_count"] += 1
                    state["last_successful_delivery_at"] = _timestamp_from_epoch(self.now())
                    state["last_error_category"] = None
                    deduplication_key = self._queued_deduplication_key(item)
                    if deduplication_key:
                        milestones = set(str(value) for value in state.get("milestones", []))
                        milestones.add(str(deduplication_key))
                        state["milestones"] = sorted(milestones)
                elif delivery.status is not None and 400 <= delivery.status < 500 and delivery.status != 429:
                    queue.pop(current_index)
                    state["rejected_count"] += 1
                    state["dead_letter_count"] += 1
                    state["last_error_category"] = delivery.error_category or f"http_{delivery.status}"
                    self._append_dead_letter(item, delivery.status, state["last_error_category"])
                else:
                    attempts = int(item.get("attempts", 0)) + 1
                    error_category = delivery.error_category
                    if delivery.status is not None and 200 <= delivery.status < 300:
                        error_category = "missing_acknowledgement"
                    elif not error_category:
                        error_category = f"http_{delivery.status}" if delivery.status is not None else "transport_error"
                    state["last_error_category"] = error_category
                    if attempts >= MAX_ATTEMPTS:
                        queue.pop(current_index)
                        state["dead_letter_count"] += 1
                        self._append_dead_letter(item, delivery.status, error_category)
                    else:
                        item["attempts"] = attempts
                        item["next_attempt_at"] = self.now() + RETRY_DELAYS_SECONDS[attempts - 1]
                        queue[current_index] = item
                _write_json(self.queue_path, queue)
                _write_json(self.state_path, state)
            processed += 1
        return processed

    @staticmethod
    def _normalize_delivery_result(value: DeliveryResult | int | dict[str, Any]) -> DeliveryResult:
        if isinstance(value, DeliveryResult):
            return value
        if isinstance(value, int):
            return DeliveryResult(status=value)
        if isinstance(value, dict):
            status = value.get("status")
            ids = value.get("acknowledged_event_ids", [])
            return DeliveryResult(
                status=int(status) if isinstance(status, int) else None,
                acknowledged_event_ids=frozenset(str(item) for item in ids if isinstance(item, str)),
                error_category=value.get("error_category") if isinstance(value.get("error_category"), str) else None,
            )
        return DeliveryResult(status=None, error_category="invalid_sender_result")

    def _dead_letter_record(
        self,
        item: dict[str, Any],
        status: int | None,
        error_category: str,
    ) -> dict[str, Any]:
        return {
            "payload": item.get("payload"),
            "attempts": int(item.get("attempts", 0)) + 1,
            "status": status,
            "error_category": error_category,
            "failed_at": _timestamp_from_epoch(self.now()),
        }

    def _append_dead_letter(self, item: dict[str, Any], status: int | None, error_category: str) -> None:
        dead_letters = self._dead_letters()
        dead_letters.append(self._dead_letter_record(item, status, error_category))
        _write_json(self.dead_letter_path, dead_letters[-MAX_DEAD_LETTER_EVENTS:])

    def status(self) -> dict[str, Any]:
        with self._lock:
            state = self._state()
            return {
                "enabled": bool(self.enabled_getter()),
                "pending_count": len(self._queue()),
                "acknowledged_count": state["acknowledged_count"],
                "rejected_count": state["rejected_count"],
                "dead_letter_count": state["dead_letter_count"],
                "last_successful_delivery_at": state["last_successful_delivery_at"],
                "last_status": state["last_status"],
                "last_error_category": state["last_error_category"],
            }

    def clear_queue(self) -> None:
        try:
            with self._lock:
                _write_json(self.queue_path, [])
                _write_json(self.dead_letter_path, [])
        except Exception:
            _log.debug("telemetry queue clear skipped", exc_info=True)


_default_client: TelemetryClient | None = None
_default_lock = threading.Lock()


def _client() -> TelemetryClient:
    global _default_client
    with _default_lock:
        if _default_client is None:
            _default_client = TelemetryClient()
        return _default_client


def emit_telemetry(event_name: str, *, deduplicate: bool | None = None) -> bool:
    try:
        return _client().emit(event_name, deduplicate=deduplicate)
    except Exception:
        return False


def flush_telemetry() -> int:
    try:
        return _client().flush()
    except Exception:
        return 0


def start_telemetry_flush() -> None:
    try:
        client = _client()
        if client.enabled_getter():
            client._start_worker()
    except Exception:
        # Best-effort background telemetry must never delay local startup.
        pass


def emit_startup_telemetry() -> None:
    emit_telemetry("installation_first_launch")
    emit_telemetry("version_first_seen")


def telemetry_status() -> dict[str, Any]:
    try:
        return _client().status()
    except Exception:
        return {
            "enabled": False,
            "pending_count": None,
            "acknowledged_count": None,
            "rejected_count": None,
            "dead_letter_count": None,
            "last_successful_delivery_at": None,
            "last_status": None,
            "last_error_category": "status_unavailable",
        }


def clear_telemetry_queue() -> None:
    try:
        _client().clear_queue()
    except Exception:
        # Best-effort opt-out cleanup must never block local settings.
        pass
