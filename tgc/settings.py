from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings
from platformdirs import PlatformDirs


_platform_dirs = PlatformDirs(appname="buscore", appauthor="tgc", ensure_exists=True)
BUSCORE_HOME: Path = Path(_platform_dirs.user_data_dir)
DATA_DIR: Path = BUSCORE_HOME / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8765
    buscore_home: str | None = Field(default=None, alias="BUSCORE_HOME")
    session_cookie_name: str = "bus_session"
    same_site: str = "lax"
    secure_cookie: bool = False

    # Version-agnostic config for pydantic-settings 2.x
    model_config = {
        "env_prefix": "BUSCORE_",
        "env_file": ".env",
        "extra": "ignore",
        "populate_by_name": True,
    }

    def dirs(self) -> PlatformDirs:
        return PlatformDirs(appname="buscore", appauthor="tgc", ensure_exists=True)

    def resolve_data_dir(self) -> Path:
        base = Path(self.buscore_home) if self.buscore_home else Path(self.dirs().user_data_path)
        base.mkdir(parents=True, exist_ok=True)
        return base
