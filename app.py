"""Alpha Core entry point."""

from __future__ import annotations

import sys

from tgc.cli_main import main as cli_main


def main() -> int:
    return cli_main()


if __name__ == "__main__":
    sys.exit(main())
