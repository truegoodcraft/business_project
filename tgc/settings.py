from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from platformdirs import PlatformDirs


_platform_dirs = PlatformDirs(appname="buscore", appauthor="tgc", ensure_exists=True)
BUSCORE_HOME: Path = Path(_platform_dirs.user_data_dir)
DATA_DIR: Path = BUSCORE_HOME / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8765

    model_config = SettingsConfigDict(env_prefix="BUSCORE_", extra="ignore")
