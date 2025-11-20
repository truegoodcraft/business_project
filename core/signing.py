# SPDX-License-Identifier: AGPL-3.0-or-later
# TGC BUS Core (Business Utility System Core)
# Copyright (C) 2025 True Good Craft
#
# This file is part of TGC BUS Core.
#
# TGC BUS Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# TGC BUS Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with TGC BUS Core.  If not, see <https://www.gnu.org/licenses/>.

"""Utilities for verifying plugin signatures."""

from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Iterable

SIGNING_AVAILABLE = True
try:  # pragma: no cover - import guard
    from nacl.signing import VerifyKey
except Exception:  # pragma: no cover - optional dependency
    SIGNING_AVAILABLE = False
    VerifyKey = None  # type: ignore[assignment]

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

    if not SIGNING_AVAILABLE:
        return True

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

