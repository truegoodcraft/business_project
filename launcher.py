# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import sys
import subprocess
import os
import ctypes

# 1. Dependency Check Routine
required_modules = ['requests', 'fastapi', 'uvicorn', 'pystray', 'PIL']
missing_modules = []

for mod in required_modules:
    try:
        import_name = "PIL" if mod == "PIL" else mod
        __import__(import_name)
    except ImportError:
        missing_modules.append(mod)
    except Exception:
        pass

if missing_modules:
    print("!" * 60)
    print("CRITICAL STARTUP ERROR: Missing Dependencies")
    print(f"Missing modules: {', '.join(missing_modules)}")
    print("-" * 60)
    print("Attempting to auto-install dependencies...")
    try:
        req_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_path])
        print("Dependencies installed. Please restart the launcher.")
        sys.exit(0)
    except Exception as e:
        print(f"Auto-install failed: {e}")
        print("Please manually run: pip install -r requirements.txt")
        print("!" * 60)
        try:
             input("Press Enter to exit...")
        except EOFError:
             pass
        sys.exit(1)

import argparse
import atexit
import signal
import socket
import threading
import time
import webbrowser
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
    from PIL import Image, ImageDraw
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

def hide_console():
    """Hides the console window."""
    if os.name == 'nt':
        try:
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 0) # SW_HIDE
        except Exception:
            pass

def show_console(icon=None, item=None):
    """Unhides the console window."""
    if os.name == 'nt':
        try:
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 5) # SW_SHOW
                ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass

def open_dashboard(url: str):
    """Attempts to open URL in 'App Mode' (no address bar) using Edge/Chrome."""
    if os.name == 'nt':
        # Try Edge first (standard on Windows)
        try:
            subprocess.Popen(f'start msedge --app="{url}"', shell=True)
            return
        except Exception:
            pass
    # Fallback to standard browser
    webbrowser.open(url)

def restart_program():
    """Restarts the current program."""
    try:
        python = sys.executable
        os.execv(python, [python] + sys.argv)
    except Exception as e:
        print(f"Failed to restart: {e}")

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

    # 2. Check Mode
    is_dev = os.environ.get("BUS_DEV") == "1"

    # Build App
    app, session_token = build_app()
    _write_last_port(port, DATA)
    print(f"Session token saved at: {TOKEN_FILE.resolve()}")
    print(f"Served UI from: {UI_STATIC_DIR.resolve()}")
    print(f"TGC Controller running at http://127.0.0.1:{port}")

    uv_config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="info" if is_dev else "warning")
    server = uvicorn.Server(uv_config)

    if is_dev:
        print("--- RUNNING IN DEV MODE (Console Visible) ---")
        server.run()
        return 0

    else:
        # --- PROD MODE ---
        print("--- RUNNING IN PROD MODE (Hidden) ---")
        print("Check System Tray for controls.")

        # A. Hide Window
        hide_console()

        # B. Start Server in Thread
        server_thread = threading.Thread(target=server.run, daemon=True)
        server_thread.start()

        # C. Wait for Health & Open Browser
        def check_and_open():
            if _wait_for_health(port, session_token):
                if not config_data.launcher.auto_start_in_tray:
                    open_dashboard(f"http://127.0.0.1:{port}/ui/shell.html#/home")

        threading.Thread(target=check_and_open, daemon=True).start()

        # D. Run Tray (Blocking)
        # Check headless fallback first
        if args.headless or os.environ.get("BUS_HEADLESS") or not HAS_GUI:
             # Just wait loop
             while server_thread.is_alive():
                 try:
                     time.sleep(1)
                 except KeyboardInterrupt:
                     server.should_exit = True
                     break
             return 0

        # Tray Logic
        image = None
        try:
             image = Image.open("Flat-Dark.png")
        except Exception:
             # Fallback
             image = Image.new('RGB', (64, 64), color=(30, 31, 34))
             from PIL import ImageDraw
             d = ImageDraw.Draw(image)
             d.text((10, 10), "BUS", fill=(255, 255, 255))

        def quit_app(icon, item):
            icon.stop()
            server.should_exit = True
            os._exit(0)

        def open_dash(icon, item):
             open_dashboard(f"http://127.0.0.1:{port}/ui/shell.html#/home")

        def restart_app(icon, item):
            icon.stop()
            restart_program()

        menu = pystray.Menu(
            pystray.MenuItem("Open Dashboard", open_dash, default=True),
            pystray.MenuItem("Show Console", show_console),
            pystray.MenuItem("Restart", restart_app),
            pystray.MenuItem("Quit", quit_app)
        )

        icon = pystray.Icon("BUS Core", image, "BUS Core", menu)
        icon.run()

        return 0


if __name__ == "__main__":
    raise SystemExit(main())
