from __future__ import annotations

import os
import time
from pathlib import Path


def wait_for_exclusive(path: Path, attempts: int = 120, sleep_s: float = 0.5) -> tuple[bool, int]:
    """Try to open ``path`` with no sharing to prove exclusive access.

    Returns (ok, last_error). On non-Windows, it's always True.
    """

    path = Path(path)
    if os.name != "nt":
        return True, 0

    import ctypes
    import ctypes.wintypes as wt

    CreateFileW = ctypes.windll.kernel32.CreateFileW
    CreateFileW.restype = wt.HANDLE

    GENERIC_READ = 0x80000000
    FILE_SHARE_NONE = 0x00000000
    OPEN_EXISTING = 3
    FILE_ATTRIBUTE_NORMAL = 0x80
    INVALID_HANDLE_VALUE = wt.HANDLE(-1).value

    last_err = 0
    for _ in range(attempts):
        handle = CreateFileW(
            str(path), GENERIC_READ, FILE_SHARE_NONE, None, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, None
        )
        if handle and int(handle) != INVALID_HANDLE_VALUE:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True, 0
        last_err = ctypes.GetLastError()
        if last_err in (5, 32):  # AccessDenied / SharingViolation
            time.sleep(sleep_s)
            continue
        break
    return False, last_err


def robust_replace(src: Path, dst: Path, attempts: int = 120, sleep_s: float = 0.5) -> tuple[bool, int]:
    """Replace ``dst`` with ``src`` with bounded retries.

    On Windows, uses MoveFileExW with replace/copy/write-through flags.
    Returns (ok, last_error). On non-Windows, raises on failure.
    """

    src = Path(src)
    dst = Path(dst)
    if os.name != "nt":
        os.replace(src, dst)
        return True, 0

    import ctypes

    MoveFileExW = ctypes.windll.kernel32.MoveFileExW
    MOVEFILE_REPLACE_EXISTING = 0x1
    MOVEFILE_COPY_ALLOWED = 0x2
    MOVEFILE_WRITE_THROUGH = 0x8
    flags = MOVEFILE_REPLACE_EXISTING | MOVEFILE_COPY_ALLOWED | MOVEFILE_WRITE_THROUGH

    last_err = 0
    for _ in range(attempts):
        ok = bool(MoveFileExW(str(src), str(dst), flags))
        if ok:
            return True, 0
        last_err = ctypes.GetLastError()
        if last_err in (5, 32):  # AccessDenied / SharingViolation
            time.sleep(sleep_s)
            continue
        break
    return False, last_err
