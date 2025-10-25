"""Archive the legacy plugins/ directory into archive/plugins_legacy_YYYYMMDD."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    legacy = root / "plugins"
    if not legacy.exists():
        print("No legacy plugins folder found; nothing to do.")
        return
    timestamp = datetime.utcnow().strftime("%Y%m%d")
    archive_root = root / "archive"
    archive_root.mkdir(parents=True, exist_ok=True)
    destination = archive_root / f"plugins_legacy_{timestamp}"
    if destination.exists():
        raise SystemExit(f"Destination already exists: {destination}")
    legacy.rename(destination)
    print(f"Archived legacy plugins to: {destination}")

    echo_source = root / "plugins" / "echo"
    if echo_source.exists():
        echo_dest = destination / "echo"
        echo_dest.parent.mkdir(parents=True, exist_ok=True)
        echo_source.rename(echo_dest)
        print(f"Moved echo plugin to: {echo_dest}")


if __name__ == "__main__":
    main()
