import json, time, pathlib

from core.unilog import write as uni_write

LOG = pathlib.Path("reports/audit.log")
LOG.parent.mkdir(parents=True, exist_ok=True)


def write_audit(
    run_id: str,
    plugin: str,
    capability: str,
    scopes: list[str],
    outcome: str,
    ms: int,
    notes: str = "",
) -> None:
    LOG.write_text("", append=True) if not LOG.exists() else None
    with LOG.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "run_id": run_id,
                    "plugin": plugin,
                    "capability": capability,
                    "scopes": scopes,
                    "outcome": outcome,
                    "ms": ms,
                    "notes": notes,
                }
            )
            + "\n"
        )
    uni_write(
        "audit.entry",
        run_id,
        plugin=plugin,
        capability=capability,
        scopes=scopes,
        outcome=outcome,
        ms=ms,
        notes=notes,
    )
