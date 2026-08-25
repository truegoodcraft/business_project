# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LOCK_FILES = (
    REPO_ROOT / "requirements-linux.lock.txt",
    REPO_ROOT / "requirements-windows.lock.txt",
    REPO_ROOT / "requirements-test-linux.lock.txt",
    REPO_ROOT / "requirements-test-windows.lock.txt",
)


def _logical_requirements(path: Path) -> list[str]:
    requirements: list[str] = []
    current: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if raw_line[:1].isspace():
            assert current, f"orphaned continuation in {path.name}: {raw_line}"
            current.append(stripped.removesuffix("\\").strip())
            continue
        if current:
            requirements.append(" ".join(current))
        current = [stripped.removesuffix("\\").strip()]
    if current:
        requirements.append(" ".join(current))
    return requirements


def test_dependency_locks_are_exact_and_hash_checked() -> None:
    exact_pin = re.compile(r"^[A-Za-z0-9_.-]+==[^ ;]+(?:\s*;.*)?$")
    for lock_path in LOCK_FILES:
        requirements = _logical_requirements(lock_path)
        assert requirements, f"empty dependency lock: {lock_path.name}"
        for requirement in requirements:
            declaration, *hashes = requirement.split(" --hash=sha256:")
            assert exact_pin.fullmatch(declaration), (
                f"non-exact dependency in {lock_path.name}: {declaration}"
            )
            assert hashes, f"missing SHA-256 hash in {lock_path.name}: {declaration}"
            assert all(re.fullmatch(r"[0-9a-f]{64}", digest) for digest in hashes)


def test_platform_locks_keep_release_tools_out_of_linux_runtime() -> None:
    linux = (REPO_ROOT / "requirements-linux.lock.txt").read_text(encoding="utf-8")
    windows = (REPO_ROOT / "requirements-windows.lock.txt").read_text(encoding="utf-8")

    assert "\npyinstaller==" not in linux
    assert "\npywin32==" not in linux
    assert "\npyinstaller==6.21.0 \\" in windows
    assert "\npywin32==312 \\" in windows
    assert "\nwheel==0.48.0 \\" in windows


def test_ci_uses_matching_hash_locked_test_graphs() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    security_workflow = (REPO_ROOT / ".github" / "workflows" / "security-audit.yml").read_text(
        encoding="utf-8"
    )
    test_policy = (REPO_ROOT / "requirements-test.txt").read_text(encoding="utf-8")
    linux_test_lock = (REPO_ROOT / "requirements-test-linux.lock.txt").read_text(encoding="utf-8")
    windows_test_lock = (REPO_ROOT / "requirements-test-windows.lock.txt").read_text(encoding="utf-8")

    assert "pytest==9.1.1" in test_policy
    assert "hypothesis==6.165.10" in test_policy
    assert "\npytest==9.1.1 \\" in linux_test_lock
    assert "\nhypothesis==6.165.10 \\" in linux_test_lock
    assert "\ncolorama==" not in linux_test_lock
    assert "\npytest==9.1.1 \\" in windows_test_lock
    assert "\nhypothesis==6.165.10 \\" in windows_test_lock
    assert "\ncolorama==0.4.6 \\" in windows_test_lock
    assert "test-lockfile: requirements-test-linux.lock.txt" in workflow
    assert "test-lockfile: requirements-test-windows.lock.txt" in workflow
    assert 'pip install --require-hashes -r "${{ matrix.test-lockfile }}"' in workflow
    assert 'pip install "pytest==9.1.1"' not in workflow
    assert "test-lockfile: requirements-test-linux.lock.txt" in security_workflow
    assert "test-lockfile: requirements-test-windows.lock.txt" in security_workflow
    assert 'python -m pip_audit\n          --require-hashes\n          -r "${{ matrix.test-lockfile }}"' in security_workflow


def test_container_uses_digest_pinned_image_and_linux_lock() -> None:
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert re.search(r"^FROM python:3\.12-slim@sha256:[0-9a-f]{64}$", dockerfile, re.MULTILINE)
    assert "COPY requirements-linux.lock.txt ." in dockerfile
    assert "--only-binary=:all:" in dockerfile
    assert "--require-hashes" in dockerfile
    assert "-r requirements-linux.lock.txt" in dockerfile
    assert "apt-get" not in dockerfile
    assert "urllib.request.urlopen" in dockerfile
