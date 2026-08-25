# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import base64
import zipfile
from decimal import Decimal
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from hypothesis import assume, given, settings, strategies as st

from core.backup import crypto as backup_crypto
from core.metrics import metric
from core.reader.ids import _b64e, rid_to_path, root_signature, to_rid
from core.runtime.manifest_trust import (
    ManifestTrustError,
    canonicalize_manifest_payload,
    verify_manifest_envelope,
)
from core.services.update_extract import ArtifactExtractError, _validated_zip_destination
from core.utils.pathsafe import PathSafetyError, resolve_path_under_roots


pytestmark = pytest.mark.unit

SAFE_SEGMENT = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-",
    min_size=1,
    max_size=16,
)
SAFE_PARTS = st.lists(SAFE_SEGMENT, min_size=1, max_size=5)
JSON_SCALAR = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-(2**31), max_value=2**31 - 1),
    st.text(max_size=64),
)

_MANIFEST_PRIVATE_KEY = Ed25519PrivateKey.generate()
_MANIFEST_KEY_ID = "hypothesis-test-key"
_MANIFEST_TRUSTED_KEYS = {
    _MANIFEST_KEY_ID: _MANIFEST_PRIVATE_KEY.public_key().public_bytes(
        encoding=Encoding.Raw,
        format=PublicFormat.Raw,
    )
}


def _fixed_root(name: str) -> Path:
    return (Path.cwd() / name).resolve(strict=False)


@given(SAFE_PARTS)
@settings(max_examples=80)
def test_relative_paths_resolve_only_below_allowed_root(parts: list[str]) -> None:
    root = _fixed_root(".hypothesis-path-root")

    resolved = resolve_path_under_roots("/".join(parts), [root])

    assert resolved.is_relative_to(root)
    assert resolved.relative_to(root).parts == tuple(parts)


@given(SAFE_PARTS, SAFE_PARTS)
@settings(max_examples=60)
def test_explicit_parent_traversal_is_always_rejected(
    prefix: list[str],
    suffix: list[str],
) -> None:
    root = _fixed_root(".hypothesis-path-root")
    malicious = "/".join([*prefix, "..", *suffix])

    with pytest.raises(PathSafetyError, match="path_out_of_roots"):
        resolve_path_under_roots(malicious, [root])


@given(SAFE_PARTS)
@settings(max_examples=80)
def test_rid_round_trip_preserves_an_in_root_path(parts: list[str]) -> None:
    root = _fixed_root(".hypothesis-rid-root")
    candidate = root.joinpath(*parts)

    rid = to_rid(str(candidate), [str(root)])
    resolved = Path(rid_to_path(rid, [str(root)])).resolve(strict=False)

    assert resolved == candidate.resolve(strict=False)
    assert resolved.is_relative_to(root)


@given(st.text(max_size=160))
@settings(max_examples=100)
def test_signed_rid_payload_can_never_escape_its_root(relative_payload: str) -> None:
    root = _fixed_root(".hypothesis-rid-root")
    rid = f"local:v2:{root_signature(str(root))}:{_b64e(relative_payload)}"

    try:
        resolved = Path(rid_to_path(rid, [str(root)])).resolve(strict=False)
    except ValueError:
        return

    assert resolved.is_relative_to(root)


@given(JSON_SCALAR, JSON_SCALAR)
@settings(max_examples=60)
def test_any_signed_manifest_value_change_fails_closed(original: object, tampered: object) -> None:
    assume(original != tampered)
    payload = {
        "latest": {
            "version": "1.4.2",
            "download": {
                "url": "https://example.test/BUS-Core-1.4.2.zip",
                "sha256": "a" * 64,
            },
        },
        "probe": original,
    }
    signature = _MANIFEST_PRIVATE_KEY.sign(canonicalize_manifest_payload(payload))
    envelope = {
        "payload": payload,
        "signature": {
            "alg": "Ed25519",
            "key_id": _MANIFEST_KEY_ID,
            "sig": base64.b64encode(signature).decode("ascii"),
        },
    }
    envelope["payload"]["probe"] = tampered

    with pytest.raises(ManifestTrustError, match="signature verification failed") as exc_info:
        verify_manifest_envelope(envelope, trusted_public_keys=_MANIFEST_TRUSTED_KEYS)

    assert exc_info.value.code == "bad_signature"


@given(SAFE_PARTS)
@settings(max_examples=80)
def test_safe_zip_entry_destination_stays_under_extraction_root(parts: list[str]) -> None:
    root = _fixed_root(".hypothesis-extract-root")
    info = zipfile.ZipInfo("/".join(parts))

    destination = _validated_zip_destination(info, root)

    assert destination.is_relative_to(root)


@given(
    SAFE_SEGMENT,
    SAFE_SEGMENT,
    st.sampled_from(("parent", "nested_parent", "absolute", "drive", "colon", "control", "surrogate")),
)
@settings(max_examples=80)
def test_unsafe_zip_entry_names_are_rejected(first: str, second: str, shape: str) -> None:
    names = {
        "parent": f"../{first}",
        "nested_parent": f"{first}/../{second}",
        "absolute": f"/{first}/{second}",
        "drive": f"C:\\{first}\\{second}",
        "colon": f"{first}:{second}",
        "control": f"{first}/\x01{second}",
        "surrogate": f"{first}/\ud800{second}",
    }
    info = zipfile.ZipInfo(names[shape])

    with pytest.raises(ArtifactExtractError) as exc_info:
        _validated_zip_destination(info, _fixed_root(".hypothesis-extract-root"))

    assert exc_info.value.code == "unsafe_zip_entry"


@given(st.binary(max_size=53))
@settings(max_examples=80)
def test_truncated_backup_containers_fail_before_key_derivation(blob: bytes) -> None:
    minimum_container_size = (
        len(backup_crypto.MAGIC)
        + 2
        + backup_crypto.SALT_LEN
        + backup_crypto.NONCE_LEN
        + backup_crypto.TAG_LEN
    )
    assume(len(blob) < minimum_container_size)

    with pytest.raises(ValueError, match="bad_container"):
        backup_crypto.decrypt_bytes("property-test-password", blob)


@given(
    st.sampled_from(
        [
            (dimension, unit)
            for dimension, units in metric.UNIT_MULTIPLIER.items()
            for unit in units
        ]
    ),
    st.integers(min_value=-1_000_000, max_value=1_000_000),
)
@settings(max_examples=100)
def test_integer_display_quantities_round_trip_exactly(
    dimension_and_unit: tuple[str, str],
    display_integer: int,
) -> None:
    dimension, unit = dimension_and_unit
    display = Decimal(display_integer)

    stored = metric.to_base_qty(display, dimension=dimension, unit=unit)
    restored = metric.from_base_qty(stored, dimension=dimension, unit=unit)

    assert stored == display_integer * metric.UNIT_MULTIPLIER[dimension][unit]
    assert restored == display.quantize(Decimal("0.01"))
    assert metric.normalize_quantity_to_base_int(str(display), unit, dimension) == stored
