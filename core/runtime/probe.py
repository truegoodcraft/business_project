from __future__ import annotations

import concurrent.futures
import time
from typing import Dict, List

from core.conn_broker import ConnectionBroker

PROBE_TIMEOUT_SEC = 5


def _probe_one(broker: ConnectionBroker, svc: str) -> dict:
    t0 = time.time()
    try:
        res = broker.probe(svc)
        if not isinstance(res, dict):
            res = {"ok": bool(res)}
        res.setdefault("elapsed_ms", int((time.time() - t0) * 1000))
        return res
    except Exception as exc:
        return {
            "ok": False,
            "detail": "probe_exception",
            "error": str(exc),
            "elapsed_ms": int((time.time() - t0) * 1000),
        }


def probe_services(broker: ConnectionBroker, services: List[str]) -> Dict[str, dict]:
    results: Dict[str, dict] = {}
    if not services:
        return results
    max_workers = min(8, max(1, len(services)))
    wall_timeout = PROBE_TIMEOUT_SEC * max(1, len(services))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futs = {pool.submit(_probe_one, broker, svc): svc for svc in services}
        try:
            for fut in concurrent.futures.as_completed(futs, timeout=wall_timeout):
                svc = futs[fut]
                try:
                    results[svc] = fut.result(timeout=0)
                except concurrent.futures.TimeoutError:
                    results[svc] = {
                        "ok": False,
                        "detail": "probe_timeout",
                        "timeout_sec": PROBE_TIMEOUT_SEC,
                    }
                except Exception as exc:
                    results[svc] = {
                        "ok": False,
                        "detail": "probe_exception",
                        "error": str(exc),
                    }
        except concurrent.futures.TimeoutError:
            pass
    for fut, svc in futs.items():
        if svc not in results:
            results[svc] = {
                "ok": False,
                "detail": "probe_timeout",
                "timeout_sec": PROBE_TIMEOUT_SEC,
            }
    return results
