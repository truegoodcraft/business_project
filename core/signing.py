"""Utilities for verifying plugin signatures."""

from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Iterable

from nacl.signing import VerifyKey

# NOTE: replace this value with the real controller public key in deployments.
PUBLIC_KEY_HEX = "00" * 32


def dir_hash(path: str | pathlib.Path) -> str:
    """Return a SHA-256 hash of all files under *path*.

    Files are processed in sorted order to ensure deterministic output. The
    hash only covers file contents; directory metadata is ignored.
    """

    h = hashlib.sha256()
    root = pathlib.Path(path)
    for entry in _iter_files(root):
        h.update(entry.read_bytes())
    return h.hexdigest()


def verify_plugin_signature(plugin_path: str | pathlib.Path, public_key_hex: str) -> bool:
    """Validate the signature for a plugin directory.

    The plugin directory must contain a ``signature.json`` file with the
    following schema::

        {"manifest": sha256, "src": sha256, "sig": hex_signature}

    The ``manifest`` hash is compared to ``plugin.toml`` and ``src`` is the
    digest of the plugin's ``src`` directory. The concatenation of those two
    hexadecimal strings is verified using Ed25519 and the provided public key.
    """

    plugin_dir = pathlib.Path(plugin_path)
    sig_file = plugin_dir / "signature.json"
    if not sig_file.exists():
        return False

    try:
        sig_data = json.loads(sig_file.read_text())
    except json.JSONDecodeError:
        return False

    manifest_path = plugin_dir / "plugin.toml"
    if not manifest_path.exists():
        return False

    manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    if sig_data.get("manifest") != manifest_hash:
        return False

    src_dir = plugin_dir / "src"
    if sig_data.get("src") != dir_hash(src_dir):
        return False

    try:
        verify_key = VerifyKey(bytes.fromhex(public_key_hex))
        verify_key.verify(
            (sig_data["manifest"] + sig_data["src"]).encode(),
            bytes.fromhex(sig_data["sig"]),
        )
    except Exception:  # pragma: no cover - defensive against library errors
        return False
    return True


def _iter_files(path: pathlib.Path) -> Iterable[pathlib.Path]:
    if not path.exists():
        return ()
    for candidate in sorted(path.rglob("*")):
        if candidate.is_file():
            yield candidate

