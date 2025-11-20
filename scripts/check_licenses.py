# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGS = ROOT / "plugins"
SKIP = {"_"}  # skip folders starting with _

def missing_plugin_licenses()->list[str]:
    out=[]
    if not PLUGS.exists(): return out
    for sub in PLUGS.iterdir():
        if sub.is_dir() and not sub.name.startswith(tuple(SKIP)):
            if not (sub/"LICENSE").exists():
                out.append(str(sub.relative_to(ROOT)))
    return out

def main()->int:
    miss = missing_plugin_licenses()
    if miss:
        print("Plugins missing LICENSE (Apache-2.0):")
        for p in miss: print(" -", p + "/LICENSE")
        return 1
    print("All plugins have LICENSE files.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
