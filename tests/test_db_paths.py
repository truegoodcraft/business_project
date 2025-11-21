# SPDX-License-Identifier: AGPL-3.0-or-later

import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_app_db_path_creates_directory(tmp_path, monkeypatch):
    import core.appdb.paths as appdb_paths

    local_app_data = tmp_path / "LocalAppData"
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))

    db_path = appdb_paths.app_db_path()

    assert db_path == local_app_data / "BUSCore" / "app" / "app.db"
    assert db_path.parent.is_dir()


def test_db_url_uses_posix(monkeypatch, tmp_path):
    local_app_data = tmp_path / "LocalAppData"
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    monkeypatch.delenv("BUS_ROOT", raising=False)

    import core.config.paths as config_paths

    importlib.reload(config_paths)

    assert config_paths.DB_URL.get_backend_name() == "sqlite"
    assert config_paths.DB_URL.database == str(config_paths.DB_PATH)
    assert "\\" not in config_paths.DB_URL.database
