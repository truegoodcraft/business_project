# Copyright (C) 2025 BUS Core Authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional


class PlatformAdapter:
    def open_path(self, path: str | Path) -> None:
        target = str(path)
        if sys.platform.startswith("win"):
            os.startfile(target)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", target], check=False)
        else:
            subprocess.run(["xdg-open", target], check=False)

    def is_admin(self) -> bool:
        if not sys.platform.startswith("win"):
            return os.geteuid() == 0 if hasattr(os, "geteuid") else False
        try:
            import ctypes
            from ctypes import wintypes
        except Exception:
            return False
        advapi32 = ctypes.WinDLL("advapi32")  # type: ignore[attr-defined]
        advapi32.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
        advapi32.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_uint, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
        token = wintypes.HANDLE()
        if not advapi32.OpenProcessToken(ctypes.windll.kernel32.GetCurrentProcess(), 0x8, ctypes.byref(token)):
            return False
        try:
            elevation = ctypes.wintypes.DWORD()
            size = ctypes.wintypes.DWORD()
            if advapi32.GetTokenInformation(token, 20, ctypes.byref(elevation), ctypes.sizeof(elevation), ctypes.byref(size)):
                return bool(elevation.value)
        finally:
            ctypes.windll.kernel32.CloseHandle(token)
        return False
