# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import os
import sys
import ctypes
import threading
import subprocess
import time
import webbrowser
from pathlib import Path

# --- 1. Dependency Guard ---
try:
    import requests
    import uvicorn
    from PIL import Image
    from core.api.http import build_app
    from core.config.manager import load_config
    from tgc.bootstrap_fs import DATA, LOGS
    from core.config.paths import APP_ROOT, STATE_DIR
except ImportError as e:
    print("!"*60)
    print(f"CRITICAL: Missing dependency - {e}")
    print("Please run: pip install -r requirements.txt")
    print("!"*60)
    try:
        input("Press Enter to exit...")
    except EOFError:
        pass
    sys.exit(1)

try:
    import pystray
    HAS_TRAY = True
except ImportError:
    print("!"*60)
    print("CRITICAL: Missing dependency - pystray")
    print("Please run: pip install -r requirements.txt")
    print("!"*60)
    sys.exit(1)
except Exception:
    # Ignore runtime errors during import (e.g. X11 missing)
    HAS_TRAY = False

def _ensure_runtime_dirs() -> None:
    for path in (DATA, LOGS):
        path.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        (APP_ROOT / "secrets").mkdir(parents=True, exist_ok=True)
        STATE_DIR.mkdir(parents=True, exist_ok=True)

# --- 2. Window Management (Stealth Mode) ---
def hide_console():
    """Vanishes the console window."""
    if os.name == 'nt':
        try:
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 0) # SW_HIDE
        except Exception:
            pass

def show_console():
    """Restores the console window."""
    if os.name == 'nt':
        try:
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 5) # SW_SHOW
                ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass

# --- 3. Browser Launch Helper ---
def open_dashboard(port):
    """Opens the UI in the default standard browser (new tab)."""
    url = f"http://127.0.0.1:{port}/ui/shell.html#/home"
    # Simple standard launch. No --app flags.
    webbrowser.open(url)

# --- 4. Main Execution ---
def main():
    _ensure_runtime_dirs()

    port = 8765
    is_dev = os.environ.get("BUS_DEV") == "1"

    if is_dev:
        print("--- DEV MODE: Console remains visible ---")
        # Run standard blocking server
        # Using build_app to ensure CORE initialization
        app, _ = build_app()
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
        return

    # B. PROD MODE: Vanish!
    hide_console()

    # C. Load Config & Resources
    cfg = load_config()

    # Load Icon (Generate logic if missing to prevent crash)
    try:
        icon_img = Image.open("Flat-Dark.png")
    except Exception:
        # Fallback: Create a blue square
        icon_img = Image.new('RGB', (64, 64), color = (73, 109, 137))

    # D. Start Server (Threaded)
    def run_server():
        app, _ = build_app()
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="error")

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # E. Auto-Launch Browser
    if not cfg.launcher.auto_start_in_tray:
        # Wait slightly for server boot
        def launch_delayed():
            time.sleep(1.5)
            open_dashboard(port)
        threading.Thread(target=launch_delayed).start()

    # F. System Tray (Blocking)
    if not HAS_TRAY:
        # Fallback for headless/error environments
        while server_thread.is_alive():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                break
        return

    def on_quit(icon, item):
        icon.stop()
        os._exit(0) # Force kill hidden window

    def on_show_console(icon, item):
        show_console()

    def on_open_dash(icon, item):
        open_dashboard(port)

    menu = pystray.Menu(
        pystray.MenuItem("Open Dashboard", on_open_dash, default=True),
        pystray.MenuItem("Show Console (Debug)", on_show_console),
        pystray.MenuItem("Quit BUS Core", on_quit)
    )

    icon = pystray.Icon("BUS Core", icon_img, "TGC BUS Core", menu)
    icon.run()

if __name__ == "__main__":
    main()
