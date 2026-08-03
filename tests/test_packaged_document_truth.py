# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]
LEGAL_AND_OPERATIONAL_SOURCE_FILES = {
    "CODE_OF_CONDUCT.md",
    "COMMERCIAL-LICENSE.md",
    "CONTRIBUTING.MD",
    "EULA.md",
    "LICENSE-AGPL-3.0.txt",
    "LICENSE.md",
    "MAINTAINER_NOTICE.md",
    "PRIVACY.md",
    "THIRD_PARTY_LICENSES.md",
    "TRADEMARKS.md",
}


def _stage_packaged_documents(tmp_path: Path) -> Path:
    stage = tmp_path / "BUS-Core-test"
    stage.mkdir(parents=True)
    shutil.copy2(REPO_ROOT / "README.md", stage / "README.md")
    shutil.copytree(REPO_ROOT / "license", stage / "license")
    shutil.copy2(REPO_ROOT / "SOT.md", stage / "license" / "SOT.md")
    return stage


def test_staged_package_contains_current_document_authorities_only(tmp_path: Path) -> None:
    stage = _stage_packaged_documents(tmp_path)
    license_files = {path.name for path in (stage / "license").iterdir() if path.is_file()}

    assert license_files == LEGAL_AND_OPERATIONAL_SOURCE_FILES | {"SOT.md"}
    assert not {"API_CONTRACT.md", "CHANGELOG.md", "README.md"} & license_files

    privacy = (stage / "license" / "PRIVACY.md").read_text(encoding="utf-8")
    eula = (stage / "license" / "EULA.md").read_text(encoding="utf-8")
    sot = (stage / "license" / "SOT.md").read_text(encoding="utf-8")
    shipped_truth = "\n".join((privacy, eula, sot))

    assert "sends nothing until that disclosure is acknowledged with telemetry enabled" in privacy
    assert "Turning telemetry off clears the unsent queue" in privacy
    assert "Worker 1.27.0 are deployed and production-verified" in privacy
    assert "does not silently overwrite the running installation" in eula
    assert "launch an unverified artifact" in eula
    assert 'Absolute "no telemetry" claims are retired' in sot
    assert "zero telemetry" not in shipped_truth.lower()


def test_build_authorities_stage_license_directory_and_canonical_sot() -> None:
    spec = (REPO_ROOT / "BUS-Core.spec").read_text(encoding="utf-8")
    build_script = (REPO_ROOT / "scripts" / "build_core.ps1").read_text(encoding="utf-8")

    assert "(str(ROOT / 'license'), 'license')" in spec
    assert "(str(ROOT / 'SOT.md'), 'license')" in spec
    assert 'Copy-Item $LicensePath (Join-Path $stagePath "license") -Recurse -Force' in build_script
    assert 'Copy-Item $SotPath (Join-Path $stagePath "license\\SOT.md") -Force' in build_script
