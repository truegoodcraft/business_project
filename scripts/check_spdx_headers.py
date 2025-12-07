# Copyright (C) 2025 BUS Core Authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core"
PLUGS = ROOT / "plugins"

REQ = {"core": "PolyForm-Noncommercial-1.0.0", "plugins": "Apache-2.0"}
SKIP_DIRS = {".git", ".github", ".venv", "venv", "__pycache__", "dist", "build"}

def head(p: Path, n=6) -> str:
    try: return "".join(p.read_text(encoding="utf-8").splitlines(True)[:n])
    except Exception: return ""

def check_tree(base: Path, expect: str) -> list[str]:
    miss=[]
    for p in base.rglob("*.py"):
        if any(part in SKIP_DIRS or part.startswith(".") for part in p.parts): continue
        if f"SPDX-License-Identifier: {expect}" not in head(p):
            miss.append(str(p.relative_to(ROOT)))
    return miss

def main()->int:
    probs=[]
    if CORE.exists(): probs += [f"[core] {p}" for p in check_tree(CORE, REQ["core"])]
    if PLUGS.exists():
        for sub in PLUGS.iterdir():
            if sub.is_dir() and not sub.name.startswith("_"):
                probs += [f"[plugins] {p}" for p in check_tree(sub, REQ["plugins"])]
    if probs:
        print("Missing/incorrect SPDX headers in:")
        for p in probs: print(" -", p)
        print("\nFix: run `python scripts/add_spdx_headers.py` and commit.")
        return 1
    print("All SPDX headers OK.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
