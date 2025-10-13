from __future__ import annotations

from pathlib import Path

import core.retention as retention


def _make_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_prune_old_runs_respects_keep_count_and_current_run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LOG_RETENTION_RUNS", "1")
    monkeypatch.setenv("UNIFIED_MAX_LINES", "100")

    reports_root = _make_dir(Path("reports"))
    docs_root = _make_dir(Path("docs/master_index_reports"))

    _make_dir(reports_root / "run_12_20240101_000000")
    _make_dir(reports_root / "run_12_20240102_000000")
    _make_dir(reports_root / "run_12_20240103_000000")

    _make_dir(docs_root / "master_index_20240101T000000Z")
    _make_dir(docs_root / "master_index_20240102T000000Z")
    _make_dir(docs_root / "master_index_20240103T000000Z")

    report = retention.prune_old_runs(
        dry_run=False,
        current_run_id="12_20240101_000000",
        verbose=False,
    )

    remaining_reports = {path.name for path in reports_root.iterdir() if path.is_dir()}
    assert remaining_reports == {"run_12_20240101_000000", "run_12_20240103_000000"}

    remaining_docs = {path.name for path in docs_root.iterdir() if path.is_dir()}
    assert remaining_docs == {
        "master_index_20240101T000000Z",
        "master_index_20240103T000000Z",
    }

    assert any("run_12_20240102_000000" in str(path) for path in report.planned_prune_paths)
    assert any("master_index_20240102T000000Z" in str(path) for path in report.planned_prune_paths)
    assert not report.dry_run


def test_prune_old_runs_truncates_logs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LOG_RETENTION_RUNS", "5")
    monkeypatch.setenv("UNIFIED_MAX_LINES", "3")

    reports_root = _make_dir(Path("reports"))
    log_path = reports_root / "all.log"
    log_path.write_text("\n".join(f"line {idx}" for idx in range(6)) + "\n", encoding="utf-8")

    report = retention.prune_old_runs(dry_run=False, verbose=False)

    content = log_path.read_text(encoding="utf-8").splitlines()
    remaining_log_lines = [line for line in content if line.startswith("line ")]
    assert "line 0" not in content
    assert "line 1" not in content
    assert "line 2" not in content
    assert remaining_log_lines
    assert remaining_log_lines[-1] == "line 5"
    assert all(int(line.split()[1]) >= 3 for line in remaining_log_lines)
    assert log_path in report.truncated_files
    assert not report.planned_prune_paths

    # Dry-run should not modify the file
    log_path.write_text("\n".join(f"line {idx}" for idx in range(6)) + "\n", encoding="utf-8")
    report_preview = retention.prune_old_runs(dry_run=True, verbose=False)
    assert log_path.read_text(encoding="utf-8").splitlines()[0] == "line 0"
    assert log_path in report_preview.planned_truncations
    assert report_preview.dry_run
