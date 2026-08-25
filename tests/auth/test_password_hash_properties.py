# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import base64
from unittest.mock import patch

from hypothesis import given, settings, strategies as st

from core.auth.passwords import (
    SALT_BYTES,
    SCRYPT_DKLEN,
    SCRYPT_N,
    SCRYPT_P,
    SCRYPT_R,
    SCRYPT_SCHEME,
    hash_password,
    verify_password,
)


PASSWORDS = st.text(min_size=8, max_size=64).filter(lambda value: len(value.strip()) >= 8)
CANONICAL_V1_FIXTURE = (
    "scrypt-v1$n=16384$r=8$p=1$salt=MDEyMzQ1Njc4OWFiY2RlZg=="
    "$hash=tjK03tRvEjqCcPwmgtddMkgjlXrk8U/b9rIvfeBMKCc="
)


def test_preexisting_canonical_v1_hash_remains_compatible() -> None:
    assert verify_password("correct horse battery staple", CANONICAL_V1_FIXTURE) is True
    assert verify_password("wrong password", CANONICAL_V1_FIXTURE) is False


@given(password=PASSWORDS)
@settings(max_examples=25, deadline=None)
def test_generated_password_hashes_round_trip(password: str) -> None:
    encoded = hash_password(password)

    assert verify_password(password, encoded) is True


@given(
    n=st.integers().filter(lambda value: value != SCRYPT_N),
    r=st.integers().filter(lambda value: value != SCRYPT_R),
    p=st.integers().filter(lambda value: value != SCRYPT_P),
)
def test_untrusted_scrypt_cost_parameters_are_rejected_without_hashing(
    n: int,
    r: int,
    p: int,
) -> None:
    salt = base64.b64encode(b"s" * SALT_BYTES).decode("ascii")
    digest = base64.b64encode(b"d" * SCRYPT_DKLEN).decode("ascii")
    candidates = (
        f"{SCRYPT_SCHEME}$n={n}$r={SCRYPT_R}$p={SCRYPT_P}$salt={salt}$hash={digest}",
        f"{SCRYPT_SCHEME}$n={SCRYPT_N}$r={r}$p={SCRYPT_P}$salt={salt}$hash={digest}",
        f"{SCRYPT_SCHEME}$n={SCRYPT_N}$r={SCRYPT_R}$p={p}$salt={salt}$hash={digest}",
    )

    def unexpected_scrypt(*args, **kwargs):
        raise AssertionError("untrusted parameters reached hashlib.scrypt")

    with patch("core.auth.passwords.hashlib.scrypt", unexpected_scrypt):
        assert all(verify_password("correct horse battery staple", candidate) is False for candidate in candidates)


@given(noncanonical_n=st.sampled_from(("016384", "+16384", "16_384", " 16384", "16384 ")))
def test_noncanonical_parameter_spellings_fail_closed_without_hashing(noncanonical_n: str) -> None:
    salt = base64.b64encode(b"s" * SALT_BYTES).decode("ascii")
    digest = base64.b64encode(b"d" * SCRYPT_DKLEN).decode("ascii")
    candidate = (
        f"{SCRYPT_SCHEME}$n={noncanonical_n}$r={SCRYPT_R}$p={SCRYPT_P}"
        f"$salt={salt}$hash={digest}"
    )

    def unexpected_scrypt(*args, **kwargs):
        raise AssertionError("noncanonical parameters reached hashlib.scrypt")

    with patch("core.auth.passwords.hashlib.scrypt", unexpected_scrypt):
        assert verify_password("correct horse battery staple", candidate) is False


@given(encoded_hash=st.text(min_size=257, max_size=2048))
def test_oversized_encoded_hashes_are_rejected_before_decoding(encoded_hash: str) -> None:
    def unexpected_decode(value: str) -> bytes:
        raise AssertionError("oversized input reached base64 decoding")

    with patch("core.auth.passwords._b64decode", unexpected_decode):
        assert verify_password("correct horse battery staple", encoded_hash) is False


@given(
    salt=st.binary(max_size=64).filter(lambda value: len(value) != SALT_BYTES),
    digest=st.binary(max_size=64).filter(lambda value: len(value) != SCRYPT_DKLEN),
)
def test_noncanonical_salt_and_digest_sizes_are_rejected_without_hashing(
    salt: bytes,
    digest: bytes,
) -> None:
    candidates = (
        f"{SCRYPT_SCHEME}$n={SCRYPT_N}$r={SCRYPT_R}$p={SCRYPT_P}"
        f"$salt={base64.b64encode(salt).decode('ascii')}"
        f"$hash={base64.b64encode(b'd' * SCRYPT_DKLEN).decode('ascii')}",
        f"{SCRYPT_SCHEME}$n={SCRYPT_N}$r={SCRYPT_R}$p={SCRYPT_P}"
        f"$salt={base64.b64encode(b's' * SALT_BYTES).decode('ascii')}"
        f"$hash={base64.b64encode(digest).decode('ascii')}",
    )

    def unexpected_scrypt(*args, **kwargs):
        raise AssertionError("noncanonical input reached hashlib.scrypt")

    with patch("core.auth.passwords.hashlib.scrypt", unexpected_scrypt):
        assert all(verify_password("correct horse battery staple", candidate) is False for candidate in candidates)
