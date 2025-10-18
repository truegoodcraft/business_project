from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from typing import Any, Dict


class SandboxError(RuntimeError):
    ...


def run_transform(plugin_id: str, fn: str, payload: Dict[str, Any], *, timeout: float = 5.0) -> Dict[str, Any]:
    """Execute plugin transform in a sandboxed subprocess."""

    with tempfile.TemporaryDirectory(prefix="bus_sandbox_") as tmp:
        env = os.environ.copy()
        env["BUS_SANDBOX_DIR"] = tmp
        cmd = [
            sys.executable,
            "-m",
            "core.runtime.sandbox_runner",
            "--plugin",
            plugin_id,
            "--fn",
            fn,
        ]
        try:
            proc = subprocess.run(
                cmd,
                input=json.dumps(payload).encode("utf-8"),
                capture_output=True,
                timeout=max(timeout, 0.5),
                check=False,
                cwd=tmp,
                env=env,
            )
        except subprocess.TimeoutExpired as exc:
            raise SandboxError(f"sandbox_timeout:{plugin_id}:{fn}") from exc
        if proc.returncode != 0:
            detail = proc.stderr.decode("utf-8", errors="ignore").strip()
            raise SandboxError(
                f"sandbox_error:{plugin_id}:{fn}:{proc.returncode}:{detail}",
            )
        stdout = proc.stdout.decode("utf-8")
        try:
            result = json.loads(stdout or "{}")
        except json.JSONDecodeError as exc:
            raise SandboxError("sandbox_invalid_json") from exc
        return result
