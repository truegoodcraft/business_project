# SPDX-License-Identifier: AGPL-3.0-or-later
"""Drift guard: one canonical version source, no hardcoded semver in UI JS."""
import re
import tomllib
from pathlib import Path

from core.version import INTERNAL_VERSION, VERSION

REPO_ROOT = Path(__file__).parent.parent
UI_JS_DIR = REPO_ROOT / "core" / "ui" / "js"
SEMVER_RE = re.compile(r"\b\d+\.\d+\.\d+\b")
STRICT_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
INTERNAL_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+\.\d+$")


def test_version_has_strict_semver_format():
    """Public VERSION must remain strict X.Y.Z."""
    assert STRICT_VERSION_RE.match(VERSION), (
        f"core/version.py VERSION={VERSION!r} must be strict X.Y.Z."
    )


def test_internal_version_has_expected_four_part_format():
    """Internal working version must remain X.Y.Z.R."""
    assert INTERNAL_VERSION_RE.match(INTERNAL_VERSION), (
        f"core/version.py INTERNAL_VERSION={INTERNAL_VERSION!r} must be X.Y.Z.R."
    )
    assert INTERNAL_VERSION.startswith(f"{VERSION}."), (
        f"INTERNAL_VERSION={INTERNAL_VERSION!r} must extend VERSION={VERSION!r}."
    )


def test_pyproject_version_matches_canonical():
    """pyproject.toml [project] version must equal core.version.VERSION."""
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    declared = data["project"]["version"]
    assert declared == VERSION, (
        f"pyproject.toml version={declared!r} does not match core/version.py VERSION={VERSION!r}. "
        "Update pyproject.toml to match core/version.py."
    )


def test_no_hardcoded_semver_in_ui_js():
    """No semver literals in runtime UI JS (changelog/docs are not here)."""
    violations: list[str] = []
    for js_file in UI_JS_DIR.rglob("*.js"):
        text = js_file.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            for m in SEMVER_RE.finditer(line):
                violations.append(f"{js_file.relative_to(UI_JS_DIR)}:{lineno}: {m.group()!r}")
    assert not violations, (
        "Hardcoded semver literals found in core/ui/js/ — remove them:\n"
        + "\n".join(violations)
    )


def test_release_update_surfaces_use_public_version_only():
    update_route = (REPO_ROOT / "core" / "api" / "routes" / "update.py").read_text(encoding="utf-8")
    update_service = (REPO_ROOT / "core" / "services" / "update.py").read_text(encoding="utf-8")
    workflow = (REPO_ROOT / ".github" / "workflows" / "release-mirror.yml").read_text(encoding="utf-8")

    assert "INTERNAL_VERSION" not in update_route
    assert "INTERNAL_VERSION" not in update_service
    assert "INTERNAL_VERSION" not in workflow
    assert "from core.version import VERSION as CURRENT_VERSION" in update_route
    assert "from core.version import VERSION as CURRENT_VERSION" in update_service


def test_release_mirror_reads_canonical_version_and_checks_tag_match():
    workflow = (REPO_ROOT / ".github" / "workflows" / "release-mirror.yml").read_text(encoding="utf-8")

    assert "core/version.py" in workflow, (
        "release-mirror workflow must read VERSION from core/version.py."
    )
    assert "does not match core/version.py VERSION" in workflow, (
        "release-mirror workflow must hard-fail when the release tag does not match the canonical VERSION."
    )
    assert "Validate release ref target" in workflow, (
        "release-mirror workflow must validate that a release tag targets the intended default-branch commit."
    )
    assert "DEFAULT_BRANCH_SHA" in workflow and "TAG_SHA" in workflow, (
        "release-mirror workflow must compare the release tag target with the default branch before mirroring."
    )
    assert "Publish the release only after the version bump is on the default branch" in workflow, (
        "release-mirror workflow must explain how to repair a tag created from the wrong commit."
    )
    assert '--arg version "$CANONICAL_VERSION"' in workflow, (
        "release-mirror manifest latest.version must come from the canonical VERSION, not from tag parsing."
    )
    assert 'EXPECTED_ASSET_NAME=BUS-Core-${CANONICAL_VERSION}.zip' in workflow, (
        "release-mirror workflow must target the canonical public ZIP artifact name."
    )
    assert 'startswith("BUS-Core-")' in workflow and 'endswith(".zip")' in workflow, (
        "release-mirror workflow history selection must only include canonical BUS-Core ZIP assets."
    )
    assert 'EXPECTED_ASSET_NAME=BUS-Core-${CANONICAL_VERSION}.exe' not in workflow, (
        "release-mirror workflow must not expect the stale BUS-Core EXE public asset name."
    )


def test_release_check_validates_current_canonical_chain():
    script = (REPO_ROOT / "scripts" / "release-check.ps1").read_text(encoding="utf-8")

    assert "build-windows.ps1" not in script, (
        "scripts/release-check.ps1 must not reference the removed build-windows.ps1 helper."
    )
    assert "build_core.ps1" in script, (
        "scripts/release-check.ps1 must call the canonical build_core.ps1 script."
    )
    assert "smoke_isolated.ps1" in script, (
        "scripts/release-check.ps1 must run the canonical isolated smoke script."
    )
    assert "Smoke script failed:" in script, (
        "scripts/release-check.ps1 must hard-fail when smoke_isolated.ps1 exits non-zero."
    )
    assert "Build script failed:" in script, (
        "scripts/release-check.ps1 must hard-fail when build_core.ps1 exits non-zero."
    )
    assert "BUS-Core.exe" in script and "BUS-Core-{0}.exe" in script, (
        "scripts/release-check.ps1 must assert the real current build artifact names."
    )
    assert "requirements-windows.lock.txt" in script, (
        "release-check must install the governed Windows runtime/build graph."
    )
    assert "requirements-test-windows.lock.txt" in script, (
        "release-check must install the governed test graph."
    )
    assert script.count("--require-hashes") >= 2, (
        "release-check must hash-verify both governed dependency graphs."
    )
    assert "Release check requires Python 3.11.x" in script, (
        "release-check must reject a non-canonical Windows build interpreter."
    )
    assert "buscore-release-check-{0}" in script and "[guid]::NewGuid()" in script, (
        "release-check must create a unique clean environment instead of mutating the user's venv."
    )
    assert "@('-m', 'venv', $TempVenvRoot)" in script, (
        "release-check must build inside a fresh Python 3.11 virtual environment."
    )
    assert "Remove-Item -Path $TempVenvRoot -Recurse -Force" in script, (
        "release-check must remove only its exact temporary environment in finally."
    )
    assert "'-m', 'pytest', '-q'" in script, (
        "release-check must run the test suite before building."
    )
    assert "validate_version_governance.py" in script and "validate_change_trace.py" in script, (
        "release-check must run both governance validations before building."
    )
    assert "'-PythonPath', $VenvPython" in script, (
        "release-check smoke must use the same governed Python environment as the build."
    )
    assert "[switch]$Release" in script and "'-Release'" in script, (
        "release-check must expose and forward an explicit signed-release mode."
    )
    assert "BUS-Core-{0}.zip" in script and "Get-AuthenticodeSignature" in script, (
        "signed-release mode must independently assert the bundle and signer."
    )


def test_governance_wrapper_rejects_an_unusable_repo_venv_before_fallback():
    script = (REPO_ROOT / "scripts" / "governance-check.ps1").read_text(encoding="utf-8")

    assert "Test-Path $python -PathType Leaf" in script
    assert '& $python -c "import sys"' in script
    assert "catch" in script and "$venvUsable = $false" in script
    assert 'Get-Command "python" -CommandType Application -ErrorAction Stop' in script
    assert "validate_version_governance.py" in script
    assert "validate_change_trace.py" in script
