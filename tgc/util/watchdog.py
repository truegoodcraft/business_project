# SPDX-License-Identifier: AGPL-3.0-or-later
import faulthandler
import sys
import threading
import time
from typing import Optional


def with_watchdog(seconds: int = 45):
    def deco(fn):
        def inner(*a, **kw):
            tripped = {"v": False}

            def timer():
                time.sleep(seconds)
                tripped["v"] = True
                sys.stderr.write(f"[watchdog] {fn.__name__} exceeded {seconds}s — dumping stacks…\n")
                try:
                    faulthandler.dump_traceback(file=sys.stderr, all_threads=True)
                except Exception:
                    pass

            t = threading.Thread(target=timer, daemon=True)
            t.start()
            try:
                return fn(*a, **kw)
            finally:
                # nothing to cancel; best-effort watchdog
                pass

        return inner

    return deco


def within_timeout(start_ts: float, timeout_sec: Optional[float]) -> bool:
    """Return ``True`` while ``timeout_sec`` has not elapsed from ``start_ts``."""

    if not timeout_sec or timeout_sec <= 0:
        return True
    return (time.perf_counter() - start_ts) <= timeout_sec
