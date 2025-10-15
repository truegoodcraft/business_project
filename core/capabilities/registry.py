from __future__ import annotations
import json, os, hmac, hashlib, time, threading, tempfile
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

    def _manifest_dict(self) -> Dict[str, Any]:
        """Build the manifest dict WITHOUT signature (internal)."""
        caps = [asdict(cap) for cap in self.list()]
        return {
            "core_version": VERSION,
            "plugin_api_version": self._plugin_api_version,
            "schema_version": "1",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "capabilities": caps,
        }

    def build_manifest(self) -> Dict[str, Any]:
        """Return signed manifest JSON dict (no disk writes, no blocking)."""
        base_no_sig = self._manifest_dict()
        payload = json.dumps(base_no_sig, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        sig = self._sign(payload)
        out = dict(base_no_sig)
        out["signature"] = sig
        return out

    def _atomic_write(self, path: Path, content: str) -> None:
        """Windows-safe atomic-ish write: temp file + replace."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", dir=str(path.parent)) as tf:
            tf.write(content)
            tmp_name = tf.name
        Path(tmp_name).replace(path)

    def emit_manifest(self) -> Dict[str, Any]:
        """Synchronous write (kept for compatibility)."""
        out = self.build_manifest()
        out.setdefault(
            "license",
            {
                "core": "PolyForm-Noncommercial-1.0.0",
                "core_url": "https://polyformproject.org/licenses/noncommercial/1.0.0/",
            },
        )
        try:
            self._atomic_write(MANIFEST_PATH, json.dumps(out, indent=2))
        except Exception as e:
            out = dict(out)
            out["_write_error"] = str(e)
        return out

    def emit_manifest_async(self, timeout_sec: float = 1.5) -> Dict[str, Any]:
        """
        Return manifest immediately; write file in a background thread.
        Never blocks the caller longer than building JSON/signing.
        """
        out = self.build_manifest()
        out.setdefault(
            "license",
            {
                "core": "PolyForm-Noncommercial-1.0.0",
                "core_url": "https://polyformproject.org/licenses/noncommercial/1.0.0/",
            },
        )

        def _writer() -> None:
            try:
                self._atomic_write(MANIFEST_PATH, json.dumps(out, indent=2))
            except Exception:
                pass

        t = threading.Thread(target=_writer, daemon=True)
        t.start()
        return out
