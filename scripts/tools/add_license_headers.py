# SPDX-License-Identifier: AGPL-3.0-or-later
"""Utility to inject SPDX headers across source files."""
import datetime
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
YEAR = str(datetime.datetime.now().year)
OWNER = "BUS Core Authors"
SPDX = "SPDX-License-Identifier: AGPL-3.0-or-later"
COPY = f"Copyright (C) {YEAR} {OWNER}"

COMMENT = {
    ".py": ("# ",),
    ".ps1": ("# ",),
    ".js": ("// ",),
    ".ts": ("// ",),
    ".css": ("/* ",),
    ".html": ("<!-- ",),
}


def has_spdx(text: str) -> bool:
    return SPDX in text


def inject(text: str, ext: str) -> str:
    if has_spdx(text):
        return text
    prefix = COMMENT[ext][0]
    header = f"{prefix}{COPY}\n{prefix}{SPDX}\n\n"
    if text.startswith("#!") and ext == ".py":
        nl = text.find("\n") + 1
        return text[:nl] + header + text[nl:]
    return header + text


def should(path: pathlib.Path) -> bool:
    if path.is_dir():
        return False
    if any(part in (".git", ".venv", "venv", "__pycache__", "node_modules") for part in path.parts):
        return False
    return path.suffix in COMMENT


def main() -> None:
    changed = 0
    for p in ROOT.rglob("*"):
        if not should(p):
            continue
        txt = p.read_text(encoding="utf-8", errors="replace")
        new = inject(txt, p.suffix)
        if new != txt:
            p.write_text(new, encoding="utf-8")
            changed += 1
    print(f"[license] Headers ensured. Files changed: {changed}")


if __name__ == "__main__":
    main()
