# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.verify_release_artifact import VerificationError, inspect_executable, inspect_zip


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _complete_toc() -> dict[str, object]:
    return {
        "launcher": object(),
        "PYZ.pyz": object(),
        "python311.dll": object(),
        "core/ui/shell.html": object(),
        "license/SOT.md": object(),
    }


def test_spec_explicitly_defines_onefile_release_mode() -> None:
    spec = _read("BUS-Core.spec")

    assert "exclude_binaries=False" in spec
    assert "append_pkg=True" in spec
    assert "COLLECT(" not in spec


def test_build_toolchain_is_pinned_and_includes_runtime_requirements() -> None:
    requirements = _read("requirements-build.txt")
    windows_lock = _read("requirements-windows.lock.txt")

    assert "-r requirements.txt" in requirements
    assert "pyinstaller==6.21.0" in requirements
    assert "pyinstaller-hooks-contrib==2026.6" in requirements
    assert "pyinstaller==6.21.0 \\" in windows_lock
    assert "--hash=sha256:" in windows_lock


def test_repository_source_guard_ignores_workspace_tool_environments() -> None:
    source_guard = _read("tests/test_empty_except_guard.py")

    assert '".tools"' in source_guard


def test_build_script_fails_closed_around_native_and_artifact_checks() -> None:
    script = _read("scripts/build_core.ps1")

    assert "pip show pyinstaller" not in script
    assert "install --upgrade pyinstaller" not in script
    assert '"--require-hashes", "-r", $buildLock' in script
    assert 'Join-Path $ROOT "requirements-windows.lock.txt"' in script
    assert "Select-String -LiteralPath $buildLock" in script
    assert '[string]$BuildPythonPath = ""' in script
    assert 'Invoke-NativeChecked' in script
    assert 'PyInstaller onefile build' in script
    assert 'Assert-OnefileArchive' in script
    assert 'Assert-LaunchSmoke' in script
    assert script.index('-Label "unsigned-versioned"') < script.index('if ($Sign)')
    assert '-Label "signed-versioned"' in script
    assert 'Release ZIP verification' in script


def test_launcher_only_executable_is_rejected(tmp_path: Path) -> None:
    candidate = tmp_path / "BUS-Core.exe"
    candidate.write_bytes(b"MZ" + b"\0" * 300_000)

    with pytest.raises(VerificationError, match="launcher-only"):
        inspect_executable(candidate)


def test_complete_embedded_archive_contract_is_accepted(tmp_path: Path) -> None:
    candidate = tmp_path / "BUS-Core.exe"
    candidate.write_bytes(b"MZ" + b"\0" * 1_100_000)

    result = inspect_executable(
        candidate,
        reader_factory=lambda _path: SimpleNamespace(toc=_complete_toc()),
    )

    assert result["bytes"] == candidate.stat().st_size
    assert result["embedded_entries"] == len(_complete_toc())


def test_zip_cannot_ship_only_a_launcher(tmp_path: Path) -> None:
    archive_path = tmp_path / "BUS-Core-1.4.0.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("BUS-Core-1.4.0.exe", b"MZ" + b"\0" * 300_000)
        archive.writestr("README.md", "readme")
        archive.writestr("license/SOT.md", "sot")

    with pytest.raises(VerificationError, match="launcher-only"):
        inspect_zip(archive_path, expected_exe_name="BUS-Core-1.4.0.exe")


def test_zip_contains_the_verified_executable_and_required_documents(tmp_path: Path) -> None:
    executable = tmp_path / "BUS-Core-1.4.0.exe"
    executable.write_bytes(b"MZ" + b"\0" * 1_100_000)
    archive_path = tmp_path / "BUS-Core-1.4.0.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.write(executable, executable.name)
        archive.writestr("README.md", "readme")
        archive.writestr("license/SOT.md", "sot")

    result = inspect_zip(
        archive_path,
        expected_exe_name=executable.name,
        expected_exe_source=executable,
        reader_factory=lambda _path: SimpleNamespace(toc=_complete_toc()),
    )

    assert result["embedded_executable_bytes"] == executable.stat().st_size
    assert result["files"] == ["BUS-Core-1.4.0.exe", "README.md", "license/SOT.md"]
