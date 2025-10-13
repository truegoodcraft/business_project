"""Helpers for rendering the normalized CLI menu."""

from __future__ import annotations

from typing import Iterable, Mapping, Sequence, Tuple

from core.brand import NAME, VENDOR
from core.menu_spec import MENU_SPEC

from . import brand

MenuItems = Sequence[Tuple[str, str]]
MenuSpec = Sequence[Tuple[str, MenuItems]]


def format_banner(*, debug: bool = False) -> str:
    """Return the standard banner string."""

    title = f"{brand.NAME} — Controller Menu"
    if debug:
        title += " (debug)"
    lines = [title, f"made by: {brand.VENDOR}"]
    return "\n".join(lines)


def _render_menu_text(
    menu_spec: MenuSpec,
    *,
    available: Mapping[str, Tuple[str, str]] | None = None,
) -> str:
    resolved: list[tuple[str, list[tuple[str, str]]]] = []
    for section, items in menu_spec:
        section_entries: list[Tuple[str, str]] = []
        for key, label in items:
            if available is not None and key not in available:
                continue
            if label:
                display = label
            elif available is not None and key in available:
                name, description = available[key]
                display = f"{name} — {description}" if description else name
            else:
                display = label
            section_entries.append((key, display))
        if section_entries:
            resolved.append((section, section_entries))

    number_width = max((len(key) for _, entries in resolved for key, _ in entries), default=1)
    lines: list[str] = []
    for index, (section, entries) in enumerate(resolved):
        if lines:
            lines.append("")
        lines.append(section)
        for key, label in entries:
            lines.append(f"  {key.ljust(number_width)}  {label}")
    return "\n".join(lines)


def render_menu(quiet: bool = False, *legacy_args, **legacy_kwargs):
    """Render the normalized menu.

    When invoked with a boolean ``quiet`` flag (the new interface), the menu is
    printed directly. Legacy callers can continue to pass a ``menu_spec`` and
    optional ``available`` mapping to receive a formatted string.
    """

    if not isinstance(quiet, bool) or legacy_args or legacy_kwargs:
        if isinstance(quiet, bool):
            menu_spec = legacy_kwargs.pop("menu_spec", MENU_SPEC)
            available = legacy_kwargs.get("available")
        else:
            menu_spec = quiet  # type: ignore[assignment]
            available = legacy_kwargs.get("available")
        return _render_menu_text(menu_spec, available=available)

    if not quiet:
        print(f"{NAME} — Controller Menu")
        print(f"made by: {VENDOR}")
        print()

    for section, items in MENU_SPEC:
        print(section)
        for key, label in items:
            print(f"{key:>3}) {label}")
        print()

    print("Select an option (or q to quit): ", end="")


def format_help_lines(*, debug: bool = False) -> Iterable[str]:
    """Return help text lines for the CLI menu."""

    yield format_banner(debug=debug)
    yield f"tagline: {brand.TAGLINE}"
    yield "Common flags: --quiet, --debug, --max-seconds, --max-items, --max-requests"
    yield "Press a number, letter action ID, or 'q' to quit."
