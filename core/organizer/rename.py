"""Filename normalization helpers for Organizer."""

from __future__ import annotations

import os
import re


def normalize_filename(name: str) -> str:
    """Return a conservatively normalized filename."""

    base, ext = os.path.splitext(name)
    base = re.sub(r"[._-]+", " ", base)
    base = re.sub(r"\s+", " ", base).strip()
    normalized = base or "unnamed"
    return normalized + ext
