"""Alpha Core entry point."""

from __future__ import annotations

import sys
from typing import Iterable

from core.api.app_router import router as app_router
from core.api.http import APP as app
from core.version import VERSION
from tgc.cli_main import main as cli_main


def _has_domain_routes(routes: Iterable[object]) -> bool:
    for route in routes:
        path = getattr(route, "path", "")
        if isinstance(path, str) and path.startswith("/app/"):
            return True
    return False


if not _has_domain_routes(app.router.routes):
    app.include_router(app_router, prefix="/app")

print(f"TGC Controller — version {VERSION}")


def main() -> int:
    return cli_main()


__all__ = ["app", "main"]


if __name__ == "__main__":
    sys.exit(main())
