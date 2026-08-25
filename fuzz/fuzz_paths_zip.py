# SPDX-License-Identifier: AGPL-3.0-or-later
"""Atheris harness for allowed-root paths and update ZIP entry names.

Run from the repository root with, for example::

    python -m fuzz.fuzz_paths_zip -atheris_runs=10000

The three-byte harness header contains a ZIP-info flag byte and a little-endian
path-field length. The remaining bounded bytes are split between a general path
and a ZIP entry name. Expected validation errors are ignored; any successful
validation that escapes the fixed root, or any unexpected exception, crashes.
"""

from __future__ import annotations

import importlib
import stat
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Sequence


MAX_FIELD_BYTES = 512
MAX_INPUT_BYTES = 3 + (2 * MAX_FIELD_BYTES)
DEFAULT_RUNS = 1024
DEFAULT_TIMEOUT_SECONDS = 5
DEFAULT_RSS_LIMIT_MB = 1024
_FUZZ_ROOT = (Path.cwd() / ".atheris-validation-root").resolve(strict=False)

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


@dataclass(frozen=True)
class _Targets:
    pathsafe: ModuleType
    update_extract: ModuleType


_TARGETS: _Targets | None = None


def _load_targets() -> _Targets:
    global _TARGETS
    if _TARGETS is None:
        _TARGETS = _Targets(
            pathsafe=importlib.import_module("core.utils.pathsafe"),
            update_extract=importlib.import_module("core.services.update_extract"),
        )
    return _TARGETS


def _split_input(data: bytes) -> tuple[int, str, str]:
    bounded = bytes(data[:MAX_INPUT_BYTES])
    if not bounded or bounded[0] & 0x80:
        flags = bounded[0] if bounded else 0x80
        if len(bounded) > 1 and bounded[1] & 0x80:
            return flags, "\ud800", "\ud800"
        token = (bounded[1:65].hex() or "entry")
        shapes = (
            f"safe/{token}.txt",
            f"../{token}.txt",
            f"safe/../{token}.txt",
            f"/{token}.txt",
            f"C:\\{token}.txt",
            f"safe:{token}.txt",
            f"safe/\x01{token}.txt",
            f"\\\\server\\{token}.txt",
        )
        return flags, shapes[(flags >> 1) & 0x07], shapes[(flags >> 4) & 0x07]

    header = bounded[:3].ljust(3, b"\0")
    payload = bounded[3:]
    path_length = int.from_bytes(header[1:3], "little") % (len(payload) + 1)
    path_bytes = payload[:path_length][:MAX_FIELD_BYTES]
    zip_bytes = payload[path_length:][:MAX_FIELD_BYTES]
    return (
        header[0],
        path_bytes.decode("utf-8", errors="replace"),
        zip_bytes.decode("utf-8", errors="replace"),
    )


def _assert_below_root(candidate: Path) -> None:
    try:
        candidate.relative_to(_FUZZ_ROOT)
    except ValueError as exc:
        raise AssertionError("validator returned a path outside the fuzz root") from exc


def TestOneInput(data: bytes) -> None:
    """Exercise both path validators with one bounded byte string."""

    targets = _load_targets()
    flags, path_value, zip_name = _split_input(data)

    try:
        resolved_path = targets.pathsafe.resolve_path_under_roots(path_value, (_FUZZ_ROOT,))
    except targets.pathsafe.PathSafetyError:
        pass  # Expected non-fatal rejection; unexpected exceptions must remain fuzz crashes.
    else:
        _assert_below_root(resolved_path)

    zip_info = zipfile.ZipInfo(zip_name)
    if flags & 0x01:
        zip_info.external_attr = (stat.S_IFLNK | 0o777) << 16

    try:
        destination = targets.update_extract._validated_zip_destination(zip_info, _FUZZ_ROOT)
    except targets.update_extract.ArtifactExtractError:
        pass  # Expected non-fatal rejection; unexpected exceptions must remain fuzz crashes.
    else:
        _assert_below_root(destination)


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
