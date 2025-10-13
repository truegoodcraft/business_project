"""Helpers for rendering the normalized CLI menu."""

from __future__ import annotations

from typing import Iterable, Mapping, Sequence, Tuple

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


def render_menu(
    menu_spec: MenuSpec,
    *,
    available: Mapping[str, Tuple[str, str]] | None = None,
) -> str:
    """Render the menu using ``menu_spec`` and optional overrides."""

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
        resolved.append((section, section_entries))

    number_width = max(
        (len(key) for _, entries in resolved for key, _ in entries),
        default=1,
    )
    lines: list[str] = []
    for idx, (section, entries) in enumerate(resolved):
        if not entries:
            continue
        if lines:
            lines.append("")
        lines.append(section)
        for key, label in entries:
            lines.append(f"  {key.ljust(number_width)}  {label}")
    return "\n".join(lines)


def format_help_lines(*, debug: bool = False) -> Iterable[str]:
    """Return help text lines for the CLI menu."""

    yield format_banner(debug=debug)
    yield f"tagline: {brand.TAGLINE}"
    yield "Common flags: --quiet, --debug, --max-seconds, --max-items, --max-requests"
    yield "Press a number, letter action ID, or 'q' to quit."
