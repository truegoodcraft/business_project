"""Controller package exports."""

from importlib.metadata import version, PackageNotFoundError

__all__ = ["get_version"]


def get_version() -> str:
    """Return the package version if installed, otherwise ``"0.1.0"``."""
    try:
        return version("tgc")
    except PackageNotFoundError:  # pragma: no cover - fallback for editable installs
        return "0.1.0"
