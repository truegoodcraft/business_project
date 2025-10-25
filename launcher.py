from __future__ import annotations

import argparse
import atexit
import os
import signal
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Optional, Tuple
from urllib import error, request

import uvicorn

from core.api.http import UI_STATIC_DIR, build_app
from tgc.bootstrap_fs import DATA, LOGS, TOKEN_FILE

DEFAULT_PORT = 8765
FALLBACK_PORT = 8777
HEALTH_PATH = "/health"


def _base_directory() -> Path:
    if getattr(sys, "frozen", False):  # PyInstaller
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _ensure_runtime_dirs() -> None:
    for path in (DATA, LOGS):
        path.mkdir(parents=True, exist_ok=True)


def _is_port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _parse_port(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    try:
        port = int(value)
    except ValueError:
        return None
    if 0 < port < 65536:
        return port
    return None


def _select_port(args_port: Optional[int], data_dir: Path) -> Tuple[int, bool, Optional[int]]:
    env_port = _parse_port(os.environ.get("TGC_PORT") or os.environ.get("PORT"))
    last_port_path = data_dir / "last_port.txt"
    explicit = args_port is not None or env_port is not None

    if args_port is not None:
        port = args_port
    elif env_port is not None:
        port = env_port
    else:
        port = DEFAULT_PORT
        if last_port_path.exists():
            previous = _parse_port(last_port_path.read_text(encoding="utf-8").strip())
            if previous:
                port = previous

    if _is_port_free(port):
        return port, explicit, None

    if explicit:
        raise RuntimeError(f"Port {port} is not available")

    fallback_candidates = []
    if port != DEFAULT_PORT:
        fallback_candidates.append(DEFAULT_PORT)
    if FALLBACK_PORT not in fallback_candidates and FALLBACK_PORT != port:
        fallback_candidates.append(FALLBACK_PORT)

    for candidate in fallback_candidates:
        if _is_port_free(candidate):
            return candidate, False, port

    raise RuntimeError("No available port found")


def _write_last_port(port: int, data_dir: Path) -> None:
    try:
        (data_dir / "last_port.txt").write_text(str(port), encoding="utf-8")
    except OSError:
        pass


def _wait_for_health(port: int, token: str, retries: int = 40, delay: float = 0.5) -> bool:
    url = f"http://127.0.0.1:{port}{HEALTH_PATH}"
    headers = {"X-Session-Token": token}
    for _ in range(retries):
        try:
            req = request.Request(url, headers=headers)
            with request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    return True
        except error.URLError:
            time.sleep(delay)
        except Exception:
            time.sleep(delay)
    return False


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="TGC Controller launcher")
    parser.add_argument("--port", type=int, help="Override listen port", default=None)
    args = parser.parse_args(argv)

    base_dir = _base_directory()
    os.chdir(base_dir)

    _ensure_runtime_dirs()

    try:
        port, explicit, previous = _select_port(args.port, DATA)
    except RuntimeError as exc:
        print(f"Error: {exc}")
        return 1

    if previous is not None:
        print(f"Port {previous} unavailable, using {port}")
    elif port != DEFAULT_PORT and not explicit:
        print(f"Selected port {port}")

    app, session_token = build_app()

    print(f"Session token saved at: {TOKEN_FILE.resolve()}")
    print(f"Served UI from: {UI_STATIC_DIR.resolve()}")

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="info")
    server = uvicorn.Server(config)

    def _shutdown_server() -> None:
        if not server.should_exit:
            server.should_exit = True

    atexit.register(_shutdown_server)

    server_thread = threading.Thread(target=server.run, name="uvicorn-server", daemon=True)
    server_thread.start()

    if not server.started.wait(timeout=10):
        print("Error: server failed to start")
        server.should_exit = True
        server_thread.join(timeout=5)
        return 1

    _write_last_port(port, DATA)
    print(f"TGC Controller running at http://127.0.0.1:{port}")

    if _wait_for_health(port, session_token):
        webbrowser.open(f"http://127.0.0.1:{port}/ui/#/writes")
    else:
        print("Warning: core health check failed; UI will not auto-open.")

    def _signal_handler(signum, frame):  # noqa: ARG001
        server.should_exit = True

    for signame in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signame, _signal_handler)

    try:
        while server_thread.is_alive():
            time.sleep(0.2)
    except KeyboardInterrupt:
        server.should_exit = True
    finally:
        server_thread.join()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
