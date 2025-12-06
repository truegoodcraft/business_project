# SPDX-License-Identifier: AGPL-3.0-or-later
"""Password-based encryption helpers for BUS Core backups."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


MAGIC = b"BUSCDBK\0"  # 8 bytes
CONTAINER_VERSION = 1
KDF_ID_ARGON2ID = 1
KDF_ID_PBKDF2 = 2

SALT_LEN = 16
NONCE_LEN = 12
TAG_LEN = 16
KEY_LEN = 32
PBKDF2_ITERS = 600_000
ARGON2_MEMORY_KIB = 65_536  # ~64 MiB
ARGON2_TIME_COST = 3
ARGON2_PARALLELISM = 2


@dataclass(frozen=True)
class ContainerHeader:
    version: int
    kdf_id: int
    salt: bytes
    nonce: bytes


def _derive_key(password: str, salt: bytes, kdf_id: int) -> bytes:
    pw_bytes = password.encode("utf-8")
    if kdf_id == KDF_ID_ARGON2ID:
        from argon2.low_level import Type, hash_secret_raw

        return hash_secret_raw(
            pw_bytes,
            salt,
            time_cost=ARGON2_TIME_COST,
            memory_cost=ARGON2_MEMORY_KIB,
            parallelism=ARGON2_PARALLELISM,
            hash_len=KEY_LEN,
            type=Type.ID,
        )

    if kdf_id == KDF_ID_PBKDF2:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_LEN,
            salt=salt,
            iterations=PBKDF2_ITERS,
        )
        return kdf.derive(pw_bytes)

    raise ValueError("bad_container")


def _select_kdf() -> int:
    try:
        import importlib

        importlib.import_module("argon2.low_level")
        return KDF_ID_ARGON2ID
    except Exception:
        return KDF_ID_PBKDF2


def encrypt_bytes(password: str, plaintext: bytes, *, version: int = CONTAINER_VERSION) -> Tuple[bytes, ContainerHeader]:
    if not password:
        raise ValueError("password_required")

    salt = os.urandom(SALT_LEN)
    nonce = os.urandom(NONCE_LEN)
    kdf_id = _select_kdf()
    key = _derive_key(password, salt, kdf_id)

    aesgcm = AESGCM(key)
    ct_with_tag = aesgcm.encrypt(nonce, plaintext, None)
    ciphertext, tag = ct_with_tag[:-TAG_LEN], ct_with_tag[-TAG_LEN:]

    header = ContainerHeader(version=version, kdf_id=kdf_id, salt=salt, nonce=nonce)
    blob = MAGIC + bytes([version, kdf_id]) + salt + nonce + ciphertext + tag
    return blob, header


def decrypt_bytes(password: str, blob: bytes) -> Tuple[bytes, ContainerHeader]:
    if not password:
        raise ValueError("password_required")

    min_len = len(MAGIC) + 1 + 1 + SALT_LEN + NONCE_LEN + TAG_LEN
    if len(blob) < min_len:
        raise ValueError("bad_container")

    if not blob.startswith(MAGIC):
        raise ValueError("bad_container")

    version = blob[len(MAGIC)]
    kdf_id = blob[len(MAGIC) + 1]

    salt_start = len(MAGIC) + 2
    salt_end = salt_start + SALT_LEN
    nonce_end = salt_end + NONCE_LEN
    salt = blob[salt_start:salt_end]
    nonce = blob[salt_end:nonce_end]
    tag = blob[-TAG_LEN:]
    ciphertext = blob[nonce_end:-TAG_LEN]

    if kdf_id not in (KDF_ID_ARGON2ID, KDF_ID_PBKDF2):
        raise ValueError("bad_container")

    try:
        key = _derive_key(password, salt, kdf_id)
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext + tag, None)
    except Exception as exc:
        raise ValueError("decrypt_failed") from exc

    header = ContainerHeader(version=version, kdf_id=kdf_id, salt=salt, nonce=nonce)
    return plaintext, header

