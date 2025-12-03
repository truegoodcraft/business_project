import os, sys
from core.appdb.ensure import DB_PATH, ensure_schema

if __name__ == "__main__":
    try:
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
            print(f"[reset] removed {DB_PATH}")
    except Exception as e:
        print(f"[reset] could not remove {DB_PATH}: {e}")
        sys.exit(1)

    res = ensure_schema()
    print(f"[reset] recreated baseline: {res}")
