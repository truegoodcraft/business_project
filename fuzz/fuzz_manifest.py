# SPDX-License-Identifier: AGPL-3.0-or-later
"""Atheris harness for update-manifest parsing and trust validation.

Run from the repository root with, for example::

    python -m fuzz.fuzz_manifest -atheris_runs=10000

The callback deliberately accepts only a bounded prefix. Documented manifest
and trust rejections are normal fuzz outcomes; every other exception remains a
crash for Atheris to report.
"""

from __future__ import annotations

import base64
import hashlib
import importlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Mapping, Sequence


MAX_INPUT_BYTES = 65_537
DEFAULT_RUNS = 1024
DEFAULT_TIMEOUT_SECONDS = 5
DEFAULT_RSS_LIMIT_MB = 1024
TRUSTED_KEY_ID = "atheris-manifest-key"
TRUSTED_PUBLIC_KEYS: Mapping[str, bytes] = {
    TRUSTED_KEY_ID: bytes.fromhex(
        "79b5562e8fe654f94078b112e8a98ba7"
        "901f853ae695bed7e0e3910bad049664"
    )
}

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


@dataclass(frozen=True)
class _Targets:
    update: ModuleType
    manifest_trust: ModuleType


_TARGETS: _Targets | None = None


def _load_targets() -> _Targets:
    global _TARGETS
    if _TARGETS is None:
        _TARGETS = _Targets(
            update=importlib.import_module("core.services.update"),
            manifest_trust=importlib.import_module("core.runtime.manifest_trust"),
        )
    return _TARGETS


class _MemoryResponse:
    """Minimal streaming response accepted by the production manifest reader."""

    status_code = 200
    headers = {"content-type": "application/json"}

    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def iter_bytes(self):
        for offset in range(0, len(self._payload), 4096):
            yield self._payload[offset : offset + 4096]


def _structured_manifest_bytes(data: bytes) -> bytes:
    """Build a signed envelope so short fuzz inputs reach deep validators."""

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    targets = _load_targets()
    control = data[0] if data else 0
    body = data[1:257] if data else b""
    digest = hashlib.sha256(body).hexdigest()
    version = ".".join(str(value % 10) for value in body[:3].ljust(3, b"\0"))
    entry = {
        "version": version,
        "download": {
            "url": f"https://example.test/BUS-Core-{digest[:16]}.zip",
            "sha256": digest,
        },
    }

    schema_mode = (control >> 1) & 0x03
    if schema_mode == 0:
        payload = {"latest": entry}
    elif schema_mode == 1:
        payload = {"channels": {"stable": entry}}
    elif schema_mode == 2:
        payload = {"latest": {"version": body.decode("utf-8", errors="replace")[:32]}}
    else:
        payload = {"latest": entry, "channels": []}

    private_key = Ed25519PrivateKey.from_private_bytes(bytes(range(1, 33)))
    signature = private_key.sign(targets.manifest_trust.canonicalize_manifest_payload(payload))
    if control & 0x08:
        signature = bytes((signature[0] ^ 1,)) + signature[1:]

    signature_metadata = {
        "alg": "RS256" if control & 0x10 else "Ed25519",
        "key_id": "unknown" if control & 0x20 else TRUSTED_KEY_ID,
        "sig": base64.b64encode(signature).decode("ascii"),
    }
    if control & 0x40:
        manifest = dict(payload)
        manifest["signature"] = signature_metadata
    else:
        manifest = {"payload": payload, "signature": signature_metadata}
    return json.dumps(manifest, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def TestOneInput(data: bytes) -> None:
    """Exercise the signed-manifest boundary with one bounded byte string."""

    targets = _load_targets()
    bounded = bytes(data[:MAX_INPUT_BYTES])
    manifest_bytes = (
        _structured_manifest_bytes(bounded)
        if not bounded or bounded[0] & 0x80
        else bounded
    )

    try:
        manifest = targets.update._read_manifest_response(_MemoryResponse(manifest_bytes))
        trusted_manifest = targets.manifest_trust.unwrap_manifest(
            manifest,
            trusted_public_keys=TRUSTED_PUBLIC_KEYS,
            require_signature=True,
        )
        targets.update._resolve_manifest_release(trusted_manifest, "stable")
    except (targets.update.UpdateCheckError, targets.manifest_trust.ManifestTrustError):
        return


def main(argv: Sequence[str] | None = None) -> None:
    try:
        import atheris
    except ModuleNotFoundError as exc:  # pragma: no cover - exercised only without the fuzz extra.
        raise SystemExit("Atheris is required to run this fuzz harness.") from exc

    with atheris.instrument_imports(include=["core"]):
        _load_targets()

    fuzz_argv = list(argv) if argv is not None else list(sys.argv)
    if not any(arg.startswith("-atheris_runs=") for arg in fuzz_argv[1:]):
        fuzz_argv.append(f"-atheris_runs={DEFAULT_RUNS}")
    if not any(arg.startswith("-max_len=") for arg in fuzz_argv[1:]):
        fuzz_argv.append(f"-max_len={MAX_INPUT_BYTES}")
    if not any(arg.startswith("-timeout=") for arg in fuzz_argv[1:]):
        fuzz_argv.append(f"-timeout={DEFAULT_TIMEOUT_SECONDS}")
    if not any(arg.startswith("-rss_limit_mb=") for arg in fuzz_argv[1:]):
        fuzz_argv.append(f"-rss_limit_mb={DEFAULT_RSS_LIMIT_MB}")

    atheris.Setup(fuzz_argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
