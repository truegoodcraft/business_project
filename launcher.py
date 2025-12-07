# SPDX-License-Identifier: AGPL-3.0-or-later
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
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from urllib import error, request

import uvicorn

from core.api.http import UI_STATIC_DIR, build_app
from core.config.paths import APP_ROOT, STATE_DIR
from core.config.manager import load_config
from tgc.bootstrap_fs import DATA, LOGS, TOKEN_FILE

try:
    import pystray
    from PIL import Image
    HAS_GUI = True
except Exception:
    HAS_GUI = False

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
    if os.name == "nt":
        (APP_ROOT / "secrets").mkdir(parents=True, exist_ok=True)
        STATE_DIR.mkdir(parents=True, exist_ok=True)


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
    parser.add_argument("--headless", action="store_true", help="Run without system tray")
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

    # Load config
    config_data = load_config()

    server_state = {
        "server": None,
        "thread": None,
        "started": False,
        "token": None
    }

    def run_server():
        app, session_token = build_app()
        server_state["token"] = session_token

        cfg = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="info")
        server = uvicorn.Server(cfg)
        server_state["server"] = server
        server.run()
        server_state["started"] = False

    def start_server_thread():
        server_state["started"] = True
        t = threading.Thread(target=run_server, name="uvicorn-server", daemon=True)
        server_state["thread"] = t
        t.start()

    def stop_server():
        if server_state["server"]:
            server_state["server"].should_exit = True
        if server_state["thread"]:
            server_state["thread"].join(timeout=5)
        server_state["server"] = None
        server_state["thread"] = None

    def restart_server(icon=None, item=None):
        print("Restarting server...")
        stop_server()
        # Small delay to ensure port release
        time.sleep(1)
        start_server_thread()
        print(f"Server restarted at http://127.0.0.1:{port}")

    def open_browser(icon=None, item=None):
        webbrowser.open(f"http://127.0.0.1:{port}/ui/#/writes")

    def open_backup(icon=None, item=None):
        path_str = config_data.backup.default_directory
        path = os.path.expandvars(path_str)
        if os.path.exists(path):
            if os.name == 'nt':
                os.startfile(path)
            else:
                 subprocess.Popen(["xdg-open", path])

    def quit_app(icon, item):
        icon.stop()
        stop_server()
        sys.exit(0)

    # Start server initially
    start_server_thread()

    def wait_startup_and_notify():
        # Wait for startup
        deadline = time.time() + 10.0
        started = False
        while time.time() < deadline:
            if server_state["server"] and getattr(server_state["server"], "started", False):
                started = True
                break
            time.sleep(0.1)

        if not started:
            print("Error: server failed to start")
            return

        print(f"Session token saved at: {TOKEN_FILE.resolve()}")
        print(f"Served UI from: {UI_STATIC_DIR.resolve()}")
        _write_last_port(port, DATA)
        print(f"TGC Controller running at http://127.0.0.1:{port}")

        if not _wait_for_health(port, server_state["token"]):
             print("Warning: core health check failed")
             return

        if not config_data.launcher.auto_start_in_tray:
            open_browser()

    threading.Thread(target=wait_startup_and_notify, daemon=True).start()

    headless = args.headless or os.environ.get("BUS_HEADLESS") or not HAS_GUI

    if headless:
        # Headless mode: wait for interrupts
        def _signal_handler(signum, frame):
            stop_server()
            sys.exit(0)

        for signame in (signal.SIGINT, signal.SIGTERM):
            signal.signal(signame, _signal_handler)

        while server_state["thread"] and server_state["thread"].is_alive():
            try:
                time.sleep(0.5)
            except KeyboardInterrupt:
                break
        stop_server()
        return 0
    else:
        # Tray mode
        # Icon image
        try:
            image = Image.open("Flat-Dark.png")
        except Exception:
            # Create a simple fallback image if file not found
            from PIL import ImageDraw
            image = Image.new('RGB', (64, 64), color = (30, 31, 34))
            d = ImageDraw.Draw(image)
            d.text((10,10), "BUS", fill=(255,255,255))

        menu = pystray.Menu(
            pystray.MenuItem("Open BUS Core", open_browser, default=True),
            pystray.MenuItem("Restart BUS Core", restart_server),
            pystray.MenuItem("Open Backup Folder", open_backup),
            pystray.MenuItem("Quit BUS Core", quit_app)
        )

        icon = pystray.Icon("BUS Core", image, "BUS Core", menu)
        icon.run()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
