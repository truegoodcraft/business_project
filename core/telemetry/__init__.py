"""Strict, optional BUS Core product telemetry."""

from .client import (
    ALLOWED_EVENT_NAMES,
    TelemetryClient,
    clear_telemetry_queue,
    emit_startup_telemetry,
    emit_telemetry,
    flush_telemetry,
    start_telemetry_flush,
    telemetry_status,
)

__all__ = [
    "ALLOWED_EVENT_NAMES",
    "TelemetryClient",
    "clear_telemetry_queue",
    "emit_startup_telemetry",
    "emit_telemetry",
    "flush_telemetry",
    "start_telemetry_flush",
    "telemetry_status",
]
