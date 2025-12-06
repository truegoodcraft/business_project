import importlib
import sqlite3
import sys
from pathlib import Path

import pytest


@pytest.fixture()
def modules(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "lad"))
    monkeypatch.setenv("BUS_DB", str(tmp_path / "lad" / "app" / "app.db"))

    for module_name in [
        "core.utils.export",
        "core.config.paths",
        "core.backup.crypto",
    ]:
        sys.modules.pop(module_name, None)

    crypto = importlib.import_module("core.backup.crypto")
    crypto = importlib.reload(crypto)
    export = importlib.import_module("core.utils.export")
    export = importlib.reload(export)
    return export, crypto


def test_export_preview_commit_restores_and_archives(modules):
    export_module, _ = modules
    app_db = export_module.APP_DB
    journal_dir = export_module.JOURNAL_DIR
    exports_dir = export_module.EXPORTS_DIR

    app_db.parent.mkdir(parents=True, exist_ok=True)
    journal_dir.mkdir(parents=True, exist_ok=True)
    exports_dir.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(app_db) as con:
        con.execute("create table sample (val text)")
        con.execute("insert into sample (val) values ('before')")
        con.commit()

    for name in ("inventory.jsonl", "manufacturing.jsonl"):
        (journal_dir / name).write_text("before\n", encoding="utf-8")

    export_res = export_module.export_db("pw")
    assert export_res["ok"] is True
    export_path = Path(export_res["path"])
    assert export_path.exists()

    with sqlite3.connect(app_db) as con:
        con.execute("update sample set val='after'")
        con.commit()

    for name in ("inventory.jsonl", "manufacturing.jsonl"):
        (journal_dir / name).write_text("after\n", encoding="utf-8")

    preview = export_module.import_preview(export_res["path"], "pw")
    assert preview["ok"] is True

    commit = export_module.import_commit(export_res["path"], "pw")
    assert commit["ok"] is True

    with sqlite3.connect(app_db) as con:
        row = con.execute("select val from sample").fetchone()
        assert row[0] == "before"

    archived = list(journal_dir.glob("*.jsonl.pre-restore-*"))
    assert len(archived) == 2
    assert all(path.read_text(encoding="utf-8").startswith("after") for path in archived)

    for name in ("inventory.jsonl", "manufacturing.jsonl"):
        fresh = journal_dir / name
        assert fresh.exists()
        assert fresh.read_text(encoding="utf-8") == ""
