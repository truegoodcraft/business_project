from __future__ import annotations

import json
import logging
import platform
import threading
import time
import uuid
import urllib.error
import urllib.request
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
MAX_ATTEMPTS = 3
REQUEST_TIMEOUT_SECONDS = 2.0
RETRY_DELAYS_SECONDS = (1.0, 5.0, 30.0)

EVENT_CATEGORIES: dict[str, tuple[str, ...]] = {
    "installation_release": (
        "installation_first_launch", "update_check", "update_success", "update_failure",
    ),
    "module_use": (
        "inventory_opened", "recipes_opened", "manufacturing_opened",
        "jobs_opened", "invoices_opened", "settings_opened",
    ),
    "workflow_milestone": (
        "first_inventory_item_created", "first_recipe_created",
        "first_manufacturing_run_completed", "first_job_completed",
        "first_invoice_created", "backup_completed", "restore_attempted",
        "restore_completed", "import_completed", "import_failed",
    ),
    "reliability": (
        "startup_failure", "backup_failure", "restore_failure",
        "unhandled_application_error", "migration_failure",
    ),
}
ALLOWED_EVENT_NAMES = frozenset(name for names in EVENT_CATEGORIES.values() for name in names)
MODULE_EVENT_NAMES = frozenset(EVENT_CATEGORIES["module_use"])
MILESTONE_EVENT_NAMES = frozenset(
    ("installation_first_launch",)
    + EVENT_CATEGORIES["workflow_milestone"][:5]
)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


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


def _default_sender(payload: dict[str, Any]) -> int:
    request = urllib.request.Request(
        TELEMETRY_ENDPOINT,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return int(response.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)


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
        sender: Callable[[dict[str, Any]], int] | None = None,
        enabled_getter: Callable[[], bool] | None = None,
        channel_getter: Callable[[], str] | None = None,
        now: Callable[[], float] | None = None,
        uuid_factory: Callable[[], uuid.UUID] | None = None,
        start_background: bool = True,
    ) -> None:
        root = state_dir()
        self.state_path = state_path or (root / "telemetry_state.json")
        self.queue_path = queue_path or (root / "telemetry_queue.json")
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
        return raw

    def _queue(self) -> list[dict[str, Any]]:
        raw = _read_json(self.queue_path, [])
        return raw if isinstance(raw, list) else []

    def installation_id(self) -> str:
        with self._lock:
            state = self._state()
            current = state.get("installation_id")
            try:
                parsed = uuid.UUID(str(current))
                if parsed.version == 4:
                    return str(parsed)
            except (ValueError, TypeError, AttributeError):
                # Expected fallback for absent or malformed optional local state.
                pass
            generated = str(self.uuid_factory())
            parsed = uuid.UUID(generated)
            if parsed.version != 4:
                raise ValueError("installation identifier must be UUIDv4")
            state["installation_id"] = generated
            _write_json(self.state_path, state)
            return generated

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
            "installation_id": self.installation_id(),
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
                if should_deduplicate and event_name in milestones:
                    return False
                queue = self._queue()
                queue.append({
                    "payload": self.build_payload(event_name),
                    "attempts": 0,
                    "next_attempt_at": self.now(),
                })
                queue = queue[-MAX_QUEUE_EVENTS:]
                _write_json(self.queue_path, queue)
                if should_deduplicate:
                    milestones.add(event_name)
                    state["milestones"] = sorted(milestones)
                    _write_json(self.state_path, state)
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
            status: int | None = None
            try:
                status = self.sender(dict(item.get("payload") or {}))
            except Exception:
                status = None
            with self._lock:
                queue = self._queue()
                event_id = (item.get("payload") or {}).get("event_id")
                current_index = next(
                    (i for i, queued in enumerate(queue) if (queued.get("payload") or {}).get("event_id") == event_id),
                    None,
                )
                if current_index is None:
                    continue
                if status is not None and 200 <= status < 300:
                    queue.pop(current_index)
                elif status is not None and 400 <= status < 500 and status != 429:
                    # Older/unsupported servers and invalid payloads fail safely.
                    queue.pop(current_index)
                else:
                    attempts = int(item.get("attempts", 0)) + 1
                    if attempts >= MAX_ATTEMPTS:
                        queue.pop(current_index)
                    else:
                        item["attempts"] = attempts
                        item["next_attempt_at"] = self.now() + RETRY_DELAYS_SECONDS[attempts - 1]
                        queue[current_index] = item
                _write_json(self.queue_path, queue)
            processed += 1
        return processed

    def clear_queue(self) -> None:
        try:
            with self._lock:
                _write_json(self.queue_path, [])
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


def clear_telemetry_queue() -> None:
    try:
        _client().clear_queue()
    except Exception:
        # Best-effort opt-out cleanup must never block local settings.
        pass
