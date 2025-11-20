# SPDX-License-Identifier: AGPL-3.0-or-later
"""Developer utility to sign plugin directories with Ed25519."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib

from nacl.signing import SigningKey


def dir_hash(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    if path.exists():
        for file_path in sorted(p for p in path.rglob("*") if p.is_file()):
            digest.update(file_path.read_bytes())
    return digest.hexdigest()


def sign_plugin(plugin_path: pathlib.Path, private_key_hex: str) -> None:
    manifest_path = plugin_path / "plugin.toml"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing plugin manifest: {manifest_path}")

    manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    src_hash = dir_hash(plugin_path / "src")
    message = (manifest_hash + src_hash).encode()

    signing_key = SigningKey(bytes.fromhex(private_key_hex))
    signed = signing_key.sign(message)

    signature_data = {
        "manifest": manifest_hash,
        "src": src_hash,
        "sig": signed.signature.hex(),
    }

    signature_path = plugin_path / "signature.json"
    signature_path.write_text(json.dumps(signature_data, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sign a plugin directory with an Ed25519 key")
    parser.add_argument("plugin", type=pathlib.Path, help="Path to the plugin directory")
    parser.add_argument(
        "--private-key-hex",
        dest="private_key",
        help="Ed25519 private key in hexadecimal (defaults to PLUGIN_SIGNING_PRIVATE_KEY env)",
    )
    args = parser.parse_args()

    private_key = args.private_key or os.getenv("PLUGIN_SIGNING_PRIVATE_KEY")
    if not private_key:
        raise SystemExit("A private key must be provided via --private-key-hex or PLUGIN_SIGNING_PRIVATE_KEY")

    sign_plugin(args.plugin, private_key)


if __name__ == "__main__":
    main()
