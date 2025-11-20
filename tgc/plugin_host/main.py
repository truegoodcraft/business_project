# SPDX-License-Identifier: AGPL-3.0-or-later
import argparse, sys
import win32file
from core.broker.jsonrpc import pack, req

def _read_frame(h):
    hr, raw_len = win32file.ReadFile(h, 4, None)
    n = int.from_bytes(raw_len, "little")
    hr, data = win32file.ReadFile(h, n, None)
    return data

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pipe-name", required=True)
    ap.add_argument("--plugin-id", required=True)
    args = ap.parse_args()

    h = win32file.CreateFile(args.pipe_name,
                             win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                             0, None, win32file.OPEN_EXISTING, 0, None)
    win32file.WriteFile(h, pack(req("hello", {"plugin_id": args.plugin_id, "api_version": 1}, 1)))
    _ = _read_frame(h)
    win32file.WriteFile(h, pack(req("ping", {}, 2)))
    _ = _read_frame(h)
    win32file.CloseHandle(h)
    return 0

if __name__ == "__main__":
    sys.exit(main())
