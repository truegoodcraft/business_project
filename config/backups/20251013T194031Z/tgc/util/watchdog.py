import sys, threading, time, faulthandler


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
