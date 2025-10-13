"""Alpha Core entry point."""

from __future__ import annotations

import sys
from pathlib import Path

from tgc.cli_main import main as cli_main

__version__ = (Path(__file__).resolve().parents[0] / "VERSION").read_text().strip()
print(f"TGC Controller — version {__version__}")


def main() -> int:
    return cli_main()


if __name__ == "__main__":
    sys.exit(main())
