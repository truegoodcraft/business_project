from __future__ import annotations
import json, os, hmac, hashlib, time, threading
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict, List, Any, Optional

from core.version import VERSION

def _state_dir() -> Path:
    # Windows: %LOCALAPPDATA%\TGC\state ; Others: ~/.tgc/state
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "TGC" / "state"
    return Path.home() / ".tgc" / "state"

MANIFEST_PATH = _state_dir() / "system_manifest.json"
KEY_PATH      = _state_dir() / "capabilities_hmac.key"

@dataclass
class Capability:
    cap: str
    provider: str
    status: str = "blocked"           # ready | blocked | pending | deprecated
    policy: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)  # non-secret metadata

@dataclass
class Manifest:
    core_version: str
    plugin_api_version: str
    schema_version: str
    generated_at: str
    capabilities: List[Capability]
    signature: Optional[str] = None   # HMAC-SHA256 over JSON (without signature)

class CapabilityRegistry:
    """Core-owned registry. Single writer. Thread-safe. No secrets."""
    def __init__(self, plugin_api_version: str = "2") -> None:
        self._lock = threading.Lock()
        self._caps: Dict[str, Capability] = {}
        self._plugin_api_version = plugin_api_version
        _state_dir().mkdir(parents=True, exist_ok=True)
        if not KEY_PATH.exists():
            KEY_PATH.write_bytes(os.urandom(32))

    def upsert(self, cap: str, *, provider: str, status: str = "ready",
               policy: Optional[Dict[str, Any]] = None, meta: Optional[Dict[str, Any]] = None) -> None:
        with self._lock:
            self._caps[cap] = Capability(cap=cap, provider=provider, status=status,
                                         policy=policy or {}, meta=meta or {})

    def delete(self, cap: str) -> None:
        with self._lock:
            self._caps.pop(cap, None)

    def list(self) -> List[Capability]:
        with self._lock:
            return list(self._caps.values())

    def _sign(self, payload: bytes) -> str:
        key = KEY_PATH.read_bytes()
        return hmac.new(key, payload, hashlib.sha256).hexdigest()

    def emit_manifest(self) -> Dict[str, Any]:
        with self._lock:
            base = asdict(Manifest(
                core_version=VERSION,
                plugin_api_version=self._plugin_api_version,
                schema_version="1",
                generated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                capabilities=self.list(),
            ))
        base_no_sig = {k: v for k, v in base.items() if k != "signature"}
        payload = json.dumps(base_no_sig, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        base_no_sig["signature"] = self._sign(payload)
        MANIFEST_PATH.write_text(json.dumps(base_no_sig, indent=2), encoding="utf-8")
        return base_no_sig
