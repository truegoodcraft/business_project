# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import base64
import json
import sys
from contextlib import nullcontext
from types import ModuleType

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.runtime.manifest_trust import canonicalize_manifest_payload
from fuzz import fuzz_manifest, fuzz_paths_zip


pytestmark = pytest.mark.unit


def _signed_manifest_bytes() -> bytes:
    private_key = Ed25519PrivateKey.from_private_bytes(bytes(range(1, 33)))
    payload = {
        "latest": {
            "version": "1.4.2",
            "download": {
                "url": "https://example.test/BUS-Core-1.4.2.zip",
                "sha256": "a" * 64,
            },
        }
    }
    signature = private_key.sign(canonicalize_manifest_payload(payload))
    envelope = {
        "payload": payload,
        "signature": {
            "alg": "Ed25519",
            "key_id": fuzz_manifest.TRUSTED_KEY_ID,
            "sig": base64.b64encode(signature).decode("ascii"),
        },
    }
    return json.dumps(envelope).encode("utf-8")


def _path_zip_input(path_value: str, zip_name: str, *, flags: int = 0) -> bytes:
    path_bytes = path_value.encode("utf-8")
    zip_bytes = zip_name.encode("utf-8")
    return bytes((flags,)) + len(path_bytes).to_bytes(2, "little") + path_bytes + zip_bytes


def test_manifest_entry_point_accepts_valid_and_rejected_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    targets = fuzz_manifest._load_targets()
    original = targets.update._resolve_manifest_release
    observed: list[str] = []

    def record_release(manifest, channel):
        observed.append(channel)
        return original(manifest, channel)

    monkeypatch.setattr(targets.update, "_resolve_manifest_release", record_release)

    fuzz_manifest.TestOneInput(_signed_manifest_bytes())
    fuzz_manifest.TestOneInput(b"")
    fuzz_manifest.TestOneInput(b"\x80structured")
    fuzz_manifest.TestOneInput(b"not-json")
    fuzz_manifest.TestOneInput(b"[]")
    fuzz_manifest.TestOneInput(b"x" * (fuzz_manifest.MAX_INPUT_BYTES + 100))

    assert observed == ["stable", "stable", "stable"]


def test_manifest_entry_point_does_not_hide_unexpected_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    targets = fuzz_manifest._load_targets()

    def unexpected_failure(_response):
        raise RuntimeError("unexpected manifest failure")

    monkeypatch.setattr(targets.update, "_read_manifest_response", unexpected_failure)

    with pytest.raises(RuntimeError, match="unexpected manifest failure"):
        fuzz_manifest.TestOneInput(b"{}")


def test_path_zip_entry_point_accepts_safe_and_rejected_inputs() -> None:
    fuzz_paths_zip.TestOneInput(_path_zip_input("reports/today.json", "assets/readme.txt"))
    fuzz_paths_zip.TestOneInput(_path_zip_input("../outside", "../escape.exe"))
    fuzz_paths_zip.TestOneInput(_path_zip_input("safe", "link.exe", flags=1))
    fuzz_paths_zip.TestOneInput(b"")
    fuzz_paths_zip.TestOneInput(b"\x82structured-parent")
    fuzz_paths_zip.TestOneInput(b"\xf0structured-unc")
    fuzz_paths_zip.TestOneInput(b"\x80\x80structured-surrogate")
    fuzz_paths_zip.TestOneInput(b"x" * (fuzz_paths_zip.MAX_INPUT_BYTES + 100))


def test_path_zip_entry_point_does_not_hide_unexpected_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    targets = fuzz_paths_zip._load_targets()

    def unexpected_failure(_path, _roots):
        raise RuntimeError("unexpected path failure")

    monkeypatch.setattr(targets.pathsafe, "resolve_path_under_roots", unexpected_failure)

    with pytest.raises(RuntimeError, match="unexpected path failure"):
        fuzz_paths_zip.TestOneInput(_path_zip_input("safe", "safe.txt"))


def test_path_zip_entry_point_crashes_if_path_validator_escapes_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    targets = fuzz_paths_zip._load_targets()
    escaped = fuzz_paths_zip._FUZZ_ROOT.parent / "escaped-path"
    monkeypatch.setattr(targets.pathsafe, "resolve_path_under_roots", lambda *_args: escaped)

    with pytest.raises(AssertionError, match="outside the fuzz root"):
        fuzz_paths_zip.TestOneInput(_path_zip_input("safe", "safe.txt"))


def test_path_zip_entry_point_crashes_if_zip_validator_escapes_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    targets = fuzz_paths_zip._load_targets()
    escaped = fuzz_paths_zip._FUZZ_ROOT.parent / "escaped-zip"
    monkeypatch.setattr(targets.update_extract, "_validated_zip_destination", lambda *_args: escaped)

    with pytest.raises(AssertionError, match="outside the fuzz root"):
        fuzz_paths_zip.TestOneInput(_path_zip_input("safe", "safe.txt"))


@pytest.mark.parametrize("harness", (fuzz_manifest, fuzz_paths_zip))
def test_atheris_main_wires_the_callback_without_starting_a_service(
    harness: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_atheris = ModuleType("atheris")
    observed: dict[str, object] = {}

    fake_atheris.instrument_imports = lambda **_kwargs: nullcontext()

    def setup(argv, callback):
        observed["argv"] = argv
        observed["callback"] = callback

    def fuzz():
        observed["fuzz_called"] = True

    fake_atheris.Setup = setup
    fake_atheris.Fuzz = fuzz
    monkeypatch.setitem(sys.modules, "atheris", fake_atheris)

    harness.main(["harness", "-atheris_runs=1", "-max_len=128"])

    assert observed == {
        "argv": [
            "harness",
            "-atheris_runs=1",
            "-max_len=128",
            f"-timeout={harness.DEFAULT_TIMEOUT_SECONDS}",
            f"-rss_limit_mb={harness.DEFAULT_RSS_LIMIT_MB}",
        ],
        "callback": harness.TestOneInput,
        "fuzz_called": True,
    }


@pytest.mark.parametrize("harness", (fuzz_manifest, fuzz_paths_zip))
def test_atheris_main_defaults_to_a_bounded_run(
    harness: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_atheris = ModuleType("atheris")
    observed: dict[str, object] = {}

    fake_atheris.instrument_imports = lambda **_kwargs: nullcontext()

    def setup(argv, _callback):
        observed["argv"] = argv

    fake_atheris.Setup = setup
    fake_atheris.Fuzz = lambda: None
    monkeypatch.setitem(sys.modules, "atheris", fake_atheris)

    harness.main(["harness"])

    assert observed["argv"] == [
        "harness",
        f"-atheris_runs={harness.DEFAULT_RUNS}",
        f"-max_len={harness.MAX_INPUT_BYTES}",
        f"-timeout={harness.DEFAULT_TIMEOUT_SECONDS}",
        f"-rss_limit_mb={harness.DEFAULT_RSS_LIMIT_MB}",
    ]
