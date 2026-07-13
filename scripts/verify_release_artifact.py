# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fail-closed structural verification for BUS Core release artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Callable


MIN_ONEFILE_BYTES = 1_000_000
REQUIRED_ARCHIVE_ENTRIES = {
    "launcher",
    "PYZ.pyz",
    "python311.dll",
    "core/ui/shell.html",
    "license/SOT.md",
}


class VerificationError(RuntimeError):
    """The candidate is not a complete BUS Core release artifact."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _archive_reader(path: Path) -> Any:
    try:
        from PyInstaller.archive.readers import CArchiveReader
    except ImportError as exc:  # pragma: no cover - exercised by the release environment
        raise VerificationError("PyInstaller is required to inspect the embedded onefile archive") from exc

    try:
        return CArchiveReader(str(path))
    except Exception as exc:
        raise VerificationError(f"missing or unreadable PyInstaller CArchive: {exc}") from exc


def inspect_executable(
    path: Path,
    *,
    reader_factory: Callable[[Path], Any] | None = None,
) -> dict[str, Any]:
    path = path.resolve(strict=True)
    size = path.stat().st_size
    if size < MIN_ONEFILE_BYTES:
        raise VerificationError(
            f"launcher-only executable ({size} bytes); expected an embedded onefile runtime"
        )

    reader = (reader_factory or _archive_reader)(path)
    entries = {str(name).replace("\\", "/") for name in reader.toc}
    missing = sorted(REQUIRED_ARCHIVE_ENTRIES - entries)
    if missing:
        raise VerificationError(f"embedded archive is missing required entries: {', '.join(missing)}")

    return {
        "artifact": str(path),
        "bytes": size,
        "sha256": _sha256(path),
        "embedded_entries": len(entries),
        "required_entries": sorted(REQUIRED_ARCHIVE_ENTRIES),
    }


def inspect_zip(
    path: Path,
    *,
    expected_exe_name: str,
    expected_exe_source: Path | None = None,
    reader_factory: Callable[[Path], Any] | None = None,
) -> dict[str, Any]:
    path = path.resolve(strict=True)
    with zipfile.ZipFile(path) as archive:
        file_entries = [item for item in archive.infolist() if not item.is_dir()]
        names = {item.filename.replace("\\", "/") for item in file_entries}
        required = {expected_exe_name, "README.md", "license/SOT.md"}
        missing = sorted(required - names)
        if missing:
            raise VerificationError(f"ZIP is missing required entries: {', '.join(missing)}")

        unexpected_roots = sorted(
            {
                name.split("/", 1)[0]
                for name in names
                if name.split("/", 1)[0] not in {expected_exe_name, "README.md", "license"}
            }
        )
        if unexpected_roots:
            raise VerificationError(f"ZIP has unexpected root entries: {', '.join(unexpected_roots)}")

        exe_info = archive.getinfo(expected_exe_name)
        if exe_info.file_size < MIN_ONEFILE_BYTES:
            raise VerificationError(
                f"ZIP contains a launcher-only executable ({exe_info.file_size} bytes)"
            )

        with tempfile.TemporaryDirectory(prefix="buscore-release-verify-") as temp_dir:
            extracted = Path(temp_dir) / expected_exe_name
            with archive.open(exe_info) as source, extracted.open("wb") as target:
                shutil.copyfileobj(source, target)
            exe_result = inspect_executable(extracted, reader_factory=reader_factory)

        if expected_exe_source is not None:
            source = expected_exe_source.resolve(strict=True)
            source_hash = _sha256(source)
            if exe_result["sha256"] != source_hash:
                raise VerificationError("ZIP executable hash does not match the release executable")

    return {
        "artifact": str(path),
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
        "files": sorted(names),
        "embedded_executable_bytes": exe_info.file_size,
        "embedded_executable_sha256": exe_result["sha256"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    exe_parser = subparsers.add_parser("exe", help="verify a PyInstaller onefile executable")
    exe_parser.add_argument("path", type=Path)

    zip_parser = subparsers.add_parser("zip", help="verify a complete release ZIP")
    zip_parser.add_argument("path", type=Path)
    zip_parser.add_argument("--expected-exe", required=True)
    zip_parser.add_argument("--expected-exe-source", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command == "exe":
            result = inspect_executable(args.path)
        else:
            result = inspect_zip(
                args.path,
                expected_exe_name=args.expected_exe,
                expected_exe_source=args.expected_exe_source,
            )
    except (OSError, VerificationError, zipfile.BadZipFile) as exc:
        print(f"[FAIL] {exc}")
        return 1

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
